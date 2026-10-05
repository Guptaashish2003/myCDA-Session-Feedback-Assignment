FROM node:20-alpine

WORKDIR /app

# Install packages first so this layer is cached until package files change
COPY package.json package-lock.json ./
RUN npm ci

# Copies the source and frontend/.env (if present). `next build` reads .env, so
# NEXT_PUBLIC_API_URL is baked into the browser bundle here.
# Without a .env file the API client falls back to http://localhost:8000/api/v1.
COPY . .

RUN npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
