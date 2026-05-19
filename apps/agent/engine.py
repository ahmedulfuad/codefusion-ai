import google.generativeai as genai
from django.conf import settings
from .models import ResearchSession, Finding
from .tools import AGENT_TOOLS, list_github_files, read_github_file, get_previous_findings

genai.configure(api_key=settings.GEMINI_API_KEY)


class CodebaseAgent:
    def __init__(self, session: ResearchSession):
        self.session = session
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[list_github_files, read_github_file, get_previous_findings]
        )

    def run_research(self):
        prompt = (
            f"You are an autonomous codebase researcher. "
            f"Always start by using 'get_previous_findings' to check the database for prior knowledge. "
            f"If you need to know what files exist, use 'list_github_files'. "
            f"If you need to inspect code, use 'read_github_file'. "
            f"Answer the user's question about the repository {self.session.repository.url}.\n\n"
            f"Question: {self.session.question}"
        )

        chat = self.model.start_chat(enable_automatic_function_calling=False)
        response = chat.send_message(prompt)

        # MULTI-STEP REASONING LOOP
        MAX_STEPS = 10
        step_count = 0

        # Helper function to safely extract the function call from the deeply nested SDK response
        def get_function_call(resp):
            if not resp.candidates or not resp.candidates[0].content.parts:
                return None
            for part in resp.candidates[0].content.parts:
                if part.function_call and part.function_call.name:
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

            # Send the tool result back using a standard Python dict.
            # The SDK automatically parses this dictionary into the correct FunctionResponse 
            # objects without needing the missing `protos` namespace.
            response = chat.send_message(
                {
                    "function_response": {
                        "name": func_name,
                        "response": {"result": tool_output}
                    }
                }
            )
            
            # Check the new response to see if Gemini wants to call *another* tool
            func_call = get_function_call(response)

        # Loop ends when Gemini stops calling tools and provides text, or hits MAX_STEPS
        self.session.final_answer = response.text
        self.session.save(update_fields=['final_answer'])
        
        return self.session
