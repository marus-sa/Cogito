FROM node:22-alpine AS frontend

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM python:3.13-slim

WORKDIR /app
ENV FLASK_ENV=production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY server ./server
COPY --from=frontend /app/dist ./dist

RUN useradd --create-home cogito
USER cogito
EXPOSE 5000

CMD ["sh", "-c", "gunicorn --chdir server --bind 0.0.0.0:${PORT:-5000} app:app"]
