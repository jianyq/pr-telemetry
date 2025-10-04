#!/bin/bash
# 快速查询trace的脚本

TRACE_ID="${1:-trace-a0dfa2b87929}"
TOKEN="dev_token_12345"

echo "🔍 查询 Trace: $TRACE_ID"
echo "================================"
echo ""

# 完整信息
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/traces/$TRACE_ID | python3 -m json.tool

