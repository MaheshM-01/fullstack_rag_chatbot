FROM node:20-alpine AS base
WORKDIR /app

COPY package.json package-lock.json turbo.json ./
COPY apps/api/package.json apps/api/package.json

RUN npm install --workspace apps/api --include-workspace-root

COPY apps/api apps/api

RUN npm run build --workspace apps/api

EXPOSE 3001
CMD ["npm", "run", "start", "--workspace", "apps/api"]
