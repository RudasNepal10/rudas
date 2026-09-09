#!/usr/bin/env python3
"""Anonymous SMS sender for Nepal 🇳🇵

Sends anonymous SMS to Nepali numbers (+977) using Twilio.
The recipient sees a custom sender name instead of a phone number.
Supports NTC, Ncell, and Smart Cell numbers.

Alphanumeric sender IDs are fully supported in Nepal.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from getpass import getpass
from pathlib import Path
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# --- Nepal phone number patterns ---
# NTC (Nepal Telecom): 984, 985, 986, 974, 975
# Ncell: 980, 981, 982, 961, 962
# Smart Cell: 988, 972
NEPAL_MOBILE = re.compile(r"^(98[0-8]|97[2-5]|96[12])\d{7}$")
MAX_MESSAGE_LENGTH = 1600
MAX_SENDER_ID_LENGTH = 11

DOTENV_KEYS = {
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_MESSAGING_SERVICE_SID",
}

# Color codes for terminal
class Color:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


BANNER = f"""{Color.RED}
    ██████╗ ██╗   ██╗██████╗  █████╗ ███████╗
    ██╔══██╗██║   ██║██╔══██╗██╔══██╗██╔════╝
    ██████╔╝██║   ██║██║  ██║███████║███████╗
    ██╔══██╗██║   ██║██║  ██║██╔══██║╚════██║
    ██║  ██║╚██████╔╝██████╔╝██║  ██║███████║
    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝{Color.RESET}
    {Color.CYAN}Anonymous SMS for Nepal 🇳🇵{Color.RESET}
    {Color.DIM}Powered by Twilio | NTC • Ncell • Smart Cell{Color.RESET}
"""

MESSAGE_TEMPLATES = {
    "1": ("Secret Admirer 💌", "Someone secretly admires you. They think about you more than you know. 💫"),
    "2": ("Anonymous Tip 🔍", "This is an anonymous tip. Please be careful about who you trust around you."),
    "3": ("Mystery Friend 👤", "You have a secret friend watching over you. Stay safe and keep smiling! 😊"),
    "4": ("Wake Up Call ⏰", "This is your anonymous wake up call! Time to rise and shine! ☀️"),
    "5": ("Truth Bomb 💣", "Someone wants you to know: You're stronger than you think. Keep going! 💪"),
}


def fail(message: str) -> NoReturn:
    print(f"\n{Color.RED}[✗] {message}{Color.RESET}", file=sys.stderr)
    raise SystemExit(1)


def success(message: str) -> None:
    print(f"{Color.GREEN}[✓] {message}{Color.RESET}")


def info(message: str) -> None:
    print(f"{Color.CYAN}[i] {message}{Color.RESET}")


def warn(message: str) -> None:
    print(f"{Color.YELLOW}[!] {message}{Color.RESET}")


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load Twilio settings from a .env file."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"Could not read {path}: {error}")

    for _, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or key not in DOTENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value:
            os.environ.setdefault(key, value)


def read_setting(name: str, prompt: str, *, secret: bool = False) -> str:
    """Read a setting from env or prompt the user."""
    value = os.getenv(name, "").strip()
    if value:
        return value
    reader = getpass if secret else input
    value = reader(f"  {prompt}: ").strip()
    if not value:
        fail(f"{name} is required.")
    return value


def identify_carrier(number: str) -> str:
    """Identify the Nepali carrier from the number prefix."""
    prefix = number[:3]
    ntc_prefixes = {"984", "985", "986", "974", "975"}
    ncell_prefixes = {"980", "981", "982", "961", "962"}
    smart_prefixes = {"988", "972"}

    if prefix in ntc_prefixes:
        return "NTC (Nepal Telecom)"
    elif prefix in ncell_prefixes:
        return "Ncell"
    elif prefix in smart_prefixes:
        return "Smart Cell"
    return "Unknown Carrier"


def read_nepal_number() -> str:
    """Read and validate a Nepali phone number."""
    print(f"\n{Color.BOLD}  Enter recipient's Nepal number:{Color.RESET}")
    print(f"  {Color.DIM}Format: 98XXXXXXXX (10 digits, no +977){Color.RESET}")
    number = input(f"\n  📱 Number: ").strip()

    # Remove common prefixes users might add
    number = number.replace(" ", "").replace("-", "")
    if number.startswith("+977"):
        number = number[4:]
    elif number.startswith("977"):
        number = number[3:]
    elif number.startswith("0"):
        number = number[1:]

    if not NEPAL_MOBILE.fullmatch(number):
        fail(
            "Invalid Nepal mobile number.\n"
            "    Supported: NTC (984/985/986), Ncell (980/981/982), Smart (988)\n"
            "    Example: 9841234567"
        )

    carrier = identify_carrier(number)
    success(f"Valid {carrier} number detected")
    return f"+977{number}"


def validate_sender_id(sender_id: str) -> str:
    """Validate alphanumeric sender ID."""
    if not sender_id:
        fail("Sender ID cannot be empty.")
    if len(sender_id) > MAX_SENDER_ID_LENGTH:
        fail(f"Sender ID must be {MAX_SENDER_ID_LENGTH} characters or fewer.")
    if not re.match(r"^[a-zA-Z0-9 ]+$", sender_id):
        fail("Sender ID can only contain letters, numbers, and spaces.")
    if sender_id.isdigit():
        fail("Sender ID must contain at least one letter.")
    return sender_id


def choose_sender_id() -> str:
    """Let user pick or type a sender ID."""
    print(f"\n{Color.BOLD}  Choose sender name (what recipient will see):{Color.RESET}")
    presets = [
        ("Anonymous", "Generic anonymous"),
        ("Unknown", "Mystery sender"),
        ("Secret", "Secret message vibe"),
        ("InfoAlert", "Looks like an alert"),
        ("HiddenFan", "Secret admirer style"),
    ]
    for i, (name, desc) in enumerate(presets, 1):
        print(f"  {Color.CYAN}[{i}]{Color.RESET} {name:12s} {Color.DIM}— {desc}{Color.RESET}")
    print(f"  {Color.CYAN}[6]{Color.RESET} Custom       {Color.DIM}— Type your own{Color.RESET}")

    choice = input(f"\n  Choice [1-6]: ").strip()

    if choice in ("1", "2", "3", "4", "5"):
        sender_id = presets[int(choice) - 1][0]
    elif choice == "6":
        sender_id = input(f"  Custom sender name (max 11 chars): ").strip()
    else:
        sender_id = "Anonymous"
        warn("Invalid choice, defaulting to 'Anonymous'")

    return validate_sender_id(sender_id)


def choose_message() -> str:
    """Let user pick a template or type a custom message."""
    print(f"\n{Color.BOLD}  Choose message:{Color.RESET}")
    for key, (title, preview) in MESSAGE_TEMPLATES.items():
        print(f"  {Color.CYAN}[{key}]{Color.RESET} {title}")
        print(f"      {Color.DIM}\"{preview[:60]}...\"{Color.RESET}" if len(preview) > 60 else f"      {Color.DIM}\"{preview}\"{Color.RESET}")
    print(f"  {Color.CYAN}[6]{Color.RESET} ✍️  Write custom message")

    choice = input(f"\n  Choice [1-6]: ").strip()

    if choice in MESSAGE_TEMPLATES:
        _, message = MESSAGE_TEMPLATES[choice]
        print(f"\n  {Color.DIM}Message: \"{message}\"{Color.RESET}")
        return message
    else:
        message = input(f"\n  ✍️  Your message: ").strip()
        if not message:
            fail("Message cannot be empty.")
        if len(message) > MAX_MESSAGE_LENGTH:
            fail(f"Message must be at most {MAX_MESSAGE_LENGTH} characters.")
        return message


def send_sms(
    account_sid: str,
    auth_token: str,
    to_number: str,
    message: str,
    *,
    messaging_service_sid: str | None = None,
    sender_id: str | None = None,
) -> str:
    """Send SMS via Twilio API. Returns the message SID."""
    credentials = f"{account_sid}:{auth_token}".encode("utf-8")
    authorization = base64.b64encode(credentials).decode("ascii")

    payload = {"To": to_number, "Body": message}

    if messaging_service_sid:
        payload["MessagingServiceSid"] = messaging_service_sid
    elif sender_id:
        payload["From"] = sender_id
    else:
        fail("No sender configured.")

    body = urlencode(payload).encode("utf-8")
    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    request = Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            details = json.loads(error.read().decode("utf-8")).get("message", "")
        except (UnicodeDecodeError, json.JSONDecodeError):
            details = ""
        fail(
            f"Twilio rejected the message (HTTP {error.code})"
            + (f": {details}" if details else ".")
        )
    except URLError as error:
        fail(f"Could not reach Twilio: {error.reason}")

    message_sid = result.get("sid")
    if not message_sid:
        fail("Twilio returned an unexpected response.")
    return message_sid


def loading_animation(text: str, duration: float = 2.0) -> None:
    """Show a simple loading animation."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r  {Color.CYAN}{frames[i % len(frames)]} {text}{Color.RESET}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r  {' ' * (len(text) + 4)}\r", end="")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send anonymous SMS to Nepal numbers using Twilio."
    )
    parser.add_argument("--sender-id", default=None, help="Sender name (max 11 chars)")
    parser.add_argument("--to", default=None, help="Recipient Nepal number (e.g. 9841234567)")
    parser.add_argument("--message", "-m", default=None, help="Message text")
    args = parser.parse_args()

    load_dotenv()

    # --- Banner ---
    print(BANNER)

    # --- Twilio credentials ---
    print(f"{Color.BOLD}  ── Twilio Credentials ──{Color.RESET}")
    account_sid = read_setting("TWILIO_ACCOUNT_SID", "Account SID")
    auth_token = read_setting("TWILIO_AUTH_TOKEN", "Auth Token", secret=True)
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "").strip()

    success("Credentials loaded")

    # --- Sender ID ---
    sender_id = args.sender_id
    if not messaging_service_sid and not sender_id:
        sender_id = choose_sender_id()
    elif sender_id:
        sender_id = validate_sender_id(sender_id)

    # --- Recipient ---
    if args.to:
        number = args.to.replace(" ", "").replace("-", "")
        if number.startswith("+977"):
            number = number[4:]
        elif number.startswith("977"):
            number = number[3:]
        if not NEPAL_MOBILE.fullmatch(number):
            fail("Invalid Nepal number.")
        to_number = f"+977{number}"
        carrier = identify_carrier(number)
        success(f"Target: {to_number} ({carrier})")
    else:
        to_number = read_nepal_number()

    # --- Message ---
    if args.message:
        message = args.message
        if len(message) > MAX_MESSAGE_LENGTH:
            fail(f"Message too long (max {MAX_MESSAGE_LENGTH} chars).")
    else:
        message = choose_message()

    # --- Confirmation ---
    sender_display = sender_id if sender_id else f"MessagingService"
    print(f"\n  {Color.BOLD}{'═' * 46}{Color.RESET}")
    print(f"  {Color.BOLD}  📨 ANONYMOUS MESSAGE PREVIEW{Color.RESET}")
    print(f"  {Color.BOLD}{'═' * 46}{Color.RESET}")
    print(f"  {Color.YELLOW}  Sender:    {sender_display}{Color.RESET}")
    print(f"  {Color.CYAN}  To:        {to_number}{Color.RESET}")
    print(f"  {Color.WHITE}  Message:   {message}{Color.RESET}")
    print(f"  {Color.BOLD}{'═' * 46}{Color.RESET}")

    confirmation = input(f"\n  {Color.BOLD}Type SEND to fire 🚀: {Color.RESET}").strip()
    if confirmation != "SEND":
        warn("Cancelled — no message sent.")
        return 0

    # --- Send ---
    loading_animation("Sending anonymous message to Nepal...")

    message_sid = send_sms(
        account_sid,
        auth_token,
        to_number,
        message,
        messaging_service_sid=messaging_service_sid if messaging_service_sid else None,
        sender_id=sender_id if not messaging_service_sid else None,
    )

    print()
    success(f"Message sent successfully! 🎉")
    print(f"  {Color.DIM}SID: {message_sid}{Color.RESET}")
    print(f"  {Color.DIM}Recipient sees sender as: \"{sender_display}\"{Color.RESET}")
    print(f"  {Color.DIM}They CANNOT reply or trace you.{Color.RESET}")
    print()
    return 0


if __name__ == "__main__":
    try:
        # Enable ANSI colors on Windows
        if sys.platform == "win32":
            os.system("")
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}  Cancelled — no message sent.{Color.RESET}")
        raise SystemExit(130)
