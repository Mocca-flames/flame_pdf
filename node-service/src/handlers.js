const { MessageMedia } = require("whatsapp-web.js");
const fs = require("fs");
const path = require("path");
const stateManager = require("./state-manager");
const apiClient = require("./api-client");

const UPLOADS_DIR =
  process.env.UPLOAD_DIR || path.join(__dirname, "..", "shared", "uploads");
const MAX_IMAGES = parseInt(process.env.MAX_IMAGES, 10) || 20;
const GENERATE_COOLDOWN_MS = 5000;
const generateCooldowns = new Map();

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

async function handleCommand(msg, body) {
  const from = msg.from;
  const userId = from.split("@")[0];
  const command = body.toLowerCase();

  // Command Aliases and Flexible Matching
  const isGenerate = command === "/generate" || command === "/pdf" || command === "/done";
  const isClear = command === "/clear" || command === "/reset";
  const isHelp = command === "/help" || command === "/start" || command === "hi" || command === "hello" || command === "hey";

  if (isGenerate) {
    const last = generateCooldowns.get(userId) || 0;
    const now = Date.now();
    if (now - last < GENERATE_COOLDOWN_MS) {
      await msg.reply(
        "Please wait a few seconds before requesting another PDF."
      );
      return;
    }
    generateCooldowns.set(userId, now);

    const session = stateManager.getSession(userId);
    if (!session || session.images.length === 0) {
      await msg.reply(
        "❌ Please send one or more images before using /pdf."
      );
      return;
    }
    const images = session.images;

    // Verify images exist on disk
    const imageDir = path.join(UPLOADS_DIR, userId);
    const missingImages = images.filter(
      (img) => !fs.existsSync(path.join(imageDir, img))
    );

    if (missingImages.length === images.length) {
      await msg.reply(
        "❌ No images found on server. Please re-upload your images."
      );
      stateManager.clearSession(userId);
      return;
    }

    if (images.length > MAX_IMAGES) {
      await msg.reply(
        `Too many images (${images.length}). Max is ${MAX_IMAGES}. Use /clear or /reset and try again.`
      );
      return;
    }

    await msg.reply("⏳ Processing your images, this may take a moment...");
    ensureDir(imageDir);

    // Write READY.txt signal
    const readyPath = path.join(imageDir, "READY.txt");
    console.log(`[handlers] Writing READY.txt to ${readyPath}`);
    fs.writeFileSync(readyPath, "");
    console.log(`[handlers] READY.txt written successfully`);

    try {
      console.log(
        `[handlers] Triggering PDF generation for user ${userId} in ${imageDir}`
      );
      const resp = await apiClient.generatePdf(userId, imageDir);

      if (!resp?.success) {
        await msg.reply("PDF generation failed on worker. Try again later.");
        return;
      }

      // If response indicates demo image fallback
      if (resp.useDemo) {
        const demoPath = path.join(__dirname, "..", "..", "assets", "demo.png");
        if (!fs.existsSync(demoPath)) {
          await msg.reply("Demo image not found. Try again later.");
          return;
        }
        const demoData = fs.readFileSync(demoPath);
        const demoBase64 = demoData.toString("base64");
        const demoMedia = new MessageMedia("image/png", demoBase64, "demo.png");
        await msg.client.sendMessage(msg.from, demoMedia);

        // Cleanup: delete session
        stateManager.clearSession(userId);

        return;
      }

      // Safely resolve PDF path
      let pdfPath = resp.pdfPath || null;
      if (pdfPath === null) {
        await msg.reply("PDF path not provided. Try again later.");
        return;
      }
      if (!path.isAbsolute(pdfPath)) {
        pdfPath = path.join(imageDir, pdfPath);
      }

      if (!fs.existsSync(pdfPath)) {
        await msg.reply("PDF file not found after generation.");
        return;
      }

      const data = fs.readFileSync(pdfPath);
      const base64 = data.toString("base64");
      const media = new MessageMedia(
        "application/pdf",
        base64,
        path.basename(pdfPath)
      );

      await msg.client.sendMessage(msg.from, media, {
        sendMediaAsDocument: true,
      });

      // Cleanup: delete PDF immediately
      try {
        if (fs.existsSync(pdfPath)) fs.unlinkSync(pdfPath);
      } catch (e) {
        console.warn("Failed to delete PDF:", e?.message || e);
      }

      // Cleanup: delete session
      stateManager.clearSession(userId);

      await msg.reply(
        "✅ Your PDF is ready! Temporary files have been cleaned up."
      );
    } catch (err) {
      console.error("Error generating PDF:", err?.message || err);
      await msg.reply(
        "❌ Sorry, the PDF generation failed due to a service error. Please try again."
      );
    }
  } else if (isClear) {
    const userDir = path.join(UPLOADS_DIR, userId);
    if (fs.existsSync(userDir)) {
      fs.rmSync(userDir, { recursive: true, force: true });
    }
    stateManager.clearSession(userId);
    await msg.reply("Cleared your uploaded images.");
  } else if (isHelp) {
    await msg.reply(
      "👋 Welcome to the Flame PDF Bot!\n\n" +
        "I can convert your images into a single PDF document.\n\n" +
        "How to use:\n" +
        "1. Send me one or more JPEG or PNG images.\n" +
        "2. When you are done, type `/pdf` (or `/done`) to generate the document.\n\n" +
        "Available commands:\n" +
        "• `/pdf` or `/done` - Generate PDF from uploaded images\n" +
        "• `/clear` or `/reset` - Clear all uploaded images and start over\n" +
        "• `/help` - Show this message again"
    );
  } else {
    // Catch-all for unrecognized text input
    await msg.reply(
      "I only understand images and commands. Please send me a JPEG or PNG image, or use one of the commands:\n" +
      "• `/pdf` to generate your PDF\n" +
      "• `/help` for instructions"
    );
  }
}

async function handleMedia(msg) {
  const from = msg.from;
  const userId = from.split("@")[0];

  const media = await msg.downloadMedia();
  if (!media || !media.data) return;

  const mimetype = (media.mimetype || "").toLowerCase();
  if (!/(image\/(jpeg|jpg|png))/i.test(mimetype)) {
    await msg.reply(
      "Unsupported file type. Please send JPEG or PNG images only."
    );
    return;
  }

  const extRaw = mimetype.includes("/")
    ? mimetype.split("/")[1].split(";")[0]
    : "bin";
  const ext = extRaw === "jpeg" ? "jpg" : extRaw;

  const userDir = path.join(UPLOADS_DIR, userId);
  ensureDir(userDir);

  let session = stateManager.getSession(userId);
  if (!session) {
    session = {
      images: [],
      timestamp: new Date().toISOString(),
      status: "collecting",
    };
  }
  if (session.images.length >= MAX_IMAGES) {
    await msg.reply(
      `Image limit reached. Max ${MAX_IMAGES} images allowed. Use /clear to reset.`
    );
    return;
  }

  const filename = `img_${String(session.images.length + 1).padStart(
    3,
    "0"
  )}.${ext}`;
  const filePath = path.join(userDir, filename);

  console.log(`[handlers] Saving image to ${filePath}`);
  const buffer = Buffer.from(media.data, "base64");
  fs.writeFileSync(filePath, buffer);
  console.log(`[handlers] Image saved successfully`);

  session.images.push(filename);
  stateManager.updateSession(userId, session);

  await msg.reply(
    `Image ${session.images.length} received. Send more or type /pdf`
  );
}

module.exports = {
  handleCommand,
  handleMedia,
};
