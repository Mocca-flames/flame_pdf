# WhatsApp PDF Bot - Deployment Guide

This document provides instructions for setting up and running the WhatsApp PDF Bot using Docker Compose.

## 🐳 Prerequisites

You must have the following installed on your deployment machine:

1.  **Docker**: [Installation Guide](https://docs.docker.com/get-docker/)
2.  **Docker Compose** (usually included with Docker Desktop)

## 🚀 Deployment

The entire application stack (Node.js WhatsApp Client and Python PDF Worker) is orchestrated using Docker Compose.

### 1. Setup Environment Variables

The services rely on environment variables defined in the `docker-compose.yml` file. For local testing or production, you should create a `.env` file in the root directory to manage secrets and configuration, although the current setup uses hardcoded values in `docker-compose.yml` for simplicity.

### 2. Build and Run

Navigate to the root directory of the project (`whatsapp-pdf-bot/`) and run the following command:

```bash
docker-compose up --build -d
```

- `--build`: Forces a rebuild of the service images (recommended for the first run or after code changes).
- `-d`: Runs the containers in detached mode (in the background).

### 3. Initial Authentication

The `whatsapp-bot` service requires authentication via a QR code.

1.  View the logs for the `whatsapp-bot` service:
    ```bash
    docker-compose logs -f whatsapp-bot
    ```
2.  Wait for the QR code to appear in the logs.
3.  Scan the QR code using your WhatsApp mobile app (Settings > Linked Devices > Link a Device).
4.  Once authenticated, the logs will show "WhatsApp client is ready".

### 4. Monitoring and Health

You can monitor the services using the following commands:

| Service        | Port | Health Check URL               |
| :------------- | :--- | :----------------------------- |
| `whatsapp-bot` | 3000 | `http://localhost:3000/health` |
| `pdf-worker`   | 8000 | `http://localhost:8000/health` |

- **View Logs**:
  ```bash
  docker-compose logs -f
  ```
- **Check Service Status**:
  ```bash
  docker-compose ps
  ```
- **Check Health Status**:
  ```bash
  docker inspect --format='{{json .State.Health}}' whatsapp-pdf-bot_whatsapp-bot_1
  docker inspect --format='{{json .State.Health}}' whatsapp-pdf-bot_pdf-worker_1
  ```

### 5. Stopping and Cleanup

To stop the services and remove the containers, networks, and volumes:

```bash
docker-compose down -v
```

- `-v`: Removes the volumes (`shared` and `state`), which will delete all uploaded images, generated PDFs, and the WhatsApp session data. Use this with caution.

## ⚙️ Configuration

The following environment variables are used:

| Service        | Variable          | Description                                                |
| :------------- | :---------------- | :--------------------------------------------------------- |
| `whatsapp-bot` | `PYTHON_API_URL`  | Internal URL for the PDF worker (`http://pdf-worker:8000`) |
| `whatsapp-bot` | `UPLOAD_DIR`      | Shared volume path (`/shared/uploads`)                     |
| `pdf-worker`   | `UPLOAD_DIR`      | Shared volume path (`/shared/uploads`)                     |
| `pdf-worker`   | `MAX_PDF_SIZE_MB` | Maximum allowed PDF size                                   |
