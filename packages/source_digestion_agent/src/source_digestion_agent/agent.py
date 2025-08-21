import os
import asyncio
import mlflow
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
import functools
import inspect
from rich.console import Console
from rich.pretty import Pretty

from add_source_to_vault import SourceManager
import tools as tool_pkg

# MLflow autologging
mlflow.openai.autolog()
mlflow.langchain.autolog()
load_dotenv()
console = Console()


class SourceDigestionAgent:
    def __init__(
            self, 
            vault_directory: str, 
            doi: str, 
            model: str = "gpt-5-mini", 
            brightdata_api_key: str = None,
            debug: bool = False,
        ) -> None:

        try:
            result = SourceManager(vault_path=vault_directory, brightdata_api_key=brightdata_api_key).add_source(doi)
        except FileExistsError as e:
            print(f"Source already exists: {e.filename}")
            result = {
                "filename": e.filename,
                "raw_text": open(os.path.join(vault_directory, "Sources", f"{e.filename}.txt"), "r", encoding="utf-8").read(),
                "md_content": open(os.path.join(vault_directory, "s", f"{e.filename}.md"), "r", encoding="utf-8").read(),
                "bib_content": open(os.path.join(vault_directory, "Sources", f"{e.filename}.bib"), "r", encoding="utf-8").read()
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

        if debug:
            def _wrap_with_pause(func):
                sig = inspect.signature(func)

                @functools.wraps(func)
                def wrapped(*args, **kwargs):
                    bound = sig.bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    console.print(f"[bold magenta][tool:args][/bold magenta] [cyan]{func.__name__}[/cyan]")
                    console.print(Pretty(dict(bound.arguments), indent_guides=True))
                    input("Press Enter to call tool...")
                    result = func(*args, **kwargs)
                    console.print(f"[bold green][tool:out][/bold green]  [cyan]{func.__name__}[/cyan]")
                    console.print(Pretty(result, indent_guides=True))
                    input("Press Enter to continue...")
                    return result

                wrapped.__signature__ = sig
                return wrapped

            tools = [
                tool(_wrap_with_pause(getattr(tool_pkg, name)(vault_directory=vault_directory)))
                for name in tool_pkg.__all__
            ]
        else:
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
        inputs = {"messages": [{"role": "user", "content": message}]}
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

        result = self._agent.invoke(inputs, config=config)

        final = result["messages"][-1]
        return getattr(final, "content", str(final))

    __call__ = invoke


if __name__ == "__main__":
    agent = SourceDigestionAgent(vault_directory="./example_vault", doi="10.48550/arXiv.2506.13131", model="gpt-5-mini", debug=True)
    print(agent.invoke("Digest this source?", thread_id="example-thread"))