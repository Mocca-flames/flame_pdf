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
  const isGenerate =
    command === "/generate" || command === "/pdf" || command === "/done";
  const isClear = command === "/clear" || command === "/reset";
  const isHelp =
    command === "/help" ||
    command === "/start" ||
    command === "hi" ||
    command === "hello" ||
    command === "hey";

  if (isGenerate) {
    const last = generateCooldowns.get(userId) || 0;
    const now = Date.now();
    if (now - last < GENERATE_COOLDOWN_MS) {
      await msg.reply(
        "Hold on, just give me a few seconds before the next PDF request 😊"
      );
      return;
    }
    generateCooldowns.set(userId, now);

    const session = stateManager.getSession(userId);
    if (!session || session.images.length === 0) {
      await msg.reply(
        "Looks like you haven't sent any images yet. Send me some images first, then I can create your PDF!"
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
        "Hmm, I can't find your images on the server. Could you upload them again?"
      );
      stateManager.clearSession(userId);
      return;
    }

    if (images.length > MAX_IMAGES) {
      await msg.reply(
        `You've got ${images.length} images, but I can only handle up to ${MAX_IMAGES}. Try using /clear to start fresh!`
      );
      return;
    }

    await msg.reply(
      "Got it! Processing your images now, this might take a moment..."
    );
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
        await msg.reply(
          "Something went wrong with the PDF generation. Mind trying again in a bit?"
        );
        return;
      }

      // If response indicates demo image fallback
      if (resp.useDemo) {
        const demoPath = path.join(__dirname, "..", "..", "assets", "demo.png");
        if (!fs.existsSync(demoPath)) {
          await msg.reply(
            "Can't find the demo image right now. Please try again later!"
          );
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
        await msg.reply(
          "Couldn't get the PDF path. Give it another shot later?"
        );
        return;
      }
      if (!path.isAbsolute(pdfPath)) {
        pdfPath = path.join(imageDir, pdfPath);
      }

      if (!fs.existsSync(pdfPath)) {
        await msg.reply(
          "The PDF was generated but I can't seem to find it. That's odd!"
        );
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
        "All done! Your PDF is ready and I've cleaned up the temporary files 🎉"
      );
    } catch (err) {
      console.error("Error generating PDF:", err?.message || err);
      await msg.reply(
        "Sorry about that! Something went wrong on my end. Could you try again?"
      );
    }
  } else if (isClear) {
    const userDir = path.join(UPLOADS_DIR, userId);
    if (fs.existsSync(userDir)) {
      fs.rmSync(userDir, { recursive: true, force: true });
    }
    stateManager.clearSession(userId);
    await msg.reply(
      "All cleared! Your images have been deleted and we can start fresh."
    );
  } else if (isHelp) {
    await msg.reply(
      "👋 Hey there! Welcome to Flame PDF Bot!\n\n" +
        "I help you convert your images into a single PDF document.\n\n" +
        "Here's how it works:\n" +
        "1. Send me one or more images (JPEG or PNG)\n" +
        "2. When you're ready, just type `/pdf` or `/done` and I'll create your document\n\n" +
        "Commands you can use:\n" +
        "• `/pdf` or `/done` - Create your PDF from the images you've sent\n" +
        "• `/clear` or `/reset` - Delete all images and start over\n" +
        "• `/help` - Show this message again"
    );
  } else {
    // Catch-all for unrecognized text input
    await msg.reply(
      "I can only work with images and commands right now. Send me a JPEG or PNG image, or try one of these:\n" +
        "• `/pdf` - Generate your PDF\n" +
        "• `/help` - Get help and instructions"
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
      "I can only accept JPEG or PNG images. Could you send a different file?"
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
      `You've hit the limit of ${MAX_IMAGES} images. Use /clear if you want to start over!`
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
    `Got image ${session.images.length}! Send more \n or type /pdf when you're ready.`
  );
}

module.exports = {
  handleCommand,
  handleMedia,
};
