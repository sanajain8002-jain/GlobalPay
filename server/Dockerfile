FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY server/package.json ./server/
COPY prisma ./prisma/
RUN npm install --omit=dev
COPY server/src ./server/src
EXPOSE 4000
HEALTHCHECK --interval=15s --timeout=5s --retries=3 CMD wget -qO- http://localhost:4000/api/v1/system/health/liveness || exit 1
CMD ["node", "server/src/runtime.mjs"]
