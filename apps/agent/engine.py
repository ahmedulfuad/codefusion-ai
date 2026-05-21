import google.generativeai as genai
from django.conf import settings
from .models import ResearchSession, Finding
from .tools import AGENT_TOOLS, list_github_files, read_github_file, get_previous_findings
from .exceptions import AgentExecutionFailedException

genai.configure(api_key=settings.GEMINI_API_KEY)


class CodebaseAgent:
    def __init__(self, session: ResearchSession):
        self.session = session
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[list_github_files, read_github_file, get_previous_findings]
        )

    def calculate_and_add_response_tokens(self, response):
        """
        Calculates token usage internally for the answer/response received from the Gemini API.
        Extracts the content text or function call structures and estimates tokens (1 token ≈ 4 characters).
        """
        if not response:
            return

        content_to_measure = ""
        try:
            # Safely extract parts (captures text or function calls from Gemini's generation)
            if response.candidates and response.candidates[0].content.parts:
                content_to_measure = str(response.candidates[0].content.parts)
            elif hasattr(response, 'text') and response.text:
                content_to_measure = response.text
        except Exception:
            # Absolute fallback: stringify the fallback structure if an unexpected structure occurs
            content_to_measure = str(response)

        # One token is roughly equal to four characters
        estimated_tokens = len(content_to_measure) // 4

        # Accumulate token usage directly onto the session model instance
        self.session.token_usage += estimated_tokens

    def run_research(self):
        # Reset token usage for a completely fresh execution run
        self.session.token_usage = 0

        prompt = (
            f"You are an autonomous codebase researcher. "
            f"Always start by using 'get_previous_findings' to check the database for prior knowledge. "
            f"If you need to know what files exist, use 'list_github_files'. "
            f"If you need to inspect code, use 'read_github_file'. "
            f"Answer the user's question about the repository {self.session.repository.url}.\n\n"
            f"Question: {self.session.question}"
        )

        chat = self.model.start_chat(enable_automatic_function_calling=False)
        # Initial call to Gemini API wrapped in a try-except to catch network failures
        try:
            response = chat.send_message(prompt)
        except Exception as e:
            raise AgentExecutionFailedException(message=f"Initial Gemini API contact failed: {str(e)}")

        # Calculate tokens strictly from the first incoming answer/response
        self.calculate_and_add_response_tokens(response)

        # MULTI-STEP REASONING LOOP
        MAX_STEPS = 10
        step_count = 0

        # Helper function to safely extract the function call from the deeply nested SDK response
        def get_function_call(resp):
            if not resp.candidates or not resp.candidates[0].content.parts:
                return None
            for part in resp.candidates[0].content.parts:
                if not isinstance(part, str) and part.function_call and part.function_call.name:
                    return part.function_call
            return None

        # Check the first response to see if Gemini wants to call a tool
        func_call = get_function_call(response)

        while func_call and step_count < MAX_STEPS:
            step_count += 1
            
            func_name = func_call.name
            
            # Safely parse the protobuf map into a standard Python dictionary
            args = type(func_call).to_dict(func_call).get('args', {})
            
            # Execute the mapped Python function
            tool_function = AGENT_TOOLS.get(func_name)
            if tool_function:
                try:
                    tool_output = tool_function(**args)
                except Exception as e:
                    tool_output = f"Tool execution failed: {str(e)}"
            else:
                tool_output = f"Tool {func_name} not found."

            # WRITE TO DATABASE: Log the Finding / ToolCall
            Finding.objects.create(
                session=self.session,
                tool_name=func_name,
                input_data=args,
                output_data=str(tool_output),
                conclusion=f"Agent utilized {func_name} during step {step_count}."
            )

            tool_payload = {
                "function_response": {
                    "name": func_name,
                    "response": {"result": tool_output}
                }
            }
            # Send tool results context back to Gemini
            try:
                response = chat.send_message(tool_payload)
            except Exception as e:
                raise AgentExecutionFailedException(message=f"For ToolCall Gemini API contact failed: {str(e)}")

            # Calculate tokens strictly from this subsequent step's incoming answer/response
            self.calculate_and_add_response_tokens(response)

            # Check the new response to see if Gemini wants to call *another* tool
            func_call = get_function_call(response)

        # Loop ends when Gemini stops calling tools and provides text, or hits MAX_STEPS
        self.session.final_answer = response.text
        # Save the final answer along with the cleanly calculated internal response tokens
        self.session.save(update_fields=['final_answer', 'token_usage'])

        return self.session
