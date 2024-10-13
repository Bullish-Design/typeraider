# llm_interface.py

import hashlib
import json
import threading
import time
import traceback
import sys

from aider.utils import format_content, format_messages
from aider.sendchat import retry_exceptions, send_completion
from aider.llm import litellm
from aider.dump import dump  # noqa: F401


class LLMInterface:
    def __init__(self, main_model, session_manager, user_interface, file_manager, io):
        self.main_model = main_model
        self.session_manager = session_manager
        self.user_interface = user_interface
        self.file_manager = file_manager
        self.io = io
        self.stream = True  # Assuming streaming is enabled
        self.verbose = False
        self.temperature = 0

        self.partial_response_content = ""
        self.partial_response_function_call = dict()
        self.multi_response_content = ""
        self.functions = None

        self.add_cache_headers = False
        self.num_cache_warming_pings = 0
        self.cache_warming_thread = None

    def format_messages(self, user_message):
        messages = self.session_manager.get_formatted_history()
        messages.append({"role": "user", "content": user_message})
        return messages

    def send_message(self, user_message):
        messages = self.format_messages(user_message)
        self.warm_cache(messages)

        retry_delay = 0.125
        exhausted = False
        interrupted = False

        while True:
            try:
                yield from self.send(messages, functions=self.functions)
                break
            except retry_exceptions() as err:
                self.io.tool_warning(str(err))
                retry_delay *= 2
                if retry_delay > 60:
                    break
                self.io.tool_output(f"Retrying in {retry_delay:.1f} seconds...")
                time.sleep(retry_delay)
                continue
            except KeyboardInterrupt:
                interrupted = True
                break
            except litellm.ContextWindowExceededError:
                exhausted = True
                break
            except Exception as err:
                self.io.tool_error(f"Unexpected error: {err}")
                lines = traceback.format_exception(type(err), err, err.__traceback__)
                self.io.tool_error("".join(lines))
                return

        if exhausted:
            self.show_exhausted_error()
            return

        if interrupted:
            self.io.tool_warning("\n\n^C KeyboardInterrupt")
            return

        self.handle_response()

    def send(self, messages, model=None, functions=None):
        if not model:
            model = self.main_model

        self.partial_response_content = ""
        self.partial_response_function_call = dict()

        self.io.log_llm_history("TO LLM", format_messages(messages))

        temp = self.temperature if self.main_model.use_temperature else None

        completion = None
        try:
            hash_object, completion = send_completion(
                model.name,
                messages,
                functions,
                self.stream,
                temp,
                extra_params=model.extra_params,
            )

            if self.stream:
                yield from self.show_send_output_stream(completion)
            else:
                self.show_send_output(completion)
        except KeyboardInterrupt as kbi:
            raise kbi
        finally:
            self.io.log_llm_history(
                "LLM RESPONSE",
                format_content("ASSISTANT", self.partial_response_content),
            )

            if self.partial_response_content:
                self.io.ai_output(self.partial_response_content)
            elif self.partial_response_function_call:
                args = self.parse_partial_args()
                if args:
                    self.io.ai_output(json.dumps(args, indent=4))

            # Token and cost calculations would go here

    def show_send_output_stream(self, completion):
        for chunk in completion:
            if len(chunk.choices) == 0:
                continue

            try:
                func = chunk.choices[0].delta.function_call
                for k, v in func.items():
                    if k in self.partial_response_function_call:
                        self.partial_response_function_call[k] += v
                    else:
                        self.partial_response_function_call[k] = v
            except AttributeError:
                pass

            try:
                text = chunk.choices[0].delta.content
                if text:
                    self.partial_response_content += text
            except AttributeError:
                text = None

            if text:
                try:
                    sys.stdout.write(text)
                except UnicodeEncodeError:
                    safe_text = text.encode(
                        sys.stdout.encoding, errors="backslashreplace"
                    ).decode(sys.stdout.encoding)
                    sys.stdout.write(safe_text)
                sys.stdout.flush()
                yield text

    def handle_response(self):
        # Process the assistant's response
        response_content = self.partial_response_content
        self.session_manager.add_message("assistant", response_content)
        self.user_interface.display_output(response_content)

    def warm_cache(self, messages):
        # Implement cache warming if needed
        pass

    def show_exhausted_error(self):
        # Inform the user about token limit exhaustion
        self.io.tool_error("Token limit exhausted.")

    def parse_partial_args(self):
        data = self.partial_response_function_call.get("arguments")
        if not data:
            return None

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
