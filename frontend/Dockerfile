# Multi-stage: build React, then serve static + reverse-proxy /api via NGINX (TLS).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
# REACT_APP_BACKEND_URL is baked at build time. Same origin as the site so cookies work.
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
RUN yarn build

FROM nginx:stable-alpine
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/nexus.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80 443
