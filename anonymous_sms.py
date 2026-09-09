#!/usr/bin/env python3
"""Send an anonymous SMS using Twilio Messaging Service.

Uses a Twilio Messaging Service with an alphanumeric sender ID so the
recipient sees a custom name (e.g. "Anonymous") instead of a phone number.
This makes the message sender untraceable from the recipient's side.

NOTE: Alphanumeric sender IDs are NOT supported in all countries.
      The US and Canada do NOT support them. They work in most other
      countries (UK, India, Nepal, Australia, etc.).
      See: https://www.twilio.com/docs/messaging/guides/alphanumeric-sender-id
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from getpass import getpass
from pathlib import Path
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


E164_NUMBER = re.compile(r"^\+[1-9]\d{7,14}$")
MAX_MESSAGE_LENGTH = 1600
MAX_SENDER_ID_LENGTH = 11

DOTENV_KEYS = {
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_MESSAGING_SERVICE_SID",
    "TWILIO_FROM_NUMBER",
}

BANNER = r"""
   _____                                                    _____ __  __ _____ 
  |  _  |                                                  /  ___|  \/  /  ___|
  | |_| |_ __   ___  _ __  _   _ _ __ ___   ___  _   _ ___\ `--.| .  . \ `--. 
  |  _  | '_ \ / _ \| '_ \| | | | '_ ` _ \ / _ \| | | / __|`--. \ |\/| |`--. \
  | | | | | | | (_) | | | | |_| | | | | | | (_) | |_| \__ /\__/ / |  | /\__/ /
  \_| |_/_| |_|\___/|_| |_|\__, |_| |_| |_|\___/ \__,_|___\____/\_|  |_\____/ 
                             __/ |                                              
                            |___/       Powered by Twilio Messaging Service
"""


def fail(message: str) -> NoReturn:
    print(f"\n[ERROR] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load supported Twilio settings from a .env file."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"Could not read {path}: {error}")

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or key not in DOTENV_KEYS:
            continue  # skip unknown keys silently
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
    value = reader(f"{prompt}: ").strip()
    if not value:
        fail(f"{name} is required.")
    return value


def read_phone(prompt: str) -> str:
    number = input(f"{prompt} (E.164, e.g. +15551234567): ").strip()
    if not E164_NUMBER.fullmatch(number):
        fail("Use a complete E.164 phone number beginning with '+'.")
    return number


def validate_sender_id(sender_id: str) -> str:
    """Validate alphanumeric sender ID per Twilio rules."""
    if not sender_id:
        fail("Sender ID cannot be empty.")
    if len(sender_id) > MAX_SENDER_ID_LENGTH:
        fail(f"Sender ID must be {MAX_SENDER_ID_LENGTH} characters or fewer.")
    if not re.match(r"^[a-zA-Z0-9 ]+$", sender_id):
        fail("Sender ID can only contain letters, numbers, and spaces.")
    if sender_id.isdigit():
        fail("Sender ID must contain at least one letter.")
    return sender_id


def send_anonymous_sms(
    account_sid: str,
    auth_token: str,
    to_number: str,
    message: str,
    *,
    messaging_service_sid: str | None = None,
    sender_id: str | None = None,
) -> str:
    """Send an SMS via Twilio. Returns the message SID.

    Uses either a Messaging Service SID or an alphanumeric sender ID.
    """
    credentials = f"{account_sid}:{auth_token}".encode("utf-8")
    authorization = base64.b64encode(credentials).decode("ascii")

    payload = {"To": to_number, "Body": message}

    if messaging_service_sid:
        payload["MessagingServiceSid"] = messaging_service_sid
    elif sender_id:
        payload["From"] = sender_id
    else:
        fail("Either a Messaging Service SID or a sender ID is required.")

    body = urlencode(payload).encode("utf-8")
    endpoint = (
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    )
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send an anonymous SMS using Twilio Messaging Service."
    )
    parser.add_argument(
        "--sender-id",
        default=None,
        help="Alphanumeric sender ID (e.g. 'Anonymous'). Max 11 chars.",
    )
    args = parser.parse_args()

    load_dotenv()
    print(BANNER)

    # --- Twilio credentials ---
    account_sid = read_setting("TWILIO_ACCOUNT_SID", "Twilio Account SID")
    auth_token = read_setting(
        "TWILIO_AUTH_TOKEN", "Twilio Auth Token", secret=True
    )

    # --- Sending method ---
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "").strip()
    sender_id = args.sender_id

    if not messaging_service_sid and not sender_id:
        print("\n--- Sender Configuration ---")
        print("[1] Use Messaging Service SID (recommended)")
        print("[2] Use alphanumeric sender ID (e.g. 'Anonymous')")
        choice = input("\nChoice [1/2]: ").strip()

        if choice == "1":
            messaging_service_sid = input("Messaging Service SID: ").strip()
            if not messaging_service_sid:
                fail("Messaging Service SID is required.")
        elif choice == "2":
            sender_id = input(
                "Sender ID (max 11 chars, e.g. 'Anonymous'): "
            ).strip()
            sender_id = validate_sender_id(sender_id)
        else:
            fail("Invalid choice.")

    if sender_id:
        sender_id = validate_sender_id(sender_id)

    # --- Recipient ---
    to_number = read_phone("\nRecipient phone number")

    # --- Message ---
    print()
    message = input("Your anonymous message: ").strip()
    if not message:
        fail("Message cannot be empty.")
    if len(message) > MAX_MESSAGE_LENGTH:
        fail(f"Message must be at most {MAX_MESSAGE_LENGTH} characters.")

    # --- Confirm ---
    sender_display = sender_id if sender_id else f"Messaging Service ({messaging_service_sid[:12]}...)"
    print("\n" + "=" * 50)
    print("  REVIEW YOUR ANONYMOUS MESSAGE")
    print("=" * 50)
    print(f"  From:    {sender_display}")
    print(f"  To:      {to_number}")
    print(f"  Message: {message}")
    print("=" * 50)

    confirmation = input("\nType SEND to send this anonymous message: ").strip()
    if confirmation != "SEND":
        print("Cancelled — no message was sent.")
        return 0

    # --- Send ---
    print("\nSending...")
    message_sid = send_anonymous_sms(
        account_sid,
        auth_token,
        to_number,
        message,
        messaging_service_sid=messaging_service_sid if messaging_service_sid else None,
        sender_id=sender_id,
    )

    print(f"\n[SUCCESS] Anonymous message sent! (SID: {message_sid})")
    print("The recipient will see the sender as:", sender_display)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled — no message was sent.")
        raise SystemExit(130)
