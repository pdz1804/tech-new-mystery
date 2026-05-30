#!/bin/bash

# Get a test token (this assumes you have auth set up)
# For testing, we'll just show the curl command

echo "Testing chat API stream..."
echo ""
echo "Command to run:"
echo 'curl -X POST "http://localhost:8000/v1/chat/sessions/{session_id}/stream" \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "Authorization: Bearer YOUR_TOKEN" \'
echo '  -d '"'"'{"content":"What is 2+2?"}'"'"' \'
echo '  -N'
echo ""
echo "Expected event sequence:"
echo "1. token events (initial response)"
echo "2. tool_invocation event"
echo "3. tool_result event"  
echo "4. token events (final answer) <-- THIS IS MISSING"
echo "5. done event"
