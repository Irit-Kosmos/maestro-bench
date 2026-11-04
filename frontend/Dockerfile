# Production image: built by the GitHub CI (.github/workflows/ci.yml), run by
# deploy/docker-compose.yml.
# Development uses Dockerfile.local instead.
# Keep the base image in line with NODE_IMAGE in .gitlab-ci.yml
FROM node:24-alpine AS build

WORKDIR /app

# Reads the pnpm version from "packageManager" in package.json
RUN corepack enable

# Copy only dependency files first (layer cache: reinstalls only when these change)
COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

# Unneeded files are filtered by .dockerignore
COPY . .
RUN pnpm build


FROM node:24-alpine

LABEL org.opencontainers.image.title="MAESTRO-bench web application" \
      org.opencontainers.image.source="https://github.com/Irit-Kosmos/maestro-bench" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000

# The Nitro server is self-contained: no node_modules needed at runtime. The
# public runtime config (NUXT_PUBLIC_BACK_URL) is read when the server starts.
COPY --from=build /app/.output ./

USER node

EXPOSE 3000

CMD ["node", "server/index.mjs"]
