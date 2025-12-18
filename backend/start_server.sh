#!/bin/bash

# Infinite loop
while true
do
    echo "Starting uvicorn..."
    uvicorn main:app --host 0.0.0.0 --port 8081
    echo "Uvicorn exited. Restarting in 2s..."
    sleep 2
done