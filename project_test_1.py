import json
import msvcrt
import os
import sys
from pathlib import Path
from colorama import Fore, Style, init
from google import genai
from google.genai import types
from google.genai.errors import APIError

init(autoreset=True)

ACCENT = Fore.CYAN + Style.BRIGHT
AI_COLOR = Fore.GREEN + Style.BRIGHT
ERROR = Fore.RED + Style.BRIGHT
MUTED = Fore.WHITE + Style.DIM
SUCCESS = Fore.MAGENTA + Style.BRIGHT
USER_COLOR = Fore.YELLOW + Style.BRIGHT

MEMORY_FILE = Path(__file__).with_name("chat_memory.json")
CREATE_NEW_CHAT = "+ Create new chat"


def load_memory():
    if not MEMORY_FILE.exists():
        return {}

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        print(f"{ERROR}[Memory Error]:{Style.RESET_ALL} Could not read saved chats. Starting fresh.")
        return {}


def save_memory(memory):
    try:
        with MEMORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(memory, file, indent=2)
    except OSError as e:
        print(f"{ERROR}[Memory Error]:{Style.RESET_ALL} Could not save chat memory: {e}")


def clear_screen():
    print("\033[2J\033[H", end="")


def read_menu_key():
    key = msvcrt.getch()

    if key in (b"\x00", b"\xe0"):
        key = msvcrt.getch()
        if key == b"H":
            return "up"
        if key == b"P":
            return "down"

    if key in (b"\r", b"\n"):
        return "enter"

    if key == b"\x03":
        raise KeyboardInterrupt

    return None


def show_chat_menu(options, selected_index):
    clear_screen()
    print(f"{ACCENT}Choose a chat{Style.RESET_ALL}")
    print(f"{MUTED}Use arrow keys to move, Enter to select.\n")

    for index, option in enumerate(options):
        pointer = ">" if index == selected_index else " "
        color = USER_COLOR if index == selected_index else Style.RESET_ALL
        print(f"{color}{pointer} {option}{Style.RESET_ALL}")

    print()


def choose_from_menu(options):
    selected_index = 0

    while True:
        show_chat_menu(options, selected_index)
        key = read_menu_key()

        if key == "up":
            selected_index = (selected_index - 1) % len(options)
        elif key == "down":
            selected_index = (selected_index + 1) % len(options)
        elif key == "enter":
            clear_screen()
            return options[selected_index]


def ask_new_chat_name(memory):
    default_name = next_chat_name(memory)

    while True:
        clear_screen()
        print(f"{ACCENT}Create New Chat{Style.RESET_ALL}")
        print(f"{MUTED}Type a name and press Enter.")
        print(f"{MUTED}Press Enter without typing to use: {default_name}\n")

        chat_name = input(f"{USER_COLOR}New chat name:{Style.RESET_ALL} ").strip() or default_name

        if chat_name not in memory:
            return chat_name

        print(f"\n{ERROR}That chat already exists. Choose a different name.")
        input(f"{MUTED}Press Enter to try again...{Style.RESET_ALL}")


def next_chat_name(memory):
    count = 1

    while f"chat_{count}" in memory:
        count += 1

    return f"chat_{count}"


def pick_chat(memory):
    options = sorted(memory.keys()) + [CREATE_NEW_CHAT]
    selected_chat = choose_from_menu(options)

    if selected_chat == CREATE_NEW_CHAT:
        chat_name = ask_new_chat_name(memory)
        memory[chat_name] = []
        print(f"{SUCCESS}Created new chat memory:{Style.RESET_ALL} {chat_name}\n")
        save_memory(memory)
        return chat_name

    message_count = len(memory[selected_chat])
    print(f"{SUCCESS}Loaded chat memory:{Style.RESET_ALL} {selected_chat} ({message_count} saved messages)\n")

    return selected_chat


def build_history(saved_messages):
    history = []

    for message in saved_messages:
        role = message.get("role")
        text = message.get("text")

        if role in {"user", "model"} and text:
            history.append(types.Content(role=role, parts=[types.Part(text=text)]))

    return history


def start_chat():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(f"{ERROR}[Error]:{Style.RESET_ALL} GEMINI_API_KEY environment variable not found.", file=sys.stderr)
        return

    try:
        memory = load_memory()
        chat_name = pick_chat(memory)
        client = genai.Client(api_key=api_key)
        
        
        model_name = "gemma-4-31b-it"
        chat = client.chats.create(model=model_name, history=build_history(memory[chat_name]))
        
        print(f"{ACCENT}{'=' * 56}")
        print(f"{SUCCESS} Chat session started with {Style.BRIGHT}{model_name}{SUCCESS}!")
        print(f"{MUTED} Type 'exit' or 'quit' to end the conversation.")
        print(f"{ACCENT}{'=' * 56}\n")

        while True:
            try:
                user_input = input(f"{USER_COLOR}You:{Style.RESET_ALL} ").strip()
                
                if user_input.lower() in ["exit", "quit"]:
                    print(f"\n{SUCCESS}Ending chat session. Goodbye!")
                    break
                if not user_input:
                    continue

                sys.stdout.write(f"{AI_COLOR}AI:{Style.RESET_ALL} ")
                sys.stdout.flush()

                # Stream the content using the native chat architecture
                response_stream = chat.send_message_stream(user_input)
                ai_response = ""
                
                for chunk in response_stream:
                    if text := chunk.text:
                        ai_response += text
                        sys.stdout.write(text)
                        sys.stdout.flush()
                
                memory[chat_name].append({"role": "user", "text": user_input})
                memory[chat_name].append({"role": "model", "text": ai_response})
                save_memory(memory)

                sys.stdout.write("\n\n")
                sys.stdout.flush()

            except APIError as e:
                print(f"\n{ERROR}[API Error]:{Style.RESET_ALL} {e.message}\n")
            except KeyboardInterrupt:
                print(f"\n\n{SUCCESS}Chat session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n{ERROR}[Unexpected Error]:{Style.RESET_ALL} {e}\n")

    except Exception as e:
        print(f"{ERROR}Failed to initialize the client:{Style.RESET_ALL} {e}", file=sys.stderr)

if __name__ == "__main__":
    start_chat()
