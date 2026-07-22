"""Schemas — correo Microsoft 365 (Outlook operativo)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class M365MailAttachment(BaseModel):
    id: str | None = None
    name: str = ""
    size_bytes: int | None = None
    content_type: str | None = None
    is_inline: bool = False


class M365MailAttachmentRef(BaseModel):
    """Adjunto para envío — archivo local (base64) o referencia OneDrive."""

    name: str
    content_type: str = "application/octet-stream"
    content_base64: str | None = None
    source_url: str | None = None
    onedrive_item_id: str | None = None


class M365MailMessage(BaseModel):
    id: str
    subject: str = ""
    sender: str = ""
    sender_name: str | None = None
    to_recipients: list[str] = Field(default_factory=list)
    cc_recipients: list[str] = Field(default_factory=list)
    received_at: datetime | None = None
    sent_at: datetime | None = None
    preview: str = ""
    body_html: str | None = None
    body_text: str | None = None
    is_read: bool = False
    has_attachments: bool = False
    attachments: list[M365MailAttachment] = Field(default_factory=list)
    web_link: str | None = None
    folder: str = "inbox"
    account_id: uuid.UUID | None = None
    account_email: str | None = None


class M365MailListResponse(BaseModel):
    items: list[M365MailMessage]
    total: int
    folder: str
    account_id: uuid.UUID | None = None
    account_email: str | None = None
    connected: bool = False
    read_only: bool = False
    message: str = ""
    error: str | None = None
    permission_hint: str | None = None


class M365MailDetailResponse(M365MailMessage):
    connected: bool = True
    read_only: bool = False
    can_reply: bool = True
    can_forward: bool = True
    can_send: bool = True


class M365MailComposeRequest(BaseModel):
    body: str
    subject: str | None = None
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    comment: str | None = None
    attachments: list[M365MailAttachmentRef] = Field(default_factory=list)
    reply_all: bool = False
    save_draft: bool = False


class M365MailActionResponse(BaseModel):
    ok: bool
    message: str
    message_id: str | None = None


class M365MailPatchRequest(BaseModel):
    is_read: bool | None = None
    move_to_folder: str | None = None


class M365MailAccountsResponse(BaseModel):
    items: list
    total: int
    azure_configured: bool = False
    oauth_ready: bool = False
