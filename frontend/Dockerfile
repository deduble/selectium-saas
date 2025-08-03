# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies needed for building
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package*.json ./
COPY yarn.lock* ./

# Install all dependencies (needed for build)
RUN npm ci && npm cache clean --force

# Copy source code
COPY . .

# Copy and make entrypoint executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production

# Build arguments for Next.js public env vars
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ARG NEXT_PUBLIC_APP_URL

# Set build-time environment variables
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL

# Build the application
RUN npm run build

# Verify build completed successfully and BUILD_ID exists
RUN ls -la /app/.next && test -f /app/.next/BUILD_ID

# Production stage  
FROM node:18-alpine AS runner

WORKDIR /app

# Security hardening and runtime dependencies
RUN apk add --no-cache libc6-compat curl ca-certificates su-exec && \
    rm -rf /var/cache/apk/*

# Create selextract user and group with consistent UID/GID (Alpine syntax)
RUN addgroup -g 1001 -S selextract && \
    adduser -u 1001 -S -G selextract -s /bin/bash selextract

# Copy built application from builder stage
COPY --from=builder /app/public ./public

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=selextract:selextract /app/.next/standalone ./
COPY --from=builder --chown=selextract:selextract /app/.next/static ./.next/static

# Copy BUILD_ID and other essential .next files
COPY --from=builder --chown=selextract:selextract /app/.next/BUILD_ID ./.next/BUILD_ID
COPY --from=builder --chown=selextract:selextract /app/.next/cache ./.next/cache

# Set correct permissions for .next directory and ensure it exists with proper structure
RUN chown -R selextract:selextract .next && \
    mkdir -p .next/cache && \
    chown -R selextract:selextract .next/cache && \
    ls -la .next/ && \
    test -f .next/BUILD_ID

# Copy entrypoint script from builder stage
COPY --from=builder /entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER selextract

# Expose port
EXPOSE 3000

# Set environment variables
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Use entrypoint script to ensure proper startup
ENTRYPOINT ["/entrypoint.sh"]