import json
import msvcrt
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style, init
from google import genai
from google.genai import types
from google.genai.errors import APIError

from coder_agent import (
    DEFAULT_CODER_MODEL,
    ask_coder,
    get_last_coder_prompt,
    is_coder_request,
    load_board_context,
    strip_coder_command,
)


init(autoreset=True)

ACCENT = Fore.CYAN + Style.BRIGHT
AI_COLOR = Fore.GREEN + Style.BRIGHT
ERROR = Fore.RED + Style.BRIGHT
MUTED = Fore.WHITE + Style.DIM
SUCCESS = Fore.MAGENTA + Style.BRIGHT
USER_COLOR = Fore.YELLOW + Style.BRIGHT

MEMORY_FILE = Path(__file__).with_name("chat_memory.json")
PROJECT_FILE = Path(__file__).with_name("project_metadata.json")
GENERATED_ROOT = Path(__file__).with_name("generated_projects")
CREATE_NEW_PROJECT = "+ Create new project"
PROJECT_LOCK = threading.Lock()
PROJECT_THREADS = []


def current_timestamp():
    return datetime.now().isoformat(timespec="seconds")


def load_local_env():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as e:
        print(f"{MUTED}[Env skipped]: {e}{Style.RESET_ALL}")


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


def planning_schema():
    return {
        "type": "object",
        "properties": {
            "response_type": {"type": "string"},
            "expertise_level": {"type": "string"},
            "needs_code_generation": {"type": "boolean"},
            "clarifying_questions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "board": {"type": "string"},
            "files_to_generate": {
                "type": "array",
                "items": {"type": "string"},
            },
            "implementation_plan": {
                "type": "array",
                "items": {"type": "string"},
            },
            "coder_request": {"type": "string"},
            "mentor_response": {"type": "string"},
        },
        "required": [
            "response_type",
            "expertise_level",
            "needs_code_generation",
            "clarifying_questions",
            "assumptions",
            "board",
            "files_to_generate",
            "implementation_plan",
            "coder_request",
            "mentor_response",
        ],
    }


def build_planning_prompt(project, user_input, recent_messages):
    board_context = load_board_context()
    recent_turns = []

    for message in recent_messages[-8:]:
        role = message.get("role")
        text = message.get("text")
        if role and text:
            recent_turns.append({"role": role, "text": text[-1200:]})

    return f"""
You are Gemma, the main FPGA engineer and mentor for PromptToChip.
You must receive every user message before any coder tool is used.

Your job:
- Infer the user's FPGA expertise level from the conversation: beginner, intermediate, advanced, or unknown.
- Ask clarifying questions when code generation would be risky or underspecified.
- Create an execution plan before any code generation.
- Decide whether the local coder_agent should be used after approval.
- Act as a mentor: explain enough for the user's level without overwhelming them.

Hard rules:
- Do not generate HDL/CST code yourself in this planning response.
- If code generation is needed, response_type must be "plan".
- If clarification is needed before planning, response_type must be "clarify" and needs_code_generation must be false.
- If no code generation is needed, response_type must be "answer".
- For Tang Nano 9K work, use only verified board resources from the board context.
- Mention unresolved board resources only as unavailable/gated, never as usable pins.
- If the user wrote /code, still create a plan and wait for approval.

Current project metadata:
{json.dumps(compact_metadata(project), indent=2)}

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Board context available to coder_agent:
{json.dumps(board_context, indent=2)}

User message:
{user_input}

Return one JSON object matching the schema.
response_type must be one of: answer, clarify, plan.
"""


def request_execution_plan(client, model_name, project, user_input, recent_messages):
    prompt = build_planning_prompt(project, user_input, recent_messages)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=planning_schema(),
        ),
    )
    if not response.text:
        raise ValueError("planning response was empty")

    return json.loads(response.text)


def print_list(title, items):
    print(f"{ACCENT}{title}:{Style.RESET_ALL}")
    if not items:
        print(f"{MUTED}- none{Style.RESET_ALL}")
        return

    for item in items:
        print(f"- {item}")


def format_plan_for_memory(plan):
    lines = [
        f"Expertise level: {plan.get('expertise_level', 'unknown')}",
        f"Board: {plan.get('board') or 'not selected'}",
        "Assumptions:",
    ]
    lines.extend(f"- {item}" for item in plan.get("assumptions", []))
    lines.append("Files to generate:")
    lines.extend(f"- {item}" for item in plan.get("files_to_generate", []))
    lines.append("Implementation plan:")
    lines.extend(f"- {item}" for item in plan.get("implementation_plan", []))
    return "\n".join(lines)


def show_execution_plan(plan):
    print(f"{AI_COLOR}Gemma plan:{Style.RESET_ALL}")
    if plan.get("mentor_response"):
        print(plan["mentor_response"])
        print()

    print(f"{ACCENT}Expertise level:{Style.RESET_ALL} {plan.get('expertise_level', 'unknown')}")
    print_list("Assumptions", plan.get("assumptions", []))
    print(f"{ACCENT}Board:{Style.RESET_ALL} {plan.get('board') or 'not selected'}")
    print_list("Files to be generated", plan.get("files_to_generate", []))
    print_list("Implementation plan", plan.get("implementation_plan", []))
    print()


def ask_for_approval():
    while True:
        answer = input(f"{USER_COLOR}Proceed with code generation? (Y/N):{Style.RESET_ALL} ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print(f"{MUTED}Please answer Y or N.{Style.RESET_ALL}")


def safe_name(value):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe.strip("._") or "project"


def code_extension_to_filename(language, index):
    normalized = language.lower()
    extension = {
        "verilog": "v",
        "systemverilog": "sv",
        "sv": "sv",
        "cst": "cst",
        "text": "txt",
    }.get(normalized, "txt")
    return f"artifact_{index}.{extension}"


def extract_named_code_blocks(coder_response):
    pattern = re.compile(
        r"(?:^|\n)\s*(?:File|Filename|Path)\s*:\s*([^\n]+)\n\s*```([A-Za-z0-9_+.-]*)\n(.*?)```",
        re.DOTALL | re.IGNORECASE,
    )
    blocks = []

    for index, match in enumerate(pattern.finditer(coder_response), start=1):
        filename = safe_name(match.group(1).strip().strip("`"))
        language = match.group(2).strip() or "text"
        code = match.group(3).strip() + "\n"
        blocks.append({"filename": filename, "language": language, "code": code, "index": index})

    if blocks:
        return blocks

    fallback = re.compile(r"```([A-Za-z0-9_+.-]*)\n(.*?)```", re.DOTALL)
    for index, match in enumerate(fallback.finditer(coder_response), start=1):
        language = match.group(1).strip() or "text"
        blocks.append(
            {
                "filename": code_extension_to_filename(language, index),
                "language": language,
                "code": match.group(2).strip() + "\n",
                "index": index,
            }
        )

    return blocks


def save_coder_artifacts(chat_name, coder_response):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = GENERATED_ROOT / safe_name(chat_name) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    response_path = output_dir / "coder_response.md"
    response_path.write_text(coder_response + "\n", encoding="utf-8")
    prompt_path = output_dir / "coder_prompt.md"
    prompt_path.write_text(get_last_coder_prompt() + "\n", encoding="utf-8")

    generated_files = [str(response_path), str(prompt_path)]
    for block in extract_named_code_blocks(coder_response):
        path = output_dir / block["filename"]
        path.write_text(block["code"], encoding="utf-8")
        generated_files.append(str(path))

    return {
        "output_dir": str(output_dir),
        "generated_files": generated_files,
    }


def build_review_prompt(plan, coder_response, artifacts):
    return f"""
You are Gemma, reviewing the local RTL coder's completed work for the user.

Explain:
- what was generated
- board resources used
- constraints used
- next available actions

Be concise and mentor-like. If the coder output appears incomplete, say so plainly.
Do not claim files exist unless they are listed in the artifact manifest.

Approved plan:
{json.dumps(plan, indent=2)}

Artifact manifest:
{json.dumps(artifacts, indent=2)}

Coder output:
{coder_response}
"""


def review_coder_completion(client, model_name, plan, coder_response, artifacts):
    response = client.models.generate_content(
        model=model_name,
        contents=build_review_prompt(plan, coder_response, artifacts),
    )
    return (response.text or "").strip()


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
    load_local_env()
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
        print(f"{MUTED} Gemma plans first; code generation runs only after Y approval.")
        print(f"{MUTED} Use '/code <request>' to request a coder plan ({DEFAULT_CODER_MODEL}).")
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

                project = projects.get(chat_name, default_project_metadata(chat_name))
                plan = request_execution_plan(
                    client,
                    model_name,
                    project,
                    user_input,
                    memory.get(chat_name, []),
                )

                if plan.get("response_type") == "clarify":
                    ai_response = plan.get("mentor_response", "").strip()
                    questions = plan.get("clarifying_questions", [])
                    if questions:
                        ai_response = (ai_response + "\n\n" if ai_response else "") + "Clarifying questions:\n"
                        ai_response += "\n".join(f"- {question}" for question in questions)
                    print(f"{AI_COLOR}Gemma:{Style.RESET_ALL} {ai_response}", end="")
                elif plan.get("response_type") == "plan" or plan.get("needs_code_generation"):
                    show_execution_plan(plan)
                    plan_memory = format_plan_for_memory(plan)

                    if not ask_for_approval():
                        ai_response = plan_memory + "\n\nCode generation was not run because approval was declined."
                        print(f"{MUTED}Code generation cancelled. We can revise the plan or keep discussing.\n{Style.RESET_ALL}", end="")
                    else:
                        coder_request = strip_coder_command(plan.get("coder_request") or user_input)
                        print(f"{AI_COLOR}Coder:{Style.RESET_ALL} running approved implementation with {DEFAULT_CODER_MODEL}...")
                        coder_response = ask_coder(
                            coder_request,
                            compact_metadata(project),
                            memory.get(chat_name, []),
                        )
                        artifacts = save_coder_artifacts(chat_name, coder_response)
                        review = review_coder_completion(client, model_name, plan, coder_response, artifacts)
                        ai_response = (
                            plan_memory
                            + "\n\nCoder output:\n"
                            + coder_response
                            + "\n\nGemma review:\n"
                            + review
                        )
                        print(f"{AI_COLOR}Gemma review:{Style.RESET_ALL} {review}", end="")
                else:
                    ai_response = plan.get("mentor_response", "").strip()
                    print(f"{AI_COLOR}Gemma:{Style.RESET_ALL} {ai_response}", end="")
                
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
