#!/bin/bash
# Start ngrok tunnel for port 5000
echo "Starting ngrok tunnel for port 5000..."
echo "Please ensure you have authenticated ngrok with your auth token if needed."
echo "Run: ngrok config add-authtoken <your-token>"
echo ""
ngrok http 5000
