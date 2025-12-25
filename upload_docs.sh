#!/bin/bash
CHATBOT_ID="07f53f0d-25e1-478c-9d91-34109d697ec1"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzNjcwZjUxNy03OGVlLTRmZWItYTgyNi0xM2RlMTc1MzcxMjYiLCJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIiwiZXhwIjoxNzY2NTA1MjE5fQ.gRkg3_7a4BS4u2xdhlEdxvWLBup9KGCwAIuSkdyiQXI"

for pdf in /home/magic/work/GraphRAG/data/*.pdf; do
  filename=$(basename "$pdf")
  echo "Uploading: $filename"
  result=$(curl -s -X POST "http://localhost:18000/api/v1/chatbots/$CHATBOT_ID/documents" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$pdf")
  echo "  Result: $result" | head -c 200
  echo ""
done
