"""
Note creation tool for Obsidian vault integration.
"""

import os
from pydantic import Field


def create_note_outer(*args, **kwargs):
    """
    Factory function to create a note creation tool bound to a specific vault directory.
    
    Args:
        vault_directory (str): Path to the Obsidian vault directory
        
    Returns:
        callable: A function that can create new notes in the vault
    """
    VAULT_DIRECTORY = kwargs["vault_directory"]
    
    def create_note(
            note_title: str = Field(description="Meaningful, concise, and self-contained title for the note. (including directories)"),
            data: str = Field(description="The content of the note to create.")
            ) -> str:
        """
        Creates a new note with the provided content.
        """
        
        if not (note_title.startswith("proposition/") or note_title.startswith("concept/")):
            return "Error: Notes can only be created in the 'proposition' or 'concept' folders."

        file_path = os.path.join(
            VAULT_DIRECTORY,
            note_title if note_title.endswith(".md") else note_title + ".md",
        )
        
        # Ensure parent directories exist when a path is provided in the title
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if os.path.exists(file_path):
            return f"Note {note_title} already exists."

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data)
            return f"Successfully created {note_title}"
        except Exception as e:
            return f"Error creating note {note_title}: {str(e)}"
    
    return create_note 

if __name__ == "__main__":
    inner = create_note_outer(vault_directory="./example_vault")
    print(inner("proposition/test", "test"))