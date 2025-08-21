import os
import json
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import Field

load_dotenv()


def get_note_list(directory: str) -> List[str]:
    """Recursively list all .md notes relative to directory, e.g. 'sub/dir/note.md'."""
    if not os.path.exists(directory):
        return []
    notes: List[str] = []
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, filename), directory)
                notes.append(rel_path.replace(os.sep, '/'))
    return sorted(notes)


def list_relevant_notes_outer(*args, **kwargs):
    vault_directory = kwargs["vault_directory"]
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0, reasoning_effort="low")

    @tool
    def log_relevant_notes(
            notes: list[str] = Field(description="List of exact note paths that are relevant to the query. (leave empty if no notes are relevant)")
            ):
        """
        Log notes relevant to the query.
        """
        print(f"Relevant notes: {notes}")
    
    llm_with_tools = llm.bind_tools([log_relevant_notes], tool_choice=True)
    
    def list_relevant_notes(
            query: str = Field(description="Concise explanation of what notes you need. This can be in natural language and contain many different sub-topics.")
            ) -> list[str]:
        """
        Get titles of all notes that are relevant to the query. It's possible to call this tool with a long query, consisting of many parts.
        """
        notes = get_note_list(vault_directory)
        if not notes:
            print("No notes in directory: ", vault_directory)
            return []

        block_size = 30
        blocks = [notes[i : i + block_size] for i in range(0, len(notes), block_size)]

        def process_block(block: List[str]) -> List[str]:
            system_prompt = (
                "Call the log_relevant_notes tool and select only the note paths relevant to the query." 
                "If the query consists of many parts, it's enough for a note to be relevant to one of the parts to be included." 
                "If no notes are relevant to the query, return an empty list \n"
                "## Query:\n" 
                "```\n"
                f"{query}\n"
                "```\n\n"
            )
            user_prompt = (
                "Choose strictly from this list (use exact strings):\n"
                f"{block}\n\n"
            )
            resp = llm_with_tools.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]) # TODO: Force tool use
            calls = getattr(resp, "tool_calls", None) or getattr(resp, "additional_kwargs", {}).get("tool_calls", [])
            if not calls:
                print("Tool call failed: no tool_calls in response")
                return []
            args = (calls[0].get("args") or (json.loads(calls[0].get("function", {}).get("arguments", "{}")) if isinstance(calls[0].get("function", {}).get("arguments"), str) else {})) or {}
            notes_list = args.get("notes")
            if not isinstance(notes_list, list):
                print(f"Tool call missing 'notes' list. args={args}")
                return []
            invalid = [n for n in notes_list if isinstance(n, str) and n not in block]
            if invalid:
                print(f"Invalid notes (not in provided block): {invalid}")
            return [n for n in notes_list if isinstance(n, str) and n in block]

        relevant_notes: List[str] = []
        with ThreadPoolExecutor(max_workers=min(len(blocks), 10)) as executor:
            futures = [executor.submit(process_block, b) for b in blocks]
            for f in as_completed(futures):
                try:
                    relevant_notes.extend(f.result())
                except Exception as exc:
                    print(f"Block processing generated an exception: {exc}")

        # dedupe while preserving order
        seen = set()
        deduped = []
        for n in relevant_notes:
            if n not in seen:
                seen.add(n)
                deduped.append(n)
        return deduped

    return list_relevant_notes

if __name__ == "__main__":
    import mlflow
    mlflow.openai.autolog()
    inner = list_relevant_notes_outer(vault_directory="./example_vault") # ~/Library/Documents/Obsidian/SecondBrainSync2
    print(inner("Notes related to AlphaEvolve (2025 Novikov et al.), coding agent, LLM-guided evolution, matrix multiplication improvements, mathematical discoveries, data center scheduling, Gemini kernel optimization, TPU circuit design, FlashAttention optimization, evolutionary code agent, propositions from this paper"))