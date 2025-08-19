from source_digestion_agent import SourceDigestionAgent


if __name__ == "__main__":
    VAULT_DIR = "./example_vault"
    agent = SourceDigestionAgent(vault_directory=VAULT_DIR, model="gpt-5-mini")

    print("Type 'quit' to exit.")
    while True:
        user = input("You: ").strip()
        if user.lower() == "quit":
            break
        print("Agent:", agent.invoke(user, thread_id="example-thread"))
