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

## Anonymous SMS

Send an SMS where the recipient sees a custom name (e.g. **"Anonymous"**) instead of your phone number.

### How it works

Uses Twilio's **Messaging Service** with an **alphanumeric sender ID**. The recipient sees a name like "Anonymous" or "Unknown" instead of a phone number — they cannot reply or trace the sender.

> **Note:** Alphanumeric sender IDs are **not supported** in the US/Canada. They work in most other countries (UK, India, Nepal, Australia, etc.).

### Setup

1. Go to [Twilio Console → Messaging Services](https://console.twilio.com/us1/develop/sms/services) and create a new Messaging Service.
2. Set up an **Alphanumeric Sender ID** (e.g. `Anonymous`) in the service.
3. Add the Messaging Service SID to your `.env`:
   ```dotenv
   TWILIO_MESSAGING_SERVICE_SID=MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Usage

```powershell
python .\anonymous_sms.py
```

Or use a sender ID directly via command line:

```powershell
python .\anonymous_sms.py --sender-id "Anonymous"
```

The script will ask for the recipient number and your message, then confirm before sending.
