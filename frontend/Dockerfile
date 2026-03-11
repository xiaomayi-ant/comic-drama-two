# ── Stage 1: build ──
FROM node:20-alpine AS builder

WORKDIR /app

# 先复制依赖清单，利用 layer cache
COPY package.json package-lock.json ./

# 安装 Python 和构建工具（用于可能的原生依赖编译）
# 使用阿里云镜像源加速
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
    apk add --no-cache python3 make g++

RUN npm ci

# 复制源码并构建
COPY . .
RUN npm run build

# ── Stage 2: nginx 静态服务 ──
FROM nginx:stable-alpine AS runtime

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
