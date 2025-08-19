import os
import mlflow
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

# MLflow autologging
mlflow.openai.autolog()
mlflow.langchain.autolog()
load_dotenv()


class SourceDigestionAgent:
    def __init__(self, vault_directory: str, model: str = "gpt-5-mini") -> None:
        from . import tools as tool_pkg

        prompt_path = os.path.join(os.path.dirname(__file__), "templates", "testing_system_prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        tools = [
            tool(getattr(tool_pkg, name)(vault_directory=vault_directory))
            for name in tool_pkg.__all__
        ]

        llm = ChatOpenAI(
            model=model,
            use_responses_api=True,
        )
        
        self._agent = create_react_agent(
            model=llm, 
            tools=tools, 
            prompt=prompt, 
            checkpointer=InMemorySaver(),
        )

    def invoke(self, message: str, thread_id: str) -> str:
        result = self._agent.invoke(
            {"messages": [{"role": "user", "content": message}]}, 
            config={"configurable": {"thread_id": thread_id}}
        )
        final = result["messages"][-1]
        return getattr(final, "content", str(final))

    __call__ = invoke