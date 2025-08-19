"""
Note editing tool for Obsidian vault integration.
"""

import os
from pydantic import Field


def edit_note_outer(*args, **kwargs):
    """
    Factory function to create a note editing tool bound to a specific vault directory.
    
    Args:
        vault_directory (str): Path to the Obsidian vault directory
        
    Returns:
        callable: A function that can edit notes using find/replace
    """
    VAULT_DIRECTORY = kwargs["vault_directory"]
    
    def edit_note(
            note_title: str = Field(description="The title of the note to edit."),
            old: str = Field(description="The exact string to replace. (if it exists multiple times, all will be replaced)"),
            new: str = Field(description="The new string to replace the old string with.")
            ) -> str:
        """
        Finds and replaces a string in a note with a new string.
        """
        file_path = os.path.join(VAULT_DIRECTORY, note_title + ".md")
        
        if not os.path.exists(file_path):
            return f"Note {note_title} not found."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if old not in content:
                return f"No string '{old}' found in {note_title}"
                
            new_content = content.replace(old, new)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return f"Successfully edited {note_title}"
        except Exception as e:
            return f"Error editing note {note_title}: {str(e)}"
    
    return edit_note 