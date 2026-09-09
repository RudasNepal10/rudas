# Manual SMS sender

This project sends one manually composed SMS through your own Twilio account.
It does not request, receive, generate, or use OTPs, and it has no bulk-send,
call, email, or third-party delivery-provider features.

Only send to recipients who have agreed to receive your messages. Your Twilio
account and sender number must be configured and approved by Twilio.

## Setup

Install Python 3.8 or newer. No third-party Python packages are required.

Set the Twilio credentials in your shell, replacing the example values with
your own:

```powershell
$env:TWILIO_ACCOUNT_SID = "AC..."
$env:TWILIO_AUTH_TOKEN = "your_auth_token"
$env:TWILIO_FROM_NUMBER = "+15551234567"
python .\bomber.py
```

On macOS or Linux:

```sh
export TWILIO_ACCOUNT_SID='AC...'
export TWILIO_AUTH_TOKEN='your_auth_token'
export TWILIO_FROM_NUMBER='+15551234567'
python3 bomber.py
```

### Using a `.env` file on Kali/Linux

Copy the included example, then enter your own values locally:

```sh
cp .env.example .env
nano .env
chmod 600 .env
python3 bomber.py
```

The `.env` file must contain only these settings:

```dotenv
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+15551234567
```

`.env` is excluded from Git; never share or commit it. Environment variables
set in the terminal take precedence over `.env` values.

The script asks for a recipient number and presents a default message. Press
Enter to use it or type a replacement, then review the result. It sends only
when you type `SEND`. Phone numbers must use E.164 format, such as
`+15551234567`.

You may leave the environment variables unset and enter the credentials
locally when prompted. Do not commit credentials to this repository.

---

## Alpha SMS — Anonymous Worldwide

Send an anonymous SMS to **any country**. The recipient sees **"Alpha"** as the sender — no phone number, no trace, no reply possible.

### Setup

Add your Twilio credentials to `.env`:

```dotenv
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your_auth_token
```

### Usage

```powershell
python .\alpha_sms.py
```

The script will:
1. Ask for the recipient's number (any country, e.g. `+977984XXXXXXX`)
2. Ask for your message
3. Show a preview and confirm
4. Send as **"Alpha"** — recipient can't reply or trace you
5. Ask if you want to send another

> **Note:** Alphanumeric sender IDs (like "Alpha") are not supported in US/Canada. Works in most other countries worldwide.

