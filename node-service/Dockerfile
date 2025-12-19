FROM mcr.microsoft.com/playwright:v1.48.2-noble

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose the port for the health check
EXPOSE 3000

CMD ["node", "src/bot.js"]