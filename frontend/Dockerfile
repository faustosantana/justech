FROM node:22-alpine AS base
WORKDIR /app

FROM base AS development
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["sh", "-c", "rm -rf .next node_modules/.cache && npm run dev"]

FROM base AS production
RUN apk add --no-cache wget
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
ARG INTERNAL_API_URL=http://host.docker.internal:8001
ARG NEXT_PUBLIC_API_URL=
ARG NEXT_PUBLIC_APP_NAME=JAIOS
ENV INTERNAL_API_URL=$INTERNAL_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build \
  && cp -r public .next/standalone/public \
  && cp -r .next/static .next/standalone/.next/static
WORKDIR /app/.next/standalone
ENV PORT=3001
ENV HOSTNAME=0.0.0.0
EXPOSE 3001
CMD ["node", "server.js"]
