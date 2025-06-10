#!/bin/sh
echo "Qwestar AI Backend"
sleep 1
uvicorn main:app --reload --host 0.0.0.0 --port 9000 --forwarded-allow-ips='*' --proxy-headers
exec "$@"
