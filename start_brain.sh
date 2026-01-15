#!/bin/bash
lsof -ti :8000 | xargs kill -9
npm run clean
export PYTHONPATH=$PYTHONPATH:./src
./.venv/bin/python3 -m brain.server > /Users/olegkizyma/Documents/GitHub/atlastrinity/brain_start.log 2>&1 &
echo "Server started"
