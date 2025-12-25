#!/bin/bash
TOKEN=$(curl -s -X POST "http://localhost:18000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

CHATBOT_ID="ffcdf94a-b91b-42b3-ac15-dd49b880e56b"

echo "=== 수정 전 경로 (잘못된 경로) ==="
curl -s "http://localhost:18000/api/v1/admin/chatbots/$CHATBOT_ID/versions" \
  -H "Authorization: Bearer $TOKEN" | jq .

echo ""
echo "=== 수정 후 경로 (올바른 경로) ==="
curl -s "http://localhost:18000/api/v1/chatbots/$CHATBOT_ID/versions" \
  -H "Authorization: Bearer $TOKEN" | jq .
