#!/bin/sh
# ============================================================================
# 生成自签名 TLS 证书供演示环境 HTTPS 使用
# 在 nginx 容器启动前由 /docker-entrypoint.d/ 自动执行
# ============================================================================
set -e

CERT_DIR="/etc/nginx/certs"
CERT_FILE="$CERT_DIR/nginx-selfsigned.crt"
KEY_FILE="$CERT_DIR/nginx-selfsigned.key"

mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "[init-certs] 生成自签名证书..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=TriCast Demo/CN=localhost"
    chmod 600 "$KEY_FILE"
    echo "[init-certs] 证书生成完成。"
else
    echo "[init-certs] 证书已存在，跳过。"
fi
