import express from "express";
import { SessionManager } from "./session-manager.js";

const PORT = Number(process.env.PORT || 3100);
const BRIDGE_SECRET = process.env.BRIDGE_SECRET || "dev-bridge-secret";
const SESSIONS_PATH = process.env.SESSIONS_PATH || "/data/sessions";
const JAIOS_WEBHOOK_URL = process.env.JAIOS_WEBHOOK_URL || "";

const manager = new SessionManager({
  sessionsPath: SESSIONS_PATH,
  webhookUrl: JAIOS_WEBHOOK_URL,
  bridgeSecret: BRIDGE_SECRET,
});

const app = express();
app.use(express.json({ limit: "10mb" }));

function auth(req, res, next) {
  const secret = req.headers["x-bridge-secret"];
  if (secret !== BRIDGE_SECRET) {
    return res.status(401).json({ error: "unauthorized" });
  }
  next();
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "jaios-whatsapp-bridge" });
});

app.use("/v1", auth);

app.post("/v1/sessions", async (req, res) => {
  const sessionId = req.body?.session_id;
  if (!sessionId) return res.status(400).json({ error: "session_id required" });
  try {
    const status = await manager.createSession(sessionId);
    res.json(status);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/v1/sessions/:sessionId/status", (req, res) => {
  res.json(manager.getStatus(req.params.sessionId));
});

app.delete("/v1/sessions/:sessionId", async (req, res) => {
  const logout = req.query.logout !== "false";
  try {
    const result = await manager.disconnect(req.params.sessionId, logout);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/v1/sessions/:sessionId/chats", async (req, res) => {
  try {
    const chats = await manager.listChats(req.params.sessionId);
    res.json({ items: chats });
  } catch (err) {
    const code = err.message === "SESSION_NOT_CONNECTED" ? 409 : 500;
    res.status(code).json({ error: err.message });
  }
});

app.get("/v1/sessions/:sessionId/chats/:jid/messages", async (req, res) => {
  const limit = Math.min(Number(req.query.limit || 50), 200);
  try {
    const items = await manager.listMessages(req.params.sessionId, req.params.jid, limit);
    res.json({ items });
  } catch (err) {
    const code = err.message === "SESSION_NOT_CONNECTED" ? 409 : 500;
    res.status(code).json({ error: err.message });
  }
});

app.post("/v1/sessions/:sessionId/chats/:jid/messages", async (req, res) => {
  const { text, quoted_message_id: quotedId } = req.body || {};
  if (!text?.trim()) return res.status(400).json({ error: "text required" });
  try {
    const result = await manager.sendText(
      req.params.sessionId,
      req.params.jid,
      text.trim(),
      quotedId || null,
    );
    res.json(result);
  } catch (err) {
    const code = err.message === "SESSION_NOT_CONNECTED" ? 409 : 500;
    res.status(code).json({ error: err.message });
  }
});

app.post("/v1/sessions/:sessionId/chats/:jid/documents", async (req, res) => {
  const { filename, mimetype, content_base64: contentBase64, caption } = req.body || {};
  if (!filename || !contentBase64) {
    return res.status(400).json({ error: "filename and content_base64 required" });
  }
  try {
    const result = await manager.sendDocument(req.params.sessionId, req.params.jid, {
      filename,
      mimetype,
      content_base64: contentBase64,
      caption,
    });
    res.json(result);
  } catch (err) {
    const code = err.message === "SESSION_NOT_CONNECTED" ? 409 : 500;
    res.status(code).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`JAIOS WhatsApp Bridge listening on :${PORT}`);
});
