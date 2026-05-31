# Multi-stage build for production
FROM public.ecr.aws/docker/library/node:22-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=/v1
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the Next.js application
RUN npm run build

# Production runtime
FROM public.ecr.aws/docker/library/node:22-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy built application from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/src ./src

EXPOSE 3000

ENV NODE_ENV=production
ENV NEXT_PUBLIC_API_URL=/v1

CMD ["npm", "run", "start"]
