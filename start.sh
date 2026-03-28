#!/usr/bin/env bash
set -e

echo "🚀 Starting MCP Server on port 8002..."
uvicorn chatbot.mcp_server.mcp_server:app --host 0.0.0.0 --port 8002 &

echo "🚀 Starting Backend Server on port 8000..."
uvicorn server:app --host 0.0.0.0 --port 8000
