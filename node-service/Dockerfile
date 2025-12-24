FROM mcr.microsoft.com/playwright:v1.48.2-noble

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN apt-get update && apt-get install -y \
    libgbm-dev \
    libxss1 \
    libasound2t64 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN npm install

# Copy application code
COPY . .

# Expose the port for the health check
EXPOSE 3000

CMD ["node", "src/bot.js"]