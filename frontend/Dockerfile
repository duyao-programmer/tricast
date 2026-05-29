# 阶段1：Node 构建
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# 阶段2：Nginx + 静态文件
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
RUN echo '<html><body><h1>Service Unavailable</h1></body></html>' > /usr/share/nginx/html/50x.html
