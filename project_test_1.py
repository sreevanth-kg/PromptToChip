import json
import msvcrt
import os
import sys
import threading
from datetime import datetime
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
PROJECT_FILE = Path(__file__).with_name("project_metadata.json")
CREATE_NEW_PROJECT = "+ Create new project"
PROJECT_LOCK = threading.Lock()
PROJECT_THREADS = []


def current_timestamp():
    return datetime.now().isoformat(timespec="seconds")


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


def save_chat_turn(memory, chat_name, user_input, ai_response):
    memory[chat_name].append({"role": "user", "text": user_input})
    memory[chat_name].append({"role": "model", "text": ai_response})
    save_memory(memory)


def load_project_metadata():
    if not PROJECT_FILE.exists():
        return {}

    try:
        with PROJECT_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        print(f"{ERROR}[Project Error]:{Style.RESET_ALL} Could not read project metadata. Starting fresh.")
        return {}


def save_project_metadata(projects):
    try:
        with PROJECT_FILE.open("w", encoding="utf-8") as file:
            json.dump(projects, file, indent=2)
    except OSError as e:
        print(f"{ERROR}[Project Error]:{Style.RESET_ALL} Could not save project metadata: {e}")


def default_project_metadata(project_name):
    timestamp = current_timestamp()

    return {
        "project_name": project_name,
        "description": "",
        "product_goal": "",
        "board": "",
        "hdl_language": "",
        "toolchain": "",
        "clock_frequency": "",
        "status": "discussion",
        "message_store": MEMORY_FILE.name,
        "message_key": project_name,
        "message_count": 0,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def compact_metadata(project):
    keys = [
        "project_name",
        "description",
        "product_goal",
        "board",
        "hdl_language",
        "toolchain",
        "clock_frequency",
        "status",
    ]
    return {key: project.get(key, "") for key in keys}


def build_metadata_prompt(project, latest_user_message, latest_model_message):
    current_metadata = json.dumps(compact_metadata(project), indent=2)

    return f"""
You update project metadata for an FPGA AI playground.

Current metadata:
{current_metadata}

Latest user message:
{latest_user_message}

Latest assistant message:
{latest_model_message}

Return one JSON object with these exact keys:
project_name, description, product_goal, board, hdl_language, toolchain, clock_frequency, status

Rules:
- Preserve existing values unless the latest chat clearly improves them.
- Do not guess board, language, toolchain, or clock frequency.
- Use empty string when unknown.
- status should usually be one of: discussion, planning, approved, coding, simulation, board_testing, completed.
- Keep description and product_goal short.
"""


def project_metadata_schema():
    return {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "description": {"type": "string"},
            "product_goal": {"type": "string"},
            "board": {"type": "string"},
            "hdl_language": {"type": "string"},
            "toolchain": {"type": "string"},
            "clock_frequency": {"type": "string"},
            "status": {"type": "string"},
        },
        "required": [
            "project_name",
            "description",
            "product_goal",
            "board",
            "hdl_language",
            "toolchain",
            "clock_frequency",
            "status",
        ],
    }


def merge_ai_metadata(project, ai_metadata):
    allowed_keys = {
        "project_name",
        "description",
        "product_goal",
        "board",
        "hdl_language",
        "toolchain",
        "clock_frequency",
        "status",
    }

    for key in allowed_keys:
        value = ai_metadata.get(key)
        if isinstance(value, str):
            project[key] = value.strip()


def update_project_metadata(projects, chat_name, memory, api_key, model_name, latest_user_message, latest_model_message):
    with PROJECT_LOCK:
        project = projects.setdefault(chat_name, default_project_metadata(chat_name))

        if not project.get("description"):
            project["description"] = latest_user_message[:200]

        prompt = build_metadata_prompt(project, latest_user_message, latest_model_message)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=project_metadata_schema(),
            ),
        )
        if not response.text:
            raise ValueError("metadata response was empty")
        ai_metadata = json.loads(response.text)
    except Exception as e:
        print(f"\n{MUTED}[Project memory skipped]: {e}{Style.RESET_ALL}")
        ai_metadata = None

    with PROJECT_LOCK:
        project = projects.setdefault(chat_name, default_project_metadata(chat_name))

        if isinstance(ai_metadata, dict):
            merge_ai_metadata(project, ai_metadata)

        project["status"] = project.get("status") or "discussion"
        project["message_store"] = MEMORY_FILE.name
        project["message_key"] = chat_name
        project["message_count"] = len(memory.get(chat_name, []))
        project["updated_at"] = current_timestamp()

        save_project_metadata(projects)


def update_project_metadata_in_background(projects, chat_name, memory, api_key, model_name, user_input, ai_response):
    thread = threading.Thread(
        target=update_project_metadata,
        args=(projects, chat_name, memory, api_key, model_name, user_input, ai_response),
    )
    PROJECT_THREADS.append(thread)
    thread.start()


def wait_for_project_metadata_updates():
    for thread in PROJECT_THREADS:
        thread.join(timeout=3)


def sync_project_metadata(memory, projects):
    changed = False

    for chat_name in memory:
        if chat_name not in projects:
            projects[chat_name] = default_project_metadata(chat_name)
            changed = True
        else:
            projects[chat_name]["message_store"] = MEMORY_FILE.name
            projects[chat_name]["message_key"] = chat_name
            projects[chat_name]["message_count"] = len(memory.get(chat_name, []))
            projects[chat_name].setdefault("status", "discussion")
            projects[chat_name].setdefault("description", "")
            projects[chat_name].setdefault("product_goal", "")
            projects[chat_name].setdefault("board", "")
            projects[chat_name].setdefault("hdl_language", "")
            projects[chat_name].setdefault("toolchain", "")
            projects[chat_name].setdefault("clock_frequency", "")
            projects[chat_name].setdefault("created_at", current_timestamp())
            projects[chat_name].setdefault("updated_at", current_timestamp())
            changed = True

    if changed:
        save_project_metadata(projects)

    return projects


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


def show_project_menu(options, selected_index, memory, projects):
    clear_screen()
    print(f"{ACCENT}Choose a project chat{Style.RESET_ALL}")
    print(f"{MUTED}Use arrow keys to move, Enter to select.\n")

    for index, option in enumerate(options):
        pointer = ">" if index == selected_index else " "
        color = USER_COLOR if index == selected_index else Style.RESET_ALL

        if option == CREATE_NEW_PROJECT:
            print(f"{color}{pointer} {option}{Style.RESET_ALL}")
            continue

        project = projects.get(option, default_project_metadata(option))
        status = project.get("status", "discussion")
        board = project.get("board") or "no board"
        message_count = project.get("message_count", len(memory.get(option, [])))
        print(f"{color}{pointer} {option:<18} {status:<12} {message_count:>3} messages  {board}{Style.RESET_ALL}")

    print()


def choose_from_menu(options, memory, projects):
    selected_index = 0

    while True:
        show_project_menu(options, selected_index, memory, projects)
        key = read_menu_key()

        if key == "up":
            selected_index = (selected_index - 1) % len(options)
        elif key == "down":
            selected_index = (selected_index + 1) % len(options)
        elif key == "enter":
            clear_screen()
            return options[selected_index]


def ask_new_project_name(memory):
    default_name = next_project_name(memory)

    while True:
        clear_screen()
        print(f"{ACCENT}Create New Project Chat{Style.RESET_ALL}")
        print(f"{MUTED}Type a name and press Enter.")
        print(f"{MUTED}Press Enter without typing to use: {default_name}\n")

        chat_name = input(f"{USER_COLOR}New project name:{Style.RESET_ALL} ").strip() or default_name

        if chat_name not in memory:
            return chat_name

        print(f"\n{ERROR}That chat already exists. Choose a different name.")
        input(f"{MUTED}Press Enter to try again...{Style.RESET_ALL}")


def next_project_name(memory):
    count = 1

    while f"project_{count}" in memory:
        count += 1

    return f"project_{count}"


def pick_project(memory, projects):
    options = sorted(memory.keys()) + [CREATE_NEW_PROJECT]
    selected_chat = choose_from_menu(options, memory, projects)

    if selected_chat == CREATE_NEW_PROJECT:
        chat_name = ask_new_project_name(memory)
        memory[chat_name] = []
        projects[chat_name] = default_project_metadata(chat_name)
        print(f"{SUCCESS}Created new project chat:{Style.RESET_ALL} {chat_name}\n")
        save_memory(memory)
        save_project_metadata(projects)
        return chat_name

    message_count = len(memory[selected_chat])
    project = projects.get(selected_chat, default_project_metadata(selected_chat))
    print(f"{SUCCESS}Loaded project chat:{Style.RESET_ALL} {selected_chat}")
    print(f"{MUTED}Status:{Style.RESET_ALL} {project.get('status', 'discussion')}")
    print(f"{MUTED}Board:{Style.RESET_ALL} {project.get('board') or 'not selected'}")
    print(f"{MUTED}Messages:{Style.RESET_ALL} {message_count}\n")

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
        projects = sync_project_metadata(memory, load_project_metadata())
        chat_name = pick_project(memory, projects)
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
                    wait_for_project_metadata_updates()
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
                
                save_chat_turn(memory, chat_name, user_input, ai_response)
                update_project_metadata_in_background(
                    projects,
                    chat_name,
                    memory,
                    api_key,
                    model_name,
                    user_input,
                    ai_response,
                )

                sys.stdout.write("\n\n")
                sys.stdout.flush()

            except APIError as e:
                print(f"\n{ERROR}[API Error]:{Style.RESET_ALL} {e.message}\n")
            except KeyboardInterrupt:
                wait_for_project_metadata_updates()
                print(f"\n\n{SUCCESS}Chat session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n{ERROR}[Unexpected Error]:{Style.RESET_ALL} {e}\n")

    except Exception as e:
        print(f"{ERROR}Failed to initialize the client:{Style.RESET_ALL} {e}", file=sys.stderr)

if __name__ == "__main__":
    start_chat()
