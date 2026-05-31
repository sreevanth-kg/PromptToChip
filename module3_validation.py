import json
import re
import sys
from pathlib import Path

from coder_agent import (
    generate_led_blinker_artifacts,
    is_coder_request,
    load_board_package_files,
)


TEST_PROMPT = "Create a Tang Nano 9K LED blinker running at 1 Hz."
OUTPUT_DIR = Path("test_outputs") / "module3_tang_nano_9k_led_blinker"


def verified_constraint_map(constraints):
    return {
        item["signal_name"]: item
        for item in constraints.get("constraints", [])
        if item.get("mapping_status", "").startswith("verified")
    }


def parse_cst_locations(cst_text):
    matches = re.findall(r'IO_LOC\s+"([^"]+)"\s+([0-9,]+)\s*;', cst_text)
    return [{"signal": signal, "package_pin": pin} for signal, pin in matches]


def validate_generated_artifacts(artifacts, board_package):
    failures = []
    constraints = board_package["constraints"]["data"]
    board_profile = board_package["board_profile"]["data"]
    verified = verified_constraint_map(constraints)

    blink_v = Path(artifacts["files"]["led_blinker_v"])
    blink_cst = Path(artifacts["files"]["led_blinker_cst"])
    coder_response = Path(artifacts["files"]["coder_response"])
    coder_prompt = Path(artifacts["files"]["coder_prompt"])
    generated_files = [blink_v, blink_cst, coder_response, coder_prompt]

    for path in generated_files:
        if not path.exists():
            failures.append(f"missing generated file: {path}")

    hdl_text = blink_v.read_text(encoding="utf-8") if blink_v.exists() else ""
    cst_text = blink_cst.read_text(encoding="utf-8") if blink_cst.exists() else ""
    cst_locations = parse_cst_locations(cst_text)

    for location in cst_locations:
        signal = location["signal"]
        package_pin = location["package_pin"]
        verified_item = verified.get(signal)

        if not verified_item:
            failures.append(f"constraint references unverified signal: {signal}")
            continue

        if str(verified_item.get("package_pin")) != package_pin:
            failures.append(
                f"constraint pin mismatch for {signal}: generated {package_pin}, expected {verified_item.get('package_pin')}"
            )

    expected_clock_hz = board_profile["clock"]["default_frequency_hz"]
    if f"CLOCK_HZ = {expected_clock_hz}" not in hdl_text:
        failures.append(f"HDL does not use board_profile clock frequency {expected_clock_hz}")

    if "input wire clk" not in hdl_text:
        failures.append("HDL does not expose verified board clock port clk")

    if "output reg [0:0] led" not in hdl_text:
        failures.append("HDL does not expose verified LED vector port led[0:0]")

    if "led[0] <= ~blink_state" not in hdl_text:
        failures.append("HDL does not account for active-low LED behavior")

    required_signals = {"clk", "led[0]"}
    generated_signals = {location["signal"] for location in cst_locations}
    missing_required = sorted(required_signals - generated_signals)
    if missing_required:
        failures.append(f"missing expected verified constraints: {missing_required}")

    if 'IO_PORT "led[0]" IO_TYPE=LVCMOS18' not in cst_text:
        failures.append("LED constraint does not use hardware-validated LVCMOS18 for bank 3")

    if 'IO_PORT "led[0]" IO_TYPE=LVCMOS33' in cst_text:
        failures.append("LED constraint still contains invalid LVCMOS33 for bank 3")

    return {
        "success": not failures,
        "failures": failures,
        "generated_files": [str(path) for path in generated_files],
        "constraints_generated": cst_locations,
        "verified_constraint_signals_available": sorted(verified.keys()),
        "clock_frequency_hz_expected": expected_clock_hz,
        "clock_frequency_hz_found_in_hdl": f"CLOCK_HZ = {expected_clock_hz}" in hdl_text,
    }


def run_validation():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    board_package = load_board_package_files()
    main_agent_routed = is_coder_request(TEST_PROMPT)

    report = {
        "module": "module_3",
        "test_name": "coder_agent_board_package_end_to_end",
        "prompt": TEST_PROMPT,
        "output_dir": str(OUTPUT_DIR),
        "main_agent_routes_request_to_coder_agent": main_agent_routed,
        "board_package_loaded": {
            "board_profile": board_package["board_profile"]["path"],
            "interfaces": board_package["interfaces"]["path"],
            "constraints": board_package["constraints"]["path"],
        },
        "interfaces_used": [],
        "constraints_generated": [],
        "files_generated": [],
        "success": False,
        "failures": [],
    }

    if not main_agent_routed:
        report["failures"].append("main agent routing heuristic did not delegate prompt to coder_agent")
    else:
        try:
            artifacts = generate_led_blinker_artifacts(
                TEST_PROMPT,
                OUTPUT_DIR,
                project_metadata={
                    "project_name": "module_3_validation",
                    "board": "Tang Nano 9K",
                    "hdl_language": "Verilog",
                    "clock_frequency": "27 MHz",
                    "status": "coding",
                },
                recent_messages=[],
            )
            validation = validate_generated_artifacts(artifacts, board_package)

            report["interfaces_used"] = artifacts["interfaces_used"]
            report["constraints_generated"] = validation["constraints_generated"]
            report["files_generated"] = validation["generated_files"]
            report["coder_response_chars"] = artifacts["coder_response_chars"]
            report["artifact_evidence"] = {
                "clock_frequency_from_board_profile_hz": validation["clock_frequency_hz_expected"],
                "clock_frequency_found_in_hdl": validation["clock_frequency_hz_found_in_hdl"],
                "constraints_selected_from_verified_board_map": validation["success"],
            }
            report["failures"].extend(validation["failures"])
        except Exception as e:
            report["failures"].append(str(e))

    report["success"] = not report["failures"]
    report_path = OUTPUT_DIR / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(run_validation())
