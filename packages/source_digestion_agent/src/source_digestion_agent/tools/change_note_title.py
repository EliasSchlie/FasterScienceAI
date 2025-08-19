"""
Note title changing tool for Obsidian vault integration.
"""

import os
import re
from pydantic import Field


def change_note_title_outer(*args, **kwargs):
    """
    Factory function to create a note renaming tool bound to a specific vault directory.
    
    Args:
        vault_directory (str): Path to the Obsidian vault directory
        
    Returns:
        callable: A function that can rename notes in the vault
    """
    VAULT_DIRECTORY = kwargs["vault_directory"]
    
    def change_note_title(
            note_title: str = Field(description="The title of the note to change."),
            new_title: str = Field(description="The new title of the note.")
            ) -> str:
        """
        Changes the title of a note and updates all wikilinks in other notes.
        """
        old_file_path = os.path.join(VAULT_DIRECTORY, note_title + ".md")
        new_file_path = os.path.join(VAULT_DIRECTORY, new_title + ".md")
        
        if not os.path.exists(old_file_path):
            return f"Note {note_title} not found."
            
        if os.path.exists(new_file_path):
            return f"Note {new_title} already exists."

        try:
            # Update wikilinks in all other notes first
            updated_files = _update_wikilinks_in_vault(VAULT_DIRECTORY, note_title, new_title)
            
            # Rename the actual file
            os.rename(old_file_path, new_file_path)
            
            if updated_files:
                return f"Successfully renamed {note_title} to {new_title}. Updated links in {len(updated_files)} files: {', '.join(updated_files)}"
            else:
                return f"Successfully renamed {note_title} to {new_title}. No links found to update."
                
        except Exception as e:
            return f"Error renaming note {note_title}: {str(e)}"
    
    return change_note_title


def _update_wikilinks_in_vault(vault_directory: str, old_title: str, new_title: str) -> list[str]:
    """
    Updates all wikilinks in the vault that reference the old title.
    
    Args:
        vault_directory: Path to the vault directory
        old_title: The old note title to replace
        new_title: The new note title to use
        
    Returns:
        List of filenames that were updated
    """
    updated_files = []
    
    # Pattern to match wikilinks: [[old_title]] or [[old_title|display_text]]
    pattern = rf'\[\[{re.escape(old_title)}(\|[^\]]+)?\]\]'
    
    for filename in os.listdir(vault_directory):
        if not filename.endswith('.md'):
            continue
            
        file_path = os.path.join(vault_directory, filename)
        
        # Skip the file we're renaming
        if filename == old_title + '.md':
            continue
        try:
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace wikilinks
            new_content = re.sub(pattern, rf'[[{new_title}\1]]', content)
            
            # Only write if content changed
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                updated_files.append(filename)
                
        except Exception as e:
            # Continue with other files if one fails
            print(f"Warning: Could not update links in {filename}: {e}")
            continue
    
    return updated_files 