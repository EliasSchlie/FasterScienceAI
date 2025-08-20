"""
Note reading tool for Obsidian vault integration.

This module provides functionality to read individual notes from an Obsidian vault.
"""

import os
from pydantic import Field


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
    
    def read_note(
            note_title: str = Field(description="The title of the note to read.")
            ) -> str:
        """
        Get the content of a note with the provided title.
        """
        # Construct file path - vault directory is pre-validated by server
        file_path = os.path.join(
            VAULT_DIRECTORY,
            note_title if note_title.endswith(".md") else note_title + ".md",
        )
        
        # Use safe file reading function
        return safe_read_file(file_path)
    
    return read_note 