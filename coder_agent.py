import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent
BOARD_ROOT = PROJECT_ROOT / "hardware_bridge" / "boards" / "tang_nano_9k"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_CODER_MODEL = "codev-rtl:latest"
DEFAULT_BOARD_ID = "tang_nano_9k"
LAST_CODER_PROMPT = ""
FORBIDDEN_GOWIN_CONSTRAINT_TOKENS = (
    "set_property",
    "get_ports",
    "PACKAGE_PIN",
    "IOSTANDARD",
    ".xdc",
)


CODING_INTENT_KEYWORDS = {
    "bitstream",
    "blink",
    "blinker",
    "build",
    "cst",
    "constraint",
    "constraints",
    "counter",
    "create module",
    "design",
    "flash",
    "fpga",
    "generate",
    "hdl",
    "implement",
    "led",
    "module",
    "pin",
    "pins",
    "program",
    "rtl",
    "sdc",
    "simulate",
    "simulation",
    "testbench",
    "tang nano",
    "verilog",
    "vhdl",
}


def is_coder_request(message: str) -> bool:
    normalized = message.lower()

    if normalized.startswith("/code "):
        return True

    return any(keyword in normalized for keyword in CODING_INTENT_KEYWORDS)


def strip_coder_command(message: str) -> str:
    if message.lower().startswith("/code "):
        return message[6:].strip()

    return message


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_board_package_files(board_id: str = DEFAULT_BOARD_ID) -> Dict:
    if board_id != DEFAULT_BOARD_ID:
        raise ValueError(f"unsupported board package: {board_id}")

    files = {
        "board_profile": BOARD_ROOT / "board_profile.json",
        "interfaces": BOARD_ROOT / "interfaces.json",
        "constraints": BOARD_ROOT / "constraints.json",
        "validation_report": BOARD_ROOT / "validation_report.json",
    }

    return {
        key: {
            "path": str(path),
            "data": _load_json(path),
        }
        for key, path in files.items()
    }


def _compact_constraints(constraints: Dict) -> List[Dict]:
    compacted = []

    for item in constraints.get("constraints", []):
        compacted.append(
            {
                "interface": item.get("interface_id"),
                "signal": item.get("signal_name"),
                "direction": item.get("direction"),
                "package_pin": item.get("package_pin"),
                "board_net": item.get("board_net"),
                "io_standard": item.get("io_standard") or constraints.get("defaults", {}).get("io_standard"),
                "frequency_hz": item.get("frequency_hz"),
                "active_polarity": item.get("active_polarity"),
                "status": item.get("mapping_status"),
            }
        )

    return compacted


def load_board_context(board_id: str = DEFAULT_BOARD_ID) -> Dict:
    package = load_board_package_files(board_id)
    board_profile = package["board_profile"]["data"]
    interfaces = package["interfaces"]["data"]
    constraints = package["constraints"]["data"]
    validation = package["validation_report"]["data"]

    return {
        "board_id": board_id,
        "loaded_files": {name: item["path"] for name, item in package.items()},
        "board_profile": {
            "name": board_profile.get("name") or board_profile.get("board_name"),
            "fpga": board_profile.get("fpga"),
            "clock": board_profile.get("clock"),
            "toolchain": board_toolchain(board_profile),
            "programming": board_profile.get("programming"),
        },
        "constraints": _compact_constraints(constraints),
        "interfaces": [
            {
                "id": interface.get("id"),
                "name": interface.get("name"),
                "status": interface.get("status"),
                "signals": interface.get("signals", []),
                "unresolved": interface.get("unresolved", []),
                "metadata": interface.get("metadata", {}),
            }
            for interface in interfaces.get("interfaces", [])
        ],
        "validation": {
            "status": validation.get("validation_status"),
            "summary": validation.get("summary"),
            "readiness_score": validation.get("readiness_score"),
            "remaining_unresolved_signals": validation.get("remaining_unresolved_signals", []),
            "reference_board_gate": validation.get("reference_board_gate"),
        },
    }


def build_coder_prompt(user_request: str, project_metadata: Dict, recent_messages: Iterable[Dict]) -> str:
    board_context = load_board_context()
    recent_turns = []

    for message in list(recent_messages)[-8:]:
        role = message.get("role")
        text = message.get("text")
        if role and text:
            recent_turns.append({"role": role, "text": text[-1200:]})

    return f"""
You are the local RTL coder agent for PromptToChip.

Mission:
- Convert the user's hardware request into concrete HDL-oriented output.
- Use the Tang Nano 9K board knowledge package as the source of truth.
- Do not invent package pins or constraints.
- Do not use HDMI SDA, HDMI SCL, HDMI HPD, HDMI CEC, SD DAT1, SD DAT2, or SD card detect unless a verified mapping exists in the board context.
- Prefer simple, synthesizable Verilog when the user does not specify a language.
- Include top-level port names that match verified constraints when targeting the board.
- If you provide constraints, emit Gowin CST lines only for verified mappings.
- For Tang Nano 9K / Gowin, generate .cst files only. Never emit set_property, .xdc, get_ports, PACKAGE_PIN, or Xilinx constraints.
- For an LED blinker, name files exactly: led_blinker.v and led_blinker.cst.
- Label every code block with its intended filename using a line immediately before the block, such as: File: led_blinker.v
- If the request is underspecified, produce a safe minimal implementation and state assumptions briefly.

Current project metadata:
{json.dumps(project_metadata, indent=2)}

Recent conversation:
{json.dumps(recent_turns, indent=2)}

Tang Nano 9K board context:
{json.dumps(board_context, indent=2)}

User request:
{user_request}

Return the answer in this structure:
1. Short implementation note
2. HDL code, if applicable
3. Constraint snippets, if applicable
4. Verification or next command, if applicable
"""


def ask_coder(
    user_request: str,
    project_metadata: Dict,
    recent_messages: Iterable[Dict],
    model: str = DEFAULT_CODER_MODEL,
    timeout: int = 180,
) -> str:
    global LAST_CODER_PROMPT
    prompt = build_coder_prompt(user_request, project_metadata, recent_messages)
    LAST_CODER_PROMPT = prompt

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"coder agent HTTP error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"could not reach Ollama coder agent at {OLLAMA_URL}: {e.reason}") from e
    text = data.get("response", "").strip()

    if not text:
        raise RuntimeError("coder agent returned an empty response")

    return validate_or_repair_coder_output(user_request, text)


def get_last_coder_prompt() -> str:
    return LAST_CODER_PROMPT


def _find_constraint(constraints: Dict, signal_name: str) -> Dict:
    for item in constraints.get("constraints", []):
        if item.get("signal_name") == signal_name and item.get("mapping_status", "").startswith("verified"):
            return item

    raise ValueError(f"verified constraint not found for signal: {signal_name}")


def _cst_line(signal_name: str, constraint: Dict) -> str:
    return f'IO_LOC "{signal_name}" {constraint["package_pin"]};'


def _io_port_line(signal_name: str, constraint: Dict, default_io_standard: str) -> str:
    io_standard = constraint.get("io_standard") or default_io_standard
    drive = " DRIVE=8" if constraint.get("direction") == "output" else ""
    pull = " PULL_MODE=UP" if signal_name.startswith("led") or signal_name == "clk" else ""
    return f'IO_PORT "{signal_name}" IO_TYPE={io_standard}{pull}{drive};'


def _extract_verilog_module_name(verilog: str) -> Optional[str]:
    match = re.search(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\s*[\(#;]", verilog)
    if match:
        return match.group(1)

    return None


def board_toolchain(board_profile: Dict) -> str:
    top_level = board_profile.get("toolchain")
    if top_level:
        return top_level.lower()

    configured = board_profile.get("programming", {}).get("toolchain")
    if configured:
        return configured.lower()

    fpga_vendor = board_profile.get("fpga", {}).get("vendor", "")
    if fpga_vendor.lower() == "gowin":
        return "gowin"

    return ""


def is_led_blinker_request(user_request: str) -> bool:
    normalized = user_request.lower()
    return "led" in normalized and ("blink" in normalized or "blinker" in normalized)


def has_forbidden_gowin_constraint_syntax(text: str) -> bool:
    return any(token.lower() in text.lower() for token in FORBIDDEN_GOWIN_CONSTRAINT_TOKENS)


def build_led_blinker_verilog(clock_frequency_hz: int) -> str:
    return f"""module led_blinker (
    input wire clk,
    output reg [0:0] led
);

    localparam integer CLOCK_HZ = {clock_frequency_hz};
    localparam integer HALF_PERIOD_CYCLES = CLOCK_HZ / 2;

    reg [24:0] counter = 0;
    reg blink_state = 1'b0;

    always @(posedge clk) begin
        if (counter == HALF_PERIOD_CYCLES - 1) begin
            counter <= 0;
            blink_state <= ~blink_state;
        end else begin
            counter <= counter + 1'b1;
        end

        led[0] <= ~blink_state;
    end
endmodule
"""


def build_gowin_cst_for_signals(constraints: Dict, signal_names: Iterable[str]) -> str:
    default_io_standard = constraints.get("defaults", {}).get("io_standard", "LVCMOS33")
    lines = []

    for signal_name in signal_names:
        constraint = _find_constraint(constraints, signal_name)
        lines.append(_cst_line(signal_name, constraint))
        lines.append(_io_port_line(signal_name, constraint, default_io_standard))

    return "\n".join(lines) + "\n"


def build_led_blinker_response(user_request: str, raw_coder_response: str, repair_reason: str) -> str:
    package = load_board_package_files()
    board_profile = package["board_profile"]["data"]
    constraints = package["constraints"]["data"]
    clock_frequency_hz = board_profile["clock"]["default_frequency_hz"]

    verilog = build_led_blinker_verilog(clock_frequency_hz)
    cst = build_gowin_cst_for_signals(constraints, ["clk", "led[0]"])

    return f"""1. Short implementation note
The coder draft was validated before artifact export because {repair_reason}. The returned artifacts below are generated from the verified Tang Nano 9K board package for the Gowin toolchain.

2. HDL code
File: led_blinker.v
```verilog
{verilog}```

3. Constraint snippets
File: led_blinker.cst
```cst
{cst}```

4. Verification or next command
- Board: Tang Nano 9K
- Toolchain: Gowin
- Clock source: board_profile.json default clock, {clock_frequency_hz} Hz
- Verified mappings used: clk -> pin 52, led[0] -> pin 10
- Rejected raw coder output reason: {repair_reason}
"""


def validate_or_repair_coder_output(user_request: str, coder_response: str) -> str:
    package = load_board_package_files()
    board_profile = package["board_profile"]["data"]
    board_id = board_profile.get("board_id")
    toolchain = board_toolchain(board_profile)

    if board_id != DEFAULT_BOARD_ID or toolchain != "gowin":
        return coder_response

    if is_led_blinker_request(user_request):
        if has_forbidden_gowin_constraint_syntax(coder_response):
            reason = "the raw output contained Xilinx/XDC constraint syntax for a Gowin board"
        else:
            reason = "the Tang Nano 9K LED blinker flow requires deterministic Gowin CST generated from constraints.json"
        return build_led_blinker_response(user_request, coder_response, reason)

    if has_forbidden_gowin_constraint_syntax(coder_response):
        reason = "it contained Xilinx/XDC constraint syntax for a Gowin board"
        raise RuntimeError(f"coder output rejected: {reason}")

    xdc_filename = re.search(r"(?im)^\s*(?:file|filename|path)\s*:\s*.*\.xdc\s*$", coder_response)
    if xdc_filename:
        reason = "it attempted to generate an .xdc file for a Gowin board"
        raise RuntimeError(f"coder output rejected: {reason}")

    return coder_response


def generate_led_blinker_artifacts(
    user_request: str,
    output_dir: Path,
    project_metadata: Optional[Dict] = None,
    recent_messages: Optional[Iterable[Dict]] = None,
) -> Dict:
    package = load_board_package_files()
    board_profile = package["board_profile"]["data"]
    interfaces = package["interfaces"]["data"]
    constraints = package["constraints"]["data"]

    clock_frequency_hz = board_profile["clock"]["default_frequency_hz"]
    clock = _find_constraint(constraints, "clk")
    led0 = _find_constraint(constraints, "led[0]")
    default_io_standard = constraints.get("defaults", {}).get("io_standard", "LVCMOS33")

    coder_response = ask_coder(
        user_request,
        project_metadata or {},
        recent_messages or [],
    )
    coder_prompt = get_last_coder_prompt()

    verilog = build_led_blinker_verilog(clock_frequency_hz)

    cst_lines = [
        _cst_line("clk", clock),
        _io_port_line("clk", clock, default_io_standard),
        _cst_line("led[0]", led0),
        _io_port_line("led[0]", led0, default_io_standard),
    ]
    cst = "\n".join(cst_lines) + "\n"

    output_dir.mkdir(parents=True, exist_ok=True)
    blink_v = output_dir / "led_blinker.v"
    blink_cst = output_dir / "led_blinker.cst"
    coder_response_path = output_dir / "coder_response.md"
    coder_prompt_path = output_dir / "coder_prompt.md"

    blink_v.write_text(verilog, encoding="utf-8")
    blink_cst.write_text(cst, encoding="utf-8")
    coder_response_path.write_text(coder_response + "\n", encoding="utf-8")
    coder_prompt_path.write_text(coder_prompt + "\n", encoding="utf-8")

    clock_interface = next(interface for interface in interfaces["interfaces"] if interface["id"] == "clock")
    led_interface = next(interface for interface in interfaces["interfaces"] if interface["id"] == "leds")

    return {
        "files": {
            "led_blinker_v": str(blink_v),
            "led_blinker_cst": str(blink_cst),
            "coder_response": str(coder_response_path),
            "coder_prompt": str(coder_prompt_path),
        },
        "board_package_loaded": {
            "board_profile": package["board_profile"]["path"],
            "interfaces": package["interfaces"]["path"],
            "constraints": package["constraints"]["path"],
        },
        "interfaces_used": [
            {
                "id": "clock",
                "signal": "clk",
                "package_pin": clock["package_pin"],
                "frequency_hz": clock_frequency_hz,
                "source": clock_interface["status"],
            },
            {
                "id": "leds",
                "signal": "led[0]",
                "package_pin": led0["package_pin"],
                "active_polarity": led0.get("active_polarity"),
                "source": led_interface["status"],
            },
        ],
        "constraints_generated": cst_lines,
        "coder_response_chars": len(coder_response),
        "verilog_module": _extract_verilog_module_name(verilog),
    }
