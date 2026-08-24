# Use official Node.js image with Chromium pre-installed for Playwright
FROM mcr.microsoft.com/playwright:v1.48.0-noble

# Set working directory
WORKDIR /app

# Install system dependencies for stable 24/7 operation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install dependencies with production flag
RUN npm ci --only=production

# Copy application source code
COPY src/ ./src/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for health checks (optional)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Set environment for stable operation
ENV NODE_ENV=production \
    NODE_OPTIONS="--max-old-space-size=512"

# Start application
CMD ["npm", "start"]
