#!/usr/bin/env python3
"""Send one manually composed SMS using a Twilio account.

This program deliberately sends exactly one message per run. It has no bulk
send, verification-code, call, email, or third-party-provider functionality.
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
DOTENV_KEYS = {"TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"}
DEFAULT_MESSAGE = (
    "Hi Amrit, it’s Alpha. I hope you’re well. I’d like to talk if you’re "
    "comfortable—please message me on WhatsApp. If you’d rather not, I’ll "
    "respect that."
)


def fail(message: str) -> NoReturn:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load the three supported Twilio settings from a local .env file.

    Existing environment variables take priority. This intentionally supports
    only simple KEY=value lines so values are never evaluated as shell code.
    """
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
            fail(f"Invalid .env entry on line {line_number}.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not value:
            fail(f"The value for {key} in .env cannot be empty.")
        os.environ.setdefault(key, value)


def read_required_setting(name: str, prompt: str, *, secret: bool = False) -> str:
    """Read a Twilio setting from the environment, or ask the local user."""
    value = os.getenv(name, "").strip()
    if value:
        return value
    reader = getpass if secret else input
    value = reader(f"{prompt}: ").strip()
    if not value:
        fail(f"{name} is required.")
    return value


def read_phone(prompt: str) -> str:
    number = input(f"{prompt} (E.164, for example +15551234567): ").strip()
    if not E164_NUMBER.fullmatch(number):
        fail("Use a complete E.164 phone number beginning with '+'.")
    return number


def read_message() -> str:
    print("\nDefault message:")
    print(DEFAULT_MESSAGE)
    message = input("\nMessage (press Enter to use the default): ").strip()
    if not message:
        message = DEFAULT_MESSAGE
    if not message:
        fail("The message cannot be empty.")
    if len(message) > MAX_MESSAGE_LENGTH:
        fail(f"The message must contain at most {MAX_MESSAGE_LENGTH} characters.")
    return message


def send_twilio_sms(account_sid: str, auth_token: str, from_number: str,
                    to_number: str, message: str) -> str:
    """Submit one message to Twilio's Messages API and return its message SID."""
    credentials = f"{account_sid}:{auth_token}".encode("utf-8")
    authorization = base64.b64encode(credentials).decode("ascii")
    body = urlencode({"To": to_number, "From": from_number, "Body": message}).encode("utf-8")
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
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        # Twilio's response may contain a useful error message; never print credentials.
        try:
            details = json.loads(error.read().decode("utf-8")).get("message", "")
        except (UnicodeDecodeError, json.JSONDecodeError):
            details = ""
        fail(f"Twilio rejected the message (HTTP {error.code})" +
             (f": {details}" if details else "."))
    except URLError as error:
        fail(f"Could not reach Twilio: {error.reason}")

    message_sid = payload.get("sid")
    if not message_sid:
        fail("Twilio returned an unexpected response.")
    return message_sid


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compose and send one consent-based SMS through Twilio.")
    parser.parse_args()
    load_dotenv()

    print("Manual SMS sender — one message only")
    print("Only send messages to people who have agreed to receive them. "
          "No OTPs are requested or handled.\n")

    account_sid = read_required_setting("TWILIO_ACCOUNT_SID", "Twilio Account SID")
    auth_token = read_required_setting("TWILIO_AUTH_TOKEN", "Twilio Auth Token", secret=True)
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip() or read_phone(
        "Your approved Twilio sender number")
    if not E164_NUMBER.fullmatch(from_number):
        fail("TWILIO_FROM_NUMBER must be an E.164 phone number beginning with '+'.")

    to_number = read_phone("Recipient number")
    message = read_message()

    print("\nReview")
    print(f"  From:    {from_number}")
    print(f"  To:      {to_number}")
    print(f"  Message: {message}")
    confirmation = input("\nType SEND to submit this one message: ").strip()
    if confirmation != "SEND":
        print("Cancelled; no message was sent.")
        return 0

    message_sid = send_twilio_sms(account_sid, auth_token, from_number, to_number, message)
    print(f"Message accepted by Twilio (SID: {message_sid}).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled; no message was sent.")
        raise SystemExit(130)
