"""Cliente IMAP — correo estilo Outlook/Thunderbird (usuario + contraseña)."""

from __future__ import annotations

import email
import imaplib
from datetime import datetime, timezone
from email.header import decode_header
from typing import Any


def _decode_mime(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, enc in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    return "".join(parts)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        texts: list[str] = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(
                part.get("Content-Disposition", "")
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    texts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
        return "\n".join(texts)[:8000]
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")[:8000]
    return str(payload or "")[:8000]


def _attachment_names(msg: email.message.Message) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for part in msg.walk():
        filename = part.get_filename()
        if not filename:
            continue
        items.append(
            {
                "name": _decode_mime(filename),
                "content_type": part.get_content_type(),
                "size_bytes": len(part.get_payload(decode=True) or b""),
                "extracted_text": _decode_mime(filename),
            }
        )
    return items[:10]


class M365ImapService:
    def __init__(
        self,
        *,
        host: str = "outlook.office365.com",
        port: int = 993,
        use_ssl: bool = True,
    ):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl

    def test_connection(self, *, email_address: str, password: str) -> dict[str, str]:
        conn = self._login(email_address, password)
        try:
            conn.select("INBOX")
            return {"status": "ok", "message": "Conexión IMAP exitosa"}
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def fetch_recent(
        self,
        *,
        email_address: str,
        password: str,
        mailbox: str = "INBOX",
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        conn = self._login(email_address, password)
        messages: list[dict[str, Any]] = []
        try:
            conn.select(mailbox)
            _, data = conn.search(None, "ALL")
            ids = data[0].split()
            for num in ids[-limit:]:
                _, msg_data = conn.fetch(num, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode_mime(msg.get("Subject"))
                sender = _decode_mime(msg.get("From"))
                sender_email = sender
                if "<" in sender and ">" in sender:
                    sender_email = sender.split("<")[-1].split(">")[0].strip()
                sender_name = sender.split("<")[0].strip().strip('"') if "<" in sender else sender
                date_hdr = msg.get("Date")
                received = datetime.now(timezone.utc)
                if date_hdr:
                    try:
                        received = email.utils.parsedate_to_datetime(date_hdr)
                        if received.tzinfo is None:
                            received = received.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass
                body = _extract_body(msg)
                message_id = (msg.get("Message-ID") or "").strip() or f"imap-{num.decode()}-{hash(raw) & 0xFFFFFFFF:x}"
                messages.append(
                    {
                        "external_message_id": message_id,
                        "mailbox": email_address,
                        "subject": subject or "(sin asunto)",
                        "sender_email": sender_email,
                        "sender_name": sender_name or None,
                        "received_at": received,
                        "body_text": body,
                        "body_preview": body[:500],
                        "attachments": _attachment_names(msg),
                    }
                )
        finally:
            try:
                conn.logout()
            except Exception:
                pass
        messages.reverse()
        return messages

    def _login(self, email_address: str, password: str) -> imaplib.IMAP4:
        if self.use_ssl:
            conn = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            conn = imaplib.IMAP4(self.host, self.port)
        conn.login(email_address, password)
        return conn


def map_imap_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "authentication failed" in text or "login failed" in text or "authenticate failed" in text:
        return (
            "Usuario o contraseña incorrectos. Si tienes MFA en Microsoft 365, "
            "crea una contraseña de aplicación en account.microsoft.com e úsala aquí."
        )
    if "basicauthblocked" in text or "auth plain disabled" in text:
        return (
            "Microsoft bloqueó autenticación básica en este tenant. "
            "Activa IMAP en el buzón y usa contraseña de aplicación, o contacta a IT."
        )
    return f"No se pudo conectar al correo: {exc}"
