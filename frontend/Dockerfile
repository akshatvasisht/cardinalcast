# Stage 1: Build the Vite app
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Expose port 80
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
