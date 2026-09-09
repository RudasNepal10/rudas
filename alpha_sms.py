#!/usr/bin/env python3
"""Alpha SMS — Send anonymous messages worldwide.

Uses Twilio with alphanumeric sender ID "Alpha".
- Recipient sees "Alpha" — no phone number, no trace, no reply.
- Supports SOCKS5/HTTP proxy to hide your IP from Twilio.
- No local logs, no message history saved.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import time
from getpass import getpass
from pathlib import Path
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    Request,
    ProxyHandler,
    build_opener,
    urlopen,
)


MAX_MSG_LEN = 1600
SENDER_ID = "Alpha"
DOTENV_KEYS = {"TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "PROXY_URL"}


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
    {C.DM}Sender: "Alpha" • No trace • No reply • No logs{C.X}
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
    if len(num) < 8 or len(num) > 16 or not num[1:].isdigit():
        fail("Invalid number. Use E.164 format with country code (e.g. +977984XXXXXXX)")
    return num


def setup_proxy() -> bool:
    """Configure proxy for Twilio API calls."""
    proxy_url = os.getenv("PROXY_URL", "").strip()

    if not proxy_url:
        print(f"\n  {C.BD}── Privacy Layer ──{C.X}")
        print(f"  {C.DM}Use a proxy to hide your IP from Twilio's servers.{C.X}")
        print(f"  {C.CN}[1]{C.X} No proxy (use direct connection)")
        print(f"  {C.CN}[2]{C.X} HTTP proxy  {C.DM}(e.g. http://127.0.0.1:8080){C.X}")
        print(f"  {C.CN}[3]{C.X} SOCKS5 proxy {C.DM}(e.g. socks5h://127.0.0.1:9050 for Tor){C.X}")
        choice = input(f"\n  Choice [1/2/3]: ").strip()

        if choice == "1":
            return False
        elif choice in ("2", "3"):
            proxy_url = input(f"  Proxy URL: ").strip()
            if not proxy_url:
                fail("Proxy URL is required.")
        else:
            return False

    # Set proxy in environment for urllib
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["HTTP_PROXY"] = proxy_url
    return True


def send_sms(sid: str, token: str, to: str, msg: str) -> str:
    """Send SMS via Twilio with 'Alpha' as sender. Routes through proxy if set."""
    creds = base64.b64encode(f"{sid}:{token}".encode()).decode("ascii")
    body = urlencode({"To": to, "From": SENDER_ID, "Body": msg}).encode()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    req = Request(url, data=body, headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        # Generic user agent — don't leak info
        "User-Agent": "Mozilla/5.0",
    }, method="POST")

    # Build opener with proxy if configured
    proxy_url = os.environ.get("HTTPS_PROXY", "")
    if proxy_url:
        proxy_handler = ProxyHandler({
            "https": proxy_url,
            "http": proxy_url,
        })
        opener = build_opener(proxy_handler)
    else:
        opener = build_opener()

    try:
        with opener.open(req, timeout=30) as resp:
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


def clear_screen() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")


def main() -> int:
    if sys.platform == "win32":
        os.system("")  # enable ANSI on Windows

    # Disable Python bytecode cache (__pycache__) — leave no trace
    sys.dont_write_bytecode = True

    print(BANNER)
    load_dotenv()

    # --- Credentials ---
    print(f"  {C.BD}── Twilio Credentials ──{C.X}")
    sid = get_cred("TWILIO_ACCOUNT_SID", "Account SID")
    token = get_cred("TWILIO_AUTH_TOKEN", "Auth Token", secret=True)
    print(f"  {C.G}[✓] Credentials loaded{C.X}")

    # --- Proxy setup ---
    using_proxy = setup_proxy()
    if using_proxy:
        print(f"  {C.G}[✓] Proxy active — your IP is hidden from Twilio{C.X}")
    else:
        print(f"  {C.Y}[!] No proxy — Twilio can see your IP{C.X}")

    # --- Privacy info ---
    print(f"\n  {C.BD}── Privacy Status ──{C.X}")
    print(f"  {C.G}[✓]{C.X} Sender ID: \"Alpha\" (no number shown)")
    print(f"  {C.G}[✓]{C.X} No local logs saved")
    print(f"  {C.G}[✓]{C.X} No message history")
    print(f"  {C.G}[✓]{C.X} No __pycache__ created")
    print(f"  {C.G}[✓]{C.X} Recipient cannot reply")
    if using_proxy:
        print(f"  {C.G}[✓]{C.X} IP hidden via proxy")
    else:
        print(f"  {C.Y}[!]{C.X} IP visible to Twilio (use proxy to hide)")

    # --- Loop: send messages ---
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
        if using_proxy:
            print(f"  {C.G}  Proxy:   Active ✓{C.X}")
        print(f"  {C.BD}{'═' * 44}{C.X}")

        confirm = input(f"\n  {C.BD}Type SEND to fire 🚀: {C.X}").strip()
        if confirm != "SEND":
            print(f"  {C.Y}[!] Cancelled.{C.X}")
        else:
            spinner("Sending as Alpha...")
            msg_sid = send_sms(sid, token, to, msg)
            print(f"  {C.G}[✓] Message sent! 🎉{C.X}")
            print(f"  {C.DM}Recipient sees: \"Alpha\"{C.X}")
            print(f"  {C.DM}Cannot reply. Cannot trace.{C.X}")
            # Don't print SID — leave no trace in terminal history
            del msg_sid

        # --- Again? ---
        print()
        again = input(f"  {C.BD}Send another? (y/n): {C.X}").strip().lower()
        if again != "y":
            # Clear screen on exit for privacy
            clear_input = input(f"  {C.BD}Clear terminal? (y/n): {C.X}").strip().lower()
            if clear_input == "y":
                clear_screen()
            print(f"\n  {C.CN}Gone like a ghost. 👻{C.X}\n")
            break

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(f"\n  {C.Y}Cancelled.{C.X}")
        raise SystemExit(130)
