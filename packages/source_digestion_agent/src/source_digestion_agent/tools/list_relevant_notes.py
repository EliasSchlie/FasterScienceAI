import os
from typing import List
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
    """Get list of all note titles (without .md extension) from directory."""
    if not os.path.exists(directory):
        return []
    return [filename[:-3] for filename in os.listdir(directory) if filename.endswith('.md')]


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
        
        for i in range(0, len(notes), block_size):
            block = notes[i:i + block_size]
            
            # Query LLM for relevant notes in this block
            messages = [
                HumanMessage(content=f"From this list of notes, return only the ones relevant to: {query}\n\nNotes:\n{block} \n Wrap the output in this format and provide no other text\n{parser.get_format_instructions()}")
            ]
            response = llm.invoke(messages)
            relevant_notes.extend(parser.parse(response.content).notes)
        return relevant_notes
    return list_relevant_notes
