from add_source_to_vault import SourceManager

# Example: Add a paper to your vault
# Change this to your actual vault path
vault_path = "./test_vault"

manager = SourceManager(vault_path)
result = manager.add_source("10.48550/arXiv.1706.03762")

print(f"Added source: {result}" if result else "Source already exists or failed to download")
