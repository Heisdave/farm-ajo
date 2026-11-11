#!/usr/bin/env bash
# Capture a REAL Farm Ajo run from a fresh copy: one command (./run.sh),
# seeded circle -> shortfalls -> contributions -> purchase -> receipt.
set -u
ENV_DIR=~/workspace/tmp-ajo-test
CAP=~/workspace/projects/farm-ajo/demo/proof/capture
mkdir -p "$CAP"
cd "$ENV_DIR" || exit 1
rm -rf data .venv
nohup ./run.sh > "$CAP/server.log" 2>&1 &
SRV=$!
echo "server pid $SRV, waiting for port 8792..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null localhost:8792/circle; then echo "up after ~$((i*3))s"; break; fi
  sleep 3
done

pretty() { python3 -m json.tool 2>/dev/null || cat; }

echo '$ curl localhost:8792/circle' > "$CAP/step1.txt"
curl -s localhost:8792/circle | pretty >> "$CAP/step1.txt"

echo '$ curl localhost:8792/farmers' > "$CAP/step2.txt"
curl -s localhost:8792/farmers | pretty >> "$CAP/step2.txt"

echo '$ curl -X POST localhost:8792/agent/tick' > "$CAP/step3.txt"
curl -s -X POST localhost:8792/agent/tick | pretty >> "$CAP/step3.txt"

{
  echo "$ curl -X POST localhost:8792/contributions -d '{\"farmer_id\": \"farmer-emeka-nwosu\", \"amount\": 5000}'"
  curl -s -X POST localhost:8792/contributions -H 'Content-Type: application/json' -d '{"farmer_id": "farmer-emeka-nwosu", "amount": 5000}' | pretty
  echo "$ curl -X POST localhost:8792/contributions -d '{\"farmer_id\": \"farmer-halima-usman\", \"amount\": 2500}'"
  curl -s -X POST localhost:8792/contributions -H 'Content-Type: application/json' -d '{"farmer_id": "farmer-halima-usman", "amount": 2500}' | pretty
} > "$CAP/step4.txt"

echo '$ curl -X POST localhost:8792/agent/tick' > "$CAP/step5.txt"
curl -s -X POST localhost:8792/agent/tick | pretty >> "$CAP/step5.txt"

echo '$ curl localhost:8792/receipts' > "$CAP/step6.txt"
curl -s localhost:8792/receipts | pretty >> "$CAP/step6.txt"

echo '$ curl localhost:8792/circle' > "$CAP/step7.txt"
curl -s localhost:8792/circle | pretty >> "$CAP/step7.txt"

kill $SRV 2>/dev/null
pkill -f "uvicorn app.main:app" 2>/dev/null
echo "=== capture done ==="
wc -l "$CAP"/step*.txt
