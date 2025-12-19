// Minimal placeholder to verify package installation
console.log("whatsapp-pdf-bot node service placeholder");
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const fs = require("fs");
const path = require("path");
const stateManager = require("./state-manager");
const handlers = require("./handlers");

const UPLOADS_DIR = path.join(__dirname, "..", "shared", "uploads");

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

ensureDir(UPLOADS_DIR);
stateManager.loadSessions();

const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: path.join(__dirname, "..", "sessions"),
  }),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

client.on("qr", (qr) => {
  // show QR in terminal for manual scanning
  qrcode.generate(qr, { small: true });
  console.log("QR code generated - scan with WhatsApp mobile app");
});

client.on("ready", () => {
  console.log("WhatsApp client is ready");
});

client.on("auth_failure", (msg) => {
  console.error("Authentication failure:", msg);
});

client.on("disconnected", (reason) => {
  console.log("Client disconnected:", reason);
});

client.on("message", async (msg) => {
  try {
    if (msg.body) {
      const body = msg.body.trim();
      await handlers.handleCommand(msg, body);
    }

    if (msg.hasMedia) {
      await handlers.handleMedia(msg);
    }
  } catch (err) {
    console.error("Error handling message:", err);
  }
});

client.initialize();

module.exports = { client };
