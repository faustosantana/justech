FROM node:22-alpine AS base
WORKDIR /app

FROM base AS development
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
# Limpiar .next solo al ARRANCAR el contenedor (antes de next dev).
# No ejecutar npm run build con el contenedor dev en marcha — corrompe middleware.js.
CMD ["sh", "-c", "rm -rf .next node_modules/.cache && npm run dev"]

FROM base AS production
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
