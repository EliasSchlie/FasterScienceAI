import argparse
import os
from .core import SourceManager


def main():
    """CLI entry point for add-source-to-vault."""
    parser = argparse.ArgumentParser(description="Add academic sources to Obsidian vault")
    parser.add_argument("--doi", required=True, help="DOI of the paper to add")
    parser.add_argument("--vault", help="Path to Obsidian vault (or set OBSIDIAN_VAULT_PATH)")
    
    args = parser.parse_args()
    
    vault_path = args.vault or os.getenv("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        print("Error: Please specify vault path with --vault or set OBSIDIAN_VAULT_PATH")
        return 1
    
    manager = SourceManager(vault_path)
    result = manager.add_source(args.doi)
    
    return 0 if result else 1


if __name__ == "__main__":
    exit(main())
