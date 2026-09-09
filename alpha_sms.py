#!/usr/bin/env python3
"""Alpha SMS — Send anonymous messages worldwide.

Uses your Twilio account with alphanumeric sender ID "Alpha".
Recipient sees "Alpha" as the sender — no phone number, no trace, no reply.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from getpass import getpass
from pathlib import Path
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MAX_MSG_LEN = 1600
SENDER_ID = "Alpha"

DOTENV_KEYS = {"TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"}


class C:
    R = "\033[91m"
    G = "\033[92m"
    Y = "\033[93m"
    B = "\033[94m"
    M = "\033[95m"
    CN = "\033[96m"
    W = "\033[97m"
    BD = "\033[1m"
    DM = "\033[2m"
    X = "\033[0m"


BANNER = f"""{C.CN}
     █████╗ ██╗     ██████╗ ██╗  ██╗ █████╗ 
    ██╔══██╗██║     ██╔══██╗██║  ██║██╔══██╗
    ███████║██║     ██████╔╝███████║███████║
    ██╔══██║██║     ██╔═══╝ ██╔══██║██╔══██║
    ██║  ██║███████╗██║     ██║  ██║██║  ██║
    ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝{C.X}
    {C.W}{C.BD}Anonymous SMS — Worldwide{C.X}
    {C.DM}Sender shows as "Alpha" • No trace • No reply{C.X}
"""


def fail(msg: str) -> NoReturn:
    print(f"\n  {C.R}[✗] {msg}{C.X}", file=sys.stderr)
    raise SystemExit(1)


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.partition("=")
        key = key.strip()
        if not sep or key not in DOTENV_KEYS:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if val:
            os.environ.setdefault(key, val)


def get_cred(name: str, prompt: str, secret: bool = False) -> str:
    val = os.getenv(name, "").strip()
    if val:
        return val
    reader = getpass if secret else input
    val = reader(f"  {prompt}: ").strip()
    if not val:
        fail(f"{name} is required.")
    return val


def read_number() -> str:
    print(f"\n  {C.BD}Enter recipient number (with country code):{C.X}")
    print(f"  {C.DM}Examples: +977984XXXXXXX, +1555XXXXXXX, +44XXXXXXXXXX{C.X}")
    num = input(f"\n  📱 To: ").strip().replace(" ", "").replace("-", "")
    if not num.startswith("+"):
        num = "+" + num
    # Basic E.164 check
    if len(num) < 8 or len(num) > 16 or not num[1:].isdigit():
        fail("Invalid number. Use E.164 format with country code (e.g. +977984XXXXXXX)")
    return num


def send_sms(sid: str, token: str, to: str, msg: str) -> str:
    """Send SMS via Twilio with 'Alpha' as sender."""
    creds = base64.b64encode(f"{sid}:{token}".encode()).decode("ascii")
    body = urlencode({"To": to, "From": SENDER_ID, "Body": msg}).encode()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    req = Request(url, data=body, headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }, method="POST")

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("message", "")
        except Exception:
            detail = ""
        fail(f"Twilio error (HTTP {e.code})" + (f": {detail}" if detail else ""))
    except URLError as e:
        fail(f"Cannot reach Twilio: {e.reason}")

    msg_sid = data.get("sid")
    if not msg_sid:
        fail("Unexpected Twilio response.")
    return msg_sid


def spinner(text: str, secs: float = 2.0) -> None:
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    end = time.time() + secs
    i = 0
    while time.time() < end:
        print(f"\r  {C.CN}{frames[i % len(frames)]} {text}{C.X}", end="", flush=True)
        time.sleep(0.08)
        i += 1
    print(f"\r{' ' * (len(text) + 8)}\r", end="")


def main() -> int:
    if sys.platform == "win32":
        os.system("")  # enable ANSI on Windows

    print(BANNER)
    load_dotenv()

    # --- Credentials ---
    print(f"  {C.BD}── Twilio Credentials ──{C.X}")
    sid = get_cred("TWILIO_ACCOUNT_SID", "Account SID")
    token = get_cred("TWILIO_AUTH_TOKEN", "Auth Token", secret=True)
    print(f"  {C.G}[✓] Credentials loaded{C.X}")

    # --- Loop: send multiple messages ---
    while True:
        to = read_number()
        print(f"\n  {C.BD}Type your anonymous message:{C.X}")
        msg = input(f"  ✍️  Message: ").strip()
        if not msg:
            fail("Message cannot be empty.")
        if len(msg) > MAX_MSG_LEN:
            fail(f"Message too long (max {MAX_MSG_LEN} chars).")

        # --- Preview ---
        print(f"\n  {C.BD}{'═' * 44}{C.X}")
        print(f"  {C.BD}  📨 ANONYMOUS MESSAGE PREVIEW{C.X}")
        print(f"  {C.BD}{'═' * 44}{C.X}")
        print(f"  {C.Y}  From:    Alpha{C.X}")
        print(f"  {C.CN}  To:      {to}{C.X}")
        print(f"  {C.W}  Message: {msg}{C.X}")
        print(f"  {C.BD}{'═' * 44}{C.X}")

        confirm = input(f"\n  {C.BD}Type SEND to fire 🚀: {C.X}").strip()
        if confirm != "SEND":
            print(f"  {C.Y}[!] Cancelled.{C.X}")
        else:
            spinner("Sending as Alpha...")
            msg_sid = send_sms(sid, token, to, msg)
            print(f"  {C.G}[✓] Message sent! 🎉{C.X}")
            print(f"  {C.DM}SID: {msg_sid}{C.X}")
            print(f"  {C.DM}Recipient sees sender as: \"Alpha\"{C.X}")
            print(f"  {C.DM}They CANNOT reply or trace you.{C.X}")

        # --- Again? ---
        print()
        again = input(f"  {C.BD}Send another? (y/n): {C.X}").strip().lower()
        if again != "y":
            print(f"\n  {C.CN}Bye! 👋{C.X}\n")
            break

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(f"\n  {C.Y}Cancelled.{C.X}")
        raise SystemExit(130)
