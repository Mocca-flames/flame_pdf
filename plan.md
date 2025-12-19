### Implementation Plan for Phase 4 Enhancements

The remaining tasks focus on robustness and user experience, primarily affecting the Node.js service's command handler and API client, and the Python service's error handling and cleanup.

#### 1. Cleanup (Delete images after PDF sent)

The architecture delegates image/signal cleanup to the Python service and PDF cleanup to the Node.js service.

- **Node.js Service (node-service/src/handlers.js)**: Implement file system logic to delete the PDF file (path returned by the Python API) after successfully sending it to the user via WhatsApp.
- **Python Service (python-worker/pdf_builder.py or python-worker/main.py)**: Verify and ensure the file system cleanup of all images and the READY.txt signal is executed reliably _before_ the API response is sent.

#### 2. Error Handling (No images, API timeout)

- **Pre-API Validation (node-service/src/handlers.js)**:
  - Check the user's session state (via node-service/src/state-manager.js) for collected images upon receiving the /generate command.
  - If no images are found, send a user feedback message: "You haven't sent any images yet. Please send one or more images to start."
- **API Communication Errors (node-service/src/api-client.js)**:
  - Implement robust error handling for the HTTP call to the Python service (e.g., network errors, timeouts).
  - If the API call fails, the Node.js service should send a user-friendly message: "The PDF generation service is currently unavailable. Please try again in a moment."
- **Internal PDF Generation Errors (python-worker/main.py & node-service/src/handlers.js)**:
  - **Python Service**: Modify the /generate-pdf endpoint to catch internal errors (e.g., corrupted image, PDF creation failure) and return a structured error response: {"success": false, "error": "Detailed error message"}.
  - **Node.js Service**: Check the 'success' flag in the API response. If false, send the user a message: "Failed to generate PDF. The service reported an issue. Try again or contact support."

#### 3. User Feedback Messages

- **Start of Processing (node-service/src/handlers.js)**: Send a message to the user immediately after validation and before the API call: "Processing your {N} images into a PDF. This may take a moment..."
- **Success (node-service/src/handlers.js)**: Send the PDF file, followed by a confirmation message: "✅ Your PDF is ready! The source images have been deleted to save space."

#### Todo List for Code Mode

```markdown
1. [ ] Refactor Node.js command handler (handlers.js) to check for images in state and send "No images collected" error message if count is zero.
2. [ ] Add "Processing {N} images..." user feedback message in Node.js (handlers.js) before calling Python API.
3. [ ] Update Node.js API client (api-client.js) to handle HTTP errors (timeout, network) and return a structured failure object.
4. [ ] Implement Node.js logic (handlers.js) to check the API response's 'success' flag and send appropriate user-friendly error messages for API failures or internal Python errors.
5. [ ] Implement Node.js logic (handlers.js) to delete the generated PDF file after successful delivery to the user.
6. [ ] Ensure Python service (pdf_builder.py/main.py) robustly deletes images and READY.txt on success.
7. [ ] Implement Python service error handling to catch exceptions during PDF creation and return a structured error response (success: false) to the Node.js service.
8. [ ] Update implementation.md to mark Phase 4 tasks as completed or in-progress.
```
