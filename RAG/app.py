from run_agent import run_agent  # import your function
import sys

def main():
    print("🤖 RAG Chatbot CLI")
    print("Type 'exit' to quit.\n")

    chat_history = []  # keep track of conversation

    while True:
        try:
            query = input("You: ").strip()
            if query.lower() in {"exit", "quit"}:
                print("👋 Goodbye!")
                break

            # call run_agent with history
            response = run_agent(query, chat_history)

            # store messages in history
            chat_history.append({"sender": "user", "message": query})
            chat_history.append({"sender": "bot", "message": response})

            print(f"Bot: {response}\n")

        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️ Error: {str(e)}\n")

if __name__ == "__main__":
    main()
