"""
Step 1: USB Device Detection

List available USB/serial devices and extract VID/PID.
Step 2: Recognize known boards from profiles and flag unknown FPGA/JTAG candidates.
Step 3: Confirm FPGA silicon with JTAG IDCODE when available.
"""

import json
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_OSS_CAD_ROOT = PROJECT_ROOT / "tools" / "oss-cad-suite"
LOCAL_OPENFPGALOADER = LOCAL_OSS_CAD_ROOT / "bin" / "openFPGALoader.exe"

BOARD_PROFILES = [
    {
        "board_name": "Tang Nano 9K",
        "vendor": "Sipeed",
        "vid": "0403",
        "pid": "6010",
        "serial_hint": "FACTORYAIOT_PRO",
        "fpga_part": "GW1NR-9C",
        "clock_frequency": "27 MHz",
        "expected_jtag_idcode": "0x0100481b",
        "openfpgaloader_board": "tangnano9k",
    }
]

FPGA_USB_HINTS = [
    "cmsis-dap",
    "digilent",
    "ft2232",
    "ft232",
    "ftdi",
    "gowin",
    "j-link",
    "jtag",
    "lattice",
    "openocd",
    "serial converter",
    "usb blaster",
    "xilinx",
]

PROGRAMMER_VIDS = {
    "0403": "FTDI",
    "09fb": "Intel/Altera USB-Blaster",
    "1366": "SEGGER J-Link",
    "15ba": "Olimex/OpenOCD",
    "2a19": "Digilent",
    "2e8a": "Raspberry Pi debug probe",
}

JTAG_IDCODES = {
    "0x0100481b": {
        "vendor": "Gowin",
        "fpga_part": "GW1NR-9C",
        "board_hint": "Tang Nano 9K",
    }
}


def resolve_openfpgaloader() -> Optional[Path]:
    if LOCAL_OPENFPGALOADER.exists():
        return LOCAL_OPENFPGALOADER

    return None


def build_oss_cad_environment() -> Dict[str, str]:
    env = os.environ.copy()

    if LOCAL_OSS_CAD_ROOT.exists():
        root = str(LOCAL_OSS_CAD_ROOT)
        env["YOSYSHQ_ROOT"] = root + "\\"
        env["SSL_CERT_FILE"] = str(LOCAL_OSS_CAD_ROOT / "etc" / "cacert.pem")
        env["PATH"] = (
            str(LOCAL_OSS_CAD_ROOT / "bin")
            + os.pathsep
            + str(LOCAL_OSS_CAD_ROOT / "lib")
            + os.pathsep
            + env.get("PATH", "")
        )
        env["PYTHON_EXECUTABLE"] = str(LOCAL_OSS_CAD_ROOT / "lib" / "python3.exe")
        env["QT_PLUGIN_PATH"] = str(LOCAL_OSS_CAD_ROOT / "lib" / "qt5" / "plugins")
        env["QT_LOGGING_RULES"] = "*=false"
        env["GTK_EXE_PREFIX"] = root
        env["GTK_DATA_PREFIX"] = root
        env["GDK_PIXBUF_MODULEDIR"] = str(
            LOCAL_OSS_CAD_ROOT / "lib" / "gdk-pixbuf-2.0" / "2.10.0" / "loaders"
        )
        env["GDK_PIXBUF_MODULE_FILE"] = str(
            LOCAL_OSS_CAD_ROOT / "lib" / "gdk-pixbuf-2.0" / "2.10.0" / "loaders.cache"
        )
        env["OPENFPGALOADER_SOJ_DIR"] = str(LOCAL_OSS_CAD_ROOT / "share" / "openFPGALoader")

    return env


def get_windows_usb_devices() -> List[Dict]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        """
        Get-PnpDevice -PresentOnly |
        Where-Object {$_.Class -in @('Ports', 'USB', 'USBDevice')} |
        Select-Object FriendlyName, InstanceId, Class |
        ConvertTo-Json -Depth 1
        """,
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)

        if not result.stdout.strip():
            return []

        data = json.loads(result.stdout)

        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data

        return []
    except Exception as e:
        print(f"Error: {e}")
        return []


def extract_vid_pid(instance_id: str) -> Tuple[Optional[str], Optional[str]]:
    match = re.search(r"VID[_+]([0-9A-Fa-f]{4}).*PID[_+]([0-9A-Fa-f]{4})", instance_id)

    if match:
        vid = match.group(1).lower()
        pid = match.group(2).lower()
        return vid, pid

    return None, None


def extract_com_port(device_name: str) -> Optional[str]:
    match = re.search(r"\((COM\d+)\)", device_name)

    if match:
        return match.group(1)

    return None


def normalize_idcode(idcode: str) -> str:
    return f"0x{int(idcode, 16):08x}"


def build_unknown_board_name(vid: str, pid: str, vendor_hint: str) -> str:
    if vendor_hint:
        return f"Unknown FPGA/JTAG device ({vendor_hint} {vid}:{pid})"

    return f"Unknown FPGA/JTAG device ({vid}:{pid})"


def is_fpga_usb_candidate(device: Dict) -> bool:
    name = device.get("FriendlyName") or ""
    instance_id = device.get("InstanceId") or ""
    vid, pid = extract_vid_pid(instance_id)

    if not vid or not pid:
        return False

    searchable_text = f"{name} {instance_id}".lower()

    if vid in PROGRAMMER_VIDS:
        return True

    return any(hint in searchable_text for hint in FPGA_USB_HINTS)


def identify_boards(devices: List[Dict]) -> List[Dict]:
    detected_boards = []
    known_vid_pids = set()

    for profile in BOARD_PROFILES:
        matched_devices = []
        com_ports = []
        same_vid_pid_devices = []
        serial_hint_seen = False

        for device in devices:
            name = device.get("FriendlyName") or "Unknown"
            instance_id = device.get("InstanceId") or ""
            vid, pid = extract_vid_pid(instance_id)

            if vid != profile["vid"] or pid != profile["pid"]:
                continue

            same_vid_pid_devices.append(device)
            serial_hint = profile.get("serial_hint")
            if not serial_hint or serial_hint in instance_id:
                serial_hint_seen = True

        if not same_vid_pid_devices or not serial_hint_seen:
            continue

        for device in same_vid_pid_devices:
            name = device.get("FriendlyName") or "Unknown"
            matched_devices.append(device)
            known_vid_pids.add((profile["vid"], profile["pid"]))

            com_port = extract_com_port(name)
            if com_port and com_port not in com_ports:
                com_ports.append(com_port)

        if matched_devices:
            detected_boards.append(
                {
                    **profile,
                    "detection_kind": "known_profile",
                    "matched_devices": matched_devices,
                    "com_ports": com_ports,
                }
            )

    unknown_groups = {}

    for device in devices:
        instance_id = device.get("InstanceId") or ""
        vid, pid = extract_vid_pid(instance_id)

        if not vid or not pid or (vid, pid) in known_vid_pids:
            continue
        if not is_fpga_usb_candidate(device):
            continue

        unknown_groups.setdefault((vid, pid), []).append(device)

    for (vid, pid), matched_devices in unknown_groups.items():
        com_ports = []
        vendor_hint = PROGRAMMER_VIDS.get(vid, "")

        for device in matched_devices:
            name = device.get("FriendlyName") or "Unknown"
            com_port = extract_com_port(name)
            if com_port and com_port not in com_ports:
                com_ports.append(com_port)

        detected_boards.append(
            {
                "board_name": build_unknown_board_name(vid, pid, vendor_hint),
                "vendor": vendor_hint or "Unknown",
                "vid": vid,
                "pid": pid,
                "serial_hint": "",
                "fpga_part": "Unknown",
                "clock_frequency": "Unknown",
                "expected_jtag_idcode": "",
                "openfpgaloader_board": "",
                "detection_kind": "usb_candidate",
                "matched_devices": matched_devices,
                "com_ports": com_ports,
            }
        )

    return detected_boards


def query_jtag_idcode(board: Optional[Dict] = None) -> Tuple[Optional[str], str]:
    openfpgaloader = resolve_openfpgaloader()
    command = [str(openfpgaloader) if openfpgaloader else "openFPGALoader", "--detect"]
    board_arg = board.get("openfpgaloader_board") if board else None

    if board_arg:
        command.extend(["-b", board_arg])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=build_oss_cad_environment(),
        )
    except FileNotFoundError:
        return None, "openFPGALoader_not_found"
    except subprocess.TimeoutExpired:
        return None, "jtag_detect_timeout"
    except OSError:
        return None, "jtag_detect_failed"

    output = result.stdout + result.stderr

    if result.returncode != 0:
        output_lower = output.lower()
        if "unable to open ftdi device" in output_lower or "can't open device" in output_lower:
            return None, "jtag_usb_open_failed"
        return None, "jtag_detect_failed"

    match = re.search(r"0x[0-9A-Fa-f]+", output)

    if not match:
        return None, "idcode_not_found"

    return normalize_idcode(match.group(0)), "idcode_found"


def add_jtag_confirmation(boards: List[Dict]) -> List[Dict]:
    if not boards:
        idcode, jtag_status = query_jtag_idcode()

        if not idcode:
            return boards

        silicon_info = JTAG_IDCODES.get(idcode, {})
        return [
            {
                "board_name": silicon_info.get("board_hint", "Unknown JTAG FPGA device"),
                "vendor": silicon_info.get("vendor", "Unknown"),
                "vid": "unknown",
                "pid": "unknown",
                "serial_hint": "",
                "fpga_part": silicon_info.get("fpga_part", "Unknown"),
                "clock_frequency": "Unknown",
                "expected_jtag_idcode": "",
                "openfpgaloader_board": "",
                "detection_kind": "jtag_only",
                "matched_devices": [],
                "com_ports": [],
                "tier_1_status": "not_seen_on_usb_scan",
                "tier_2_status": jtag_status,
                "jtag_idcode": idcode,
                "silicon_info": silicon_info,
                "confirmation": "jtag_detected",
            }
        ]

    for board in boards:
        idcode, jtag_status = query_jtag_idcode(board)
        board["tier_1_status"] = "candidate_detected"
        board["tier_2_status"] = jtag_status
        board["jtag_idcode"] = idcode or ""
        board["confirmation"] = "candidate"

        if not idcode:
            continue

        expected_idcode = board.get("expected_jtag_idcode", "").lower()
        board["silicon_info"] = JTAG_IDCODES.get(idcode, {})

        if expected_idcode and idcode == expected_idcode:
            board["tier_2_status"] = "jtag_confirmed"
            board["confirmation"] = "confirmed"
        elif expected_idcode:
            board["tier_2_status"] = "jtag_mismatch"
            board["confirmation"] = "mismatch"
        else:
            board["confirmation"] = "jtag_detected"

    return boards


def print_usb_devices(devices: List[Dict]) -> None:
    print(f"Found {len(devices)} device(s):")
    print()

    for index, device in enumerate(devices, start=1):
        name = device.get("FriendlyName") or "Unknown"
        instance_id = device.get("InstanceId") or "Unknown"
        device_class = device.get("Class") or "Unknown"
        vid, pid = extract_vid_pid(instance_id)

        print(f"[{index}] {name}")
        print(f"    Class: {device_class}")
        print(f"    Instance ID: {instance_id}")

        if vid and pid:
            print(f"    VID:PID = {vid}:{pid}")
        else:
            print("    VID:PID = Could not extract")

        print()


def print_detected_boards(boards: List[Dict]) -> None:
    print("=" * 70)
    print("FPGA / JTAG Board Candidates")
    print("=" * 70)
    print()

    if not boards:
        print("No FPGA/JTAG board candidates detected.")
        print()
        return

    for index, board in enumerate(boards, start=1):
        print(f"[{index}] {board['board_name']}")
        print(f"    Detection: {board.get('detection_kind', 'unknown')}")
        print(f"    Vendor: {board['vendor']}")
        print(f"    FPGA: {board['fpga_part']}")
        print(f"    Clock: {board['clock_frequency']}")
        print(f"    VID:PID = {board['vid']}:{board['pid']}")

        if board.get("serial_hint"):
            print(f"    Serial Hint: {board['serial_hint']}")

        print(f"    Tier 1: {board.get('tier_1_status', 'candidate_detected')}")
        print(f"    Tier 2: {board.get('tier_2_status', 'not_checked')}")
        print(f"    Confirmation: {board.get('confirmation', 'candidate')}")

        if board.get("jtag_idcode"):
            print(f"    JTAG IDCODE: {board['jtag_idcode']}")

        print(f"    COM Ports: {', '.join(board['com_ports']) if board['com_ports'] else 'none'}")

        if board["matched_devices"]:
            print("    Matched Devices:")

            for device in board["matched_devices"]:
                name = device.get("FriendlyName") or "Unknown"
                device_class = device.get("Class") or "Unknown"
                print(f"      - {name} [{device_class}]")

        print()


def scan_hardware() -> None:
    print()
    print("=" * 70)
    print("USB Device Detection")
    print("=" * 70)
    print()

    if platform.system() != "Windows":
        print("Currently only Windows is supported.")
        print("Add Linux/macOS detection later.")
        print()
        return

    devices = get_windows_usb_devices()

    if not devices:
        print("No USB or serial devices detected.")
        print()
        return

    boards = identify_boards(devices)
    boards = add_jtag_confirmation(boards)

    print_usb_devices(devices)
    print_detected_boards(boards)


if __name__ == "__main__":
    scan_hardware()
