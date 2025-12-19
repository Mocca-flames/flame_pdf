const axios = require("axios");

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

async function generatePdf(userId, imageDir) {
  const url = `${PYTHON_API_URL.replace(/\/$/, "")}/generate-pdf`;
  console.log(`[api-client] Sending request to ${url} for user ${userId}`);
  const startTime = Date.now();
  try {
    const response = await axios.post(
      url,
      {
        userId: userId,
        imageDir: imageDir,
      },
      {
        timeout: 30000, // 30 seconds timeout
      }
    );
    const duration = Date.now() - startTime;
    console.log(`[api-client] Received response from ${url} in ${duration}ms:`, response.data);
    if (response.status !== 200) {
      throw new Error(
        `API returned status ${response.status}: ${response.statusText}`
      );
    }
    return response.data;
  } catch (error) {
    if (error.code === "ECONNREFUSED" || error.code === "ENOTFOUND") {
      throw new Error(
        "Connection failed: Unable to reach the PDF generation service."
      );
    } else if (error.code === "ETIMEDOUT") {
      throw new Error("Request timed out: PDF generation took too long.");
    } else if (error.response) {
      throw new Error(
        `API error: ${error.response.status} - ${error.response.statusText}`
      );
    } else {
      throw new Error(`Unexpected error: ${error.message}`);
    }
  }
}

module.exports = {
  generatePdf,
};
