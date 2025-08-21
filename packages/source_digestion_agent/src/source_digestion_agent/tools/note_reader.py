"""
Note reading tool for Obsidian vault integration.

This module provides functionality to read individual notes from an Obsidian vault.
"""

import os
import re
from pydantic import Field, BaseModel
from typing import List, Union
import mmap
from concurrent.futures import ThreadPoolExecutor, as_completed


class Note(BaseModel):
    """A Pydantic model for a note."""
    content: str = Field(description="The full content of the note.")
    inlinks: List[str] = Field(description="A list of file paths for notes that link to this one.")


def safe_read_file(file_path: str) -> str:
    """Safely read a file and return its content or error message."""
    try:
        if not os.path.exists(file_path):
            return f"Note not found at: {file_path}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

def read_note_outer(*args, **kwargs):
    """
    Factory function to create a note reading tool bound to a specific vault directory.
    
    Args:
        vault_directory (str): Path to the Obsidian vault directory
        
    Returns:
        callable: A function that can read notes from the vault
    """
    VAULT_DIRECTORY = kwargs["vault_directory"]

    def search_in_file(file_path, search_pattern):
        try:
            with open(file_path, 'rb', 0) as f, \
                 mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as s:
                if re.search(search_pattern, s):
                    return os.path.relpath(file_path, VAULT_DIRECTORY)
        except (IOError, ValueError):
            pass
        return None

    def list_inlinks(file_path: str) -> list[str]:
        """
        Finds all notes in the vault that link to the given note.
        This is done by searching for "[[note_title]]" or "[[note_title|...]]" links efficiently.
        """
        inlinks = []
        try:
            note_title = os.path.splitext(os.path.basename(file_path))[0]
            # Bytes pattern (when searching bytes)
            search_pattern = re.compile(rb"\[\[" + re.escape(note_title).encode("utf-8") + rb"(?:\]\]|\|)")

            md_files = []
            for root, _, files in os.walk(VAULT_DIRECTORY):
                for file in files:
                    if file.endswith(".md") and os.path.join(root, file) != file_path:
                        md_files.append(os.path.join(root, file))

            with ThreadPoolExecutor() as executor:
                future_to_file = {executor.submit(search_in_file, md_file, search_pattern): md_file for md_file in md_files}
                for future in as_completed(future_to_file):
                    result = future.result()
                    if result:
                        inlinks.append(result)

        except Exception:
            return ["Error: Failed to list inlinks"]
        return inlinks
    
    def read_note(
            note_title: str = Field(description="The title of the note to read.")
            ) -> Union[Note, str]:
        """
        Get the content of a note with the provided title and a list of other notes that link to it (inlinks).
        Returns a Note object on success, or an error string on failure.
        """
        # Construct file path - vault directory is pre-validated by server
        file_path = os.path.join(
            VAULT_DIRECTORY,
            note_title if note_title.endswith(".md") else note_title + ".md",
        )
        
        content = safe_read_file(file_path)
        
        if "Note not found" in content or "Error reading file" in content:
            return content

        inlinks = list_inlinks(file_path)
        
        return Note(content=content, inlinks=inlinks)
    
    return read_note


if __name__ == "__main__":
    inner = read_note_outer(vault_directory="./example_vault")
    print(inner("proposition/test"))