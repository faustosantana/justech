import fs from "fs";
import path from "path";
import makeWASocket, {
  DisconnectReason,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  getContentType,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import pino from "pino";
import QRCode from "qrcode";

const logger = pino({ level: process.env.LOG_LEVEL || "info" });

function jidToPhone(jid) {
  if (!jid) return null;
  return jid.split("@")[0].split(":")[0];
}

export class SessionManager {
  constructor({ sessionsPath, webhookUrl, bridgeSecret }) {
    this.sessionsPath = sessionsPath;
    this.webhookUrl = webhookUrl;
    this.bridgeSecret = bridgeSecret;
    /** @type {Map<string, { sock: import('@whiskeysockets/baileys').WASocket | null, status: string, phone: string | null, qr: string | null, qrImage: string | null, pushName: string | null, lastError: string | null }>} */
    this.sessions = new Map();
    fs.mkdirSync(sessionsPath, { recursive: true });
  }

  async _postWebhook(sessionId, event, payload) {
    if (!this.webhookUrl) return;
    try {
      const { default: axios } = await import("axios");
      await axios.post(
        this.webhookUrl,
        { session_id: sessionId, event, payload },
        {
          headers: { "X-Bridge-Secret": this.bridgeSecret },
          timeout: 15000,
        },
      );
    } catch (err) {
      logger.warn({ err: err.message, sessionId, event }, "webhook failed");
    }
  }

  _ensureMeta(sessionId) {
    if (!this.sessions.has(sessionId)) {
      this.sessions.set(sessionId, {
        sock: null,
        status: "disconnected",
        phone: null,
        qr: null,
        qrImage: null,
        pushName: null,
        lastError: null,
      });
    }
    return this.sessions.get(sessionId);
  }

  async createSession(sessionId) {
    const meta = this._ensureMeta(sessionId);
    if (meta.sock) {
      return this.getStatus(sessionId);
    }

    const authDir = path.join(this.sessionsPath, sessionId);
    fs.mkdirSync(authDir, { recursive: true });

    const { state, saveCreds } = await useMultiFileAuthState(authDir);
    const { version } = await fetchLatestBaileysVersion();

    const sock = makeWASocket({
      version,
      auth: state,
      logger: pino({ level: "silent" }),
      printQRInTerminal: false,
      syncFullHistory: false,
      markOnlineOnConnect: false,
      generateHighQualityLinkPreview: false,
    });

    meta.sock = sock;
    meta.status = "connecting";

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        meta.qr = qr;
        meta.qrImage = await QRCode.toDataURL(qr, { margin: 1, width: 280 });
        meta.status = "qr_pending";
        await this._postWebhook(sessionId, "qr", { qr_image: meta.qrImage });
      }

      if (connection === "open") {
        meta.status = "connected";
        meta.qr = null;
        meta.qrImage = null;
        meta.phone = jidToPhone(sock.user?.id);
        meta.pushName = sock.user?.name || null;
        meta.lastError = null;
        await this._postWebhook(sessionId, "connected", {
          phone: meta.phone,
          push_name: meta.pushName,
        });
      }

      if (connection === "close") {
        const code = lastDisconnect?.error?.output?.statusCode;
        const shouldReconnect = code !== DisconnectReason.loggedOut;
        meta.status = shouldReconnect ? "reconnecting" : "disconnected";
        meta.lastError = lastDisconnect?.error?.message || "connection closed";
        meta.sock = null;

        await this._postWebhook(sessionId, "disconnected", {
          code,
          should_reconnect: shouldReconnect,
          error: meta.lastError,
        });

        if (shouldReconnect) {
          setTimeout(() => this.createSession(sessionId).catch(() => {}), 3000);
        }
      }
    });

    sock.ev.on("messages.upsert", async ({ messages, type }) => {
      if (type !== "notify") return;
      for (const msg of messages) {
        if (!msg.message) continue;
        const contentType = getContentType(msg.message);
        let body = "";
        let mediaType = null;
        let mediaMime = null;

        if (contentType === "conversation") {
          body = msg.message.conversation || "";
        } else if (contentType === "extendedTextMessage") {
          body = msg.message.extendedTextMessage?.text || "";
        } else if (contentType === "imageMessage") {
          mediaType = "image";
          mediaMime = msg.message.imageMessage?.mimetype || "image/jpeg";
          body = msg.message.imageMessage?.caption || "";
        } else if (contentType === "documentMessage") {
          mediaType = "document";
          mediaMime = msg.message.documentMessage?.mimetype || "application/octet-stream";
          body = msg.message.documentMessage?.caption || msg.message.documentMessage?.fileName || "";
        } else if (contentType === "audioMessage") {
          mediaType = "audio";
          mediaMime = msg.message.audioMessage?.mimetype || "audio/ogg";
        } else if (contentType === "videoMessage") {
          mediaType = "video";
          mediaMime = msg.message.videoMessage?.mimetype || "video/mp4";
          body = msg.message.videoMessage?.caption || "";
        } else if (contentType === "stickerMessage") {
          mediaType = "sticker";
        }

        const fromMe = !!msg.key.fromMe;
        const remoteJid = msg.key.remoteJid || "";
        const participant = msg.key.participant || null;

        await this._postWebhook(sessionId, "message", {
          wa_message_id: msg.key.id,
          remote_jid: remoteJid,
          participant,
          from_me: fromMe,
          timestamp: Number(msg.messageTimestamp || Date.now()) * 1000,
          body,
          media_type: mediaType,
          media_mime: mediaMime,
          content_type: contentType,
        });
      }
    });

    sock.ev.on("chats.upsert", async (chats) => {
      for (const chat of chats) {
        await this._postWebhook(sessionId, "chat", {
          remote_jid: chat.id,
          name: chat.name || null,
          unread_count: chat.unreadCount || 0,
          conversation_timestamp: chat.conversationTimestamp
            ? Number(chat.conversationTimestamp) * 1000
            : null,
        });
      }
    });

    return this.getStatus(sessionId);
  }

  getStatus(sessionId) {
    const meta = this._ensureMeta(sessionId);
    return {
      session_id: sessionId,
      status: meta.status,
      phone: meta.phone,
      push_name: meta.pushName,
      qr_image: meta.qrImage,
      last_error: meta.lastError,
    };
  }

  async disconnect(sessionId, logout = true) {
    const meta = this.sessions.get(sessionId);
    if (meta?.sock) {
      try {
        if (logout) await meta.sock.logout();
        else meta.sock.end(undefined);
      } catch {
        /* ignore */
      }
    }
    this.sessions.delete(sessionId);
    const authDir = path.join(this.sessionsPath, sessionId);
    if (logout && fs.existsSync(authDir)) {
      fs.rmSync(authDir, { recursive: true, force: true });
    }
    return { session_id: sessionId, status: "disconnected" };
  }

  _requireSock(sessionId) {
    const meta = this.sessions.get(sessionId);
    if (!meta?.sock || meta.status !== "connected") {
      throw new Error("SESSION_NOT_CONNECTED");
    }
    return meta.sock;
  }

  async listChats(sessionId) {
    const sock = this._requireSock(sessionId);
    const chats = await sock.store?.chats?.all?.();
    if (!chats?.length) {
      return [];
    }
    return chats
      .filter((c) => c.id && !c.id.includes("@broadcast"))
      .map((c) => ({
        remote_jid: c.id,
        name: c.name || jidToPhone(c.id),
        unread_count: c.unreadCount || 0,
        conversation_timestamp: c.conversationTimestamp
          ? Number(c.conversationTimestamp) * 1000
          : null,
        is_group: c.id.endsWith("@g.us"),
      }))
      .sort((a, b) => (b.conversation_timestamp || 0) - (a.conversation_timestamp || 0));
  }

  async listMessages(sessionId, remoteJid, limit = 50) {
    const sock = this._requireSock(sessionId);
    const msgs = await sock.store?.messages?.[remoteJid]?.array?.();
    if (!msgs?.length) return [];

    return msgs
      .slice(-limit)
      .reverse()
      .map((msg) => {
        const contentType = msg.message ? getContentType(msg.message) : null;
        let body = "";
        if (contentType === "conversation") body = msg.message.conversation || "";
        else if (contentType === "extendedTextMessage")
          body = msg.message.extendedTextMessage?.text || "";

        return {
          wa_message_id: msg.key.id,
          remote_jid: msg.key.remoteJid,
          from_me: !!msg.key.fromMe,
          timestamp: Number(msg.messageTimestamp || 0) * 1000,
          body,
          content_type: contentType,
        };
      });
  }

  async sendText(sessionId, remoteJid, text, quotedId = null) {
    const sock = this._requireSock(sessionId);
    const content = { text };
    const options = {};
    if (quotedId) {
      const msgs = await sock.store?.messages?.[remoteJid]?.array?.();
      const quoted = msgs?.find((m) => m.key.id === quotedId);
      if (quoted) options.quoted = quoted;
    }
    const result = await sock.sendMessage(remoteJid, content, options);
    return {
      wa_message_id: result?.key?.id,
      remote_jid: remoteJid,
      timestamp: Date.now(),
    };
  }

  async sendDocument(sessionId, remoteJid, { filename, mimetype, content_base64, caption }) {
    const sock = this._requireSock(sessionId);
    const buffer = Buffer.from(content_base64, "base64");
    const content = {
      document: buffer,
      mimetype: mimetype || "application/octet-stream",
      fileName: filename || "documento",
      caption: caption?.trim() || undefined,
    };
    const result = await sock.sendMessage(remoteJid, content);
    return {
      wa_message_id: result?.key?.id,
      remote_jid: remoteJid,
      timestamp: Date.now(),
      filename,
    };
  }
}
