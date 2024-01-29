#!/bin/sh
echo "AI toys Backend" | figlet
echo "Waiting for postgres..."
while ! nc -z $host_database $port_database; do  sleep 1
done
echo "PostgreSQL started"
sleep 1
uvicorn main:app --reload --host 0.0.0.0 --port 9000 --forwarded-allow-ips='*' --proxy-headers
exec "$@"
