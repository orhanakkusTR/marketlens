# MarketLens frontend (development)
# Source kod docker-compose tarafından bind-mount edilir.
FROM node:20-alpine

WORKDIR /app

EXPOSE 5173

# Container açılışında:
#  - package-lock.json yoksa npm install ile lock dosyası oluşturulur (host'a yazılır, commit edilmesi gerekir)
#  - varsa, npm ci ile hızlı kurulum
# Sonra Vite dev server 0.0.0.0'da başlatılır.
CMD ["sh", "-c", "if [ -f package-lock.json ]; then npm ci; else npm install; fi && npm run dev -- --host 0.0.0.0"]
