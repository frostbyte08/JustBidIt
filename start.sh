#!/bin/bash

# Kill anything already on these ports
kill $(lsof -t -i:3000) 2>/dev/null
kill $(lsof -t -i:8000) 2>/dev/null
sleep 1

# Start FastAPI backend
cd /home/ak4xu/Documents/JustBidIt/app/backend
source venv/bin/activate
uvicorn main:app --reload &

# Start frontend
cd /home/ak4xu/Documents/JustBidIt/app/frontend
python3 -m http.server 3000 &

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both"

wait
