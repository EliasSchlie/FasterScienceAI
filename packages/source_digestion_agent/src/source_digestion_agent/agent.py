import os
import asyncio
import mlflow
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from add_source_to_vault import SourceManager

# MLflow autologging
mlflow.openai.autolog()
mlflow.langchain.autolog()
load_dotenv()


class SourceDigestionAgent:
    def __init__(
            self, 
            vault_directory: str, 
            doi: str, 
            model: str = "gpt-5-mini", 
            brightdata_api_key: str = None
        ) -> None:
        from . import tools as tool_pkg

        try:
            result = SourceManager(vault_path=vault_directory, brightdata_api_key=brightdata_api_key).add_source(doi)
        except FileExistsError as e:
            print(f"Source already exists: {e.filename}")
            result = {
                "filename": e.filename,
                "raw_text": open(os.path.join(vault_directory, "Sources", "raw", f"{e.filename}.txt"), "r", encoding="utf-8").read(),
                "md_content": open(os.path.join(vault_directory, "Sources", "md", f"{e.filename}.md"), "r", encoding="utf-8").read(),
                "bib_content": open(os.path.join(vault_directory, "Sources", "bib", f"{e.filename}.bib"), "r", encoding="utf-8").read()
            }

        prompt_path = os.path.join(os.path.dirname(__file__), "templates", "system_prompt.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        prompt = prompt.format(
            filename=result["filename"],
            raw_text=result["raw_text"],
            bib_content=result["bib_content"]
        )
        print(prompt)

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

    def invoke(self, message: str, thread_id: str, verbose: bool = False) -> str:
        inputs = {"messages": [{"role": "user", "content": message}]}
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

        if not verbose:
            result = self._agent.invoke(inputs, config=config)
        else:
            async def _run():
                out = None
                async for event in self._agent.astream_events(inputs, config=config, version="v2"):
                    ev = event.get("event")
                    name = event.get("name")
                    data = event.get("data", {})
                    if ev == "on_tool_start":
                        print(f"[tool:start] {name} args={data.get('input')}")
                    elif ev == "on_tool_end":
                        print(f"[tool:end]   {name} -> {data.get('output')}")
                    elif ev == "on_graph_end":
                        out = data.get("output")
                return out

            result = asyncio.run(_run())

        final = result["messages"][-1]
        return getattr(final, "content", str(final))

    __call__ = invoke