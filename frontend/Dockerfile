# ──────────────────────────────────────────────────────────────────────────────
# Frontend Production Dockerfile (Vite + TanStack Nitro)
# ──────────────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS builder

WORKDIR /app

# Copy dependency manifests
COPY package*.json ./
RUN npm ci

# Copy source code and compile production bundle
COPY . .
RUN npm run build

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2: Minimal Node Runner
# ──────────────────────────────────────────────────────────────────────────────
FROM node:24-alpine AS runner

WORKDIR /app

COPY --from=builder /app/.output ./.output
COPY --from=builder /app/package*.json ./

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=5173

EXPOSE 5173

CMD ["node", ".output/server/index.mjs"]
