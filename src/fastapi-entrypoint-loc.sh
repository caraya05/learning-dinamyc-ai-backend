#!/bin/sh
echo "Qwestar AI Backend" | figlet
echo "Waiting for mongodb..."
while ! nc -z 192.168.1.45 6000; do  sleep 2
echo "mongodb not started yet"
done
echo "mongodb started"
sleep 1
uvicorn main:app --reload --host 0.0.0.0 --port 9000 --forwarded-allow-ips='*' --proxy-headers
exec "$@"
