const fs = require("fs");
const path = require("path");

// Persistent state for user sessions
const userSessions = new Map();
const STATE_FILE = path.join(
  __dirname,
  "..",
  "..",
  "state",
  "user_sessions.json"
);

function loadSessions() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const data = fs.readFileSync(STATE_FILE, "utf8");
      const sessions = JSON.parse(data);
      for (const [userId, session] of Object.entries(sessions)) {
        userSessions.set(userId, session);
      }
    }
  } catch (err) {
    console.warn("Failed to load sessions:", err.message);
  }
}

let saveTimeout;
function saveSessions() {
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    try {
      const sessions = {};
      for (const [userId, session] of userSessions) {
        sessions[userId] = session;
      }
      fs.writeFileSync(STATE_FILE, JSON.stringify(sessions, null, 2));
    } catch (err) {
      console.error("Failed to save sessions:", err.message);
    }
  }, 1000);
}

function getSession(userId) {
  return userSessions.get(userId);
}

function updateSession(userId, session) {
  userSessions.set(userId, session);
  saveSessions();
}

function clearSession(userId) {
  userSessions.delete(userId);
  saveSessions();
}

module.exports = {
  loadSessions,
  saveSessions,
  getSession,
  updateSession,
  clearSession,
};