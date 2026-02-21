"""
Communications MCP server — Gmail (SMTP/IMAP) and WhatsApp (Meta Business API).
"""

from __future__ import annotations

import email
import imaplib
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP(name="Communications Server")


# ── Gmail helpers ──────────────────────────────────────────────────


def _gmail_address() -> str:
    addr = os.environ.get("GMAIL_ADDRESS", "")
    if not addr:
        raise ValueError("GMAIL_ADDRESS environment variable is required")
    return addr


def _gmail_app_password() -> str:
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pwd:
        raise ValueError("GMAIL_APP_PASSWORD environment variable is required")
    return pwd


def _imap_connect() -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    conn.login(_gmail_address(), _gmail_app_password())
    return conn


# ── Email Tools ────────────────────────────────────────────────────


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
) -> dict[str, Any]:
    """Send an email via Gmail SMTP.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text).
        cc: Optional CC addresses, comma-separated.
        bcc: Optional BCC addresses, comma-separated.
    """
    sender = _gmail_address()

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain"))

    recipients = [to]
    if cc:
        recipients.extend(a.strip() for a in cc.split(",") if a.strip())
    if bcc:
        recipients.extend(a.strip() for a in bcc.split(",") if a.strip())

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, _gmail_app_password())
        server.sendmail(sender, recipients, msg.as_string())

    return {"status": "sent", "to": to, "subject": subject}


@mcp.tool()
def read_emails(
    folder: str = "INBOX",
    limit: int = 10,
    unread_only: bool = False,
) -> dict[str, Any]:
    """List recent emails from a Gmail folder via IMAP.

    Args:
        folder: Mail folder to read (default "INBOX").
        limit: Maximum number of emails to return (default 10).
        unread_only: If True, only return unread messages.
    """
    conn = _imap_connect()
    try:
        conn.select(folder, readonly=True)
        criteria = "UNSEEN" if unread_only else "ALL"
        _, msg_nums = conn.search(None, criteria)
        ids = msg_nums[0].split()
        ids = ids[-limit:]  # most recent

        emails = []
        for mid in reversed(ids):
            _, data = conn.fetch(mid, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")

            emails.append({
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body_preview": body[:500],
            })

        return {"folder": folder, "count": len(emails), "emails": emails}
    finally:
        conn.close()
        conn.logout()


@mcp.tool()
def search_emails(
    query: str,
    folder: str = "INBOX",
    limit: int = 10,
) -> dict[str, Any]:
    """Search emails by IMAP query string.

    Args:
        query: IMAP search query (e.g. 'FROM "alice@example.com"',
               'SUBJECT "invoice"', 'SINCE "01-Jan-2025"').
        folder: Mail folder to search (default "INBOX").
        limit: Maximum number of results (default 10).
    """
    conn = _imap_connect()
    try:
        conn.select(folder, readonly=True)
        _, msg_nums = conn.search(None, query)
        ids = msg_nums[0].split()
        ids = ids[-limit:]

        emails = []
        for mid in reversed(ids):
            _, data = conn.fetch(mid, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")

            emails.append({
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body_preview": body[:500],
            })

        return {"query": query, "folder": folder, "count": len(emails), "emails": emails}
    finally:
        conn.close()
        conn.logout()


# ── WhatsApp helpers ───────────────────────────────────────────────


def _whatsapp_token() -> str:
    token = os.environ.get("WHATSAPP_TOKEN", "")
    if not token:
        raise ValueError("WHATSAPP_TOKEN environment variable is required")
    return token


def _whatsapp_phone_id() -> str:
    pid = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    if not pid:
        raise ValueError("WHATSAPP_PHONE_NUMBER_ID environment variable is required")
    return pid


WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


async def _whatsapp_post(payload: dict[str, Any]) -> dict[str, Any]:
    phone_id = _whatsapp_phone_id()
    url = f"{WHATSAPP_API_BASE}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {_whatsapp_token()}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


# ── WhatsApp Tools ─────────────────────────────────────────────────


@mcp.tool()
async def send_whatsapp(to: str, message: str) -> dict[str, Any]:
    """Send a text message via WhatsApp Business Cloud API.

    Args:
        to: Recipient phone number in international format (e.g. "+14155551234").
        message: The text message to send.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    data = await _whatsapp_post(payload)
    return {
        "status": "sent",
        "to": to,
        "message_id": data.get("messages", [{}])[0].get("id", ""),
    }


@mcp.tool()
async def send_whatsapp_template(
    to: str,
    template_name: str,
    language: str = "en_US",
    components: str | None = None,
) -> dict[str, Any]:
    """Send a template message via WhatsApp Business Cloud API.

    Template messages are required for initiating conversations with users
    who haven't messaged you in the last 24 hours.

    Args:
        to: Recipient phone number in international format.
        template_name: Name of the approved message template.
        language: Template language code (default "en_US").
        components: Optional JSON string of template components for variable
                    substitution (e.g. '[{"type":"body","parameters":[{"type":"text","text":"John"}]}]').
    """
    import json as _json

    template: dict[str, Any] = {
        "name": template_name,
        "language": {"code": language},
    }
    if components:
        template["components"] = _json.loads(components)

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": template,
    }
    data = await _whatsapp_post(payload)
    return {
        "status": "sent",
        "to": to,
        "template": template_name,
        "message_id": data.get("messages", [{}])[0].get("id", ""),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        mcp.http_app(stateless_http=True),
        host="0.0.0.0",
        port=9001,
    )
