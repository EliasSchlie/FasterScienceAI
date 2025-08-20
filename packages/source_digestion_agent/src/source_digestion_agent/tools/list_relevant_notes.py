import os
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class RelevantNotes(BaseModel):
    """Model for relevant notes."""
    notes: List[str] = Field(description="List of relevant note titles")


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
    parser = PydanticOutputParser(pydantic_object=RelevantNotes)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    def list_relevant_notes(
            query: str = Field(description="Short explanation of what notes you need. (can be in natural language)")
            ) -> list[str]:
        """
        Get titles of all notes that are relevant to the query.
        """
        notes = get_note_list(vault_directory)
        # Break notes into blocks of 50
        block_size = 50
        relevant_notes = []
        
        # Create blocks for parallel processing
        blocks = [notes[i:i + block_size] for i in range(0, len(notes), block_size)]
        
        def process_block(block):
            """Process a single block of notes."""
            messages = [
                HumanMessage(content=f"From this list of notes, return only the ones relevant to: {query}\n\nNotes:\n{block} \n Wrap the output in this format and provide no other text\n{parser.get_format_instructions()}")
            ]
            response = llm.invoke(messages)
            return parser.parse(response.content).notes
        
        # Process blocks in parallel
        with ThreadPoolExecutor(max_workers=min(len(blocks), 10)) as executor:
            # Submit all tasks
            future_to_block = {executor.submit(process_block, block): block for block in blocks}
            
            # Collect results as they complete
            for future in as_completed(future_to_block):
                try:
                    block_results = future.result()
                    relevant_notes.extend(block_results)
                except Exception as exc:
                    # Log the error but continue processing other blocks
                    print(f'Block processing generated an exception: {exc}')
        
        return relevant_notes
    return list_relevant_notes
