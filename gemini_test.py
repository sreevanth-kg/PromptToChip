import os
import sys
from google import genai
from google.genai import types
from google.genai.errors import APIError

def start_chat():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Error]: GEMINI_API_KEY environment variable not found.", file=sys.stderr)
        return

    try:
        client = genai.Client(api_key=api_key)
        
        # Switched to the stable 26B variant of Gemma 4 to bypass the multi-turn SDK parser bug
        model_name = "gemma-4-31b-it"
        chat = client.chats.create(model=model_name)
        
        print("====================================================")
        print(f" Chat session started with {model_name}!")
        print(" Type 'exit' or 'quit' to end the conversation.")
        print("====================================================\n")

        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ["exit", "quit"]:
                    print("\nEnding chat session. Goodbye!")
                    break
                if not user_input:
                    continue

                sys.stdout.write("AI: ")
                sys.stdout.flush()

                # Stream the content using the native chat architecture
                response_stream = chat.send_message_stream(user_input)
                
                for chunk in response_stream:
                    if text := chunk.text:
                        sys.stdout.write(text)
                        sys.stdout.flush()
                
                sys.stdout.write("\n\n")
                sys.stdout.flush()

            except APIError as e:
                print(f"\n[API Error]: {e.message}\n")
            except KeyboardInterrupt:
                print("\n\nChat session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n[Unexpected Error]: {e}\n")

    except Exception as e:
        print(f"Failed to initialize the client: {e}", file=sys.stderr)

if __name__ == "__main__":
    start_chat()