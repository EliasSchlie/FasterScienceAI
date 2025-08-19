"""
Note deletion tool for Obsidian vault integration.
"""

import os
from pydantic import Field


def delete_note_outer(*args, **kwargs):
    """
    Factory function to create a note deletion tool bound to a specific vault directory.
    
    Args:
        vault_directory (str): Path to the Obsidian vault directory
        
    Returns:
        callable: A function that can delete notes from the vault
    """
    VAULT_DIRECTORY = kwargs["vault_directory"]
    
    def delete_note(
            note_title: str = Field(description="The title of the note to delete.")
            ) -> str:
        """
        Deletes a note.
        """
        file_path = os.path.join(VAULT_DIRECTORY, note_title + ".md")
        
        if not os.path.exists(file_path):
            return f"Note {note_title} not found."

        try:
            os.remove(file_path)
            return f"Successfully deleted {note_title}"
        except Exception as e:
            return f"Error deleting note {note_title}: {str(e)}"
    
    return delete_note 