#!/bin/bash

# Test script to manually run the podcast pipeline command
# This simulates what the cron job will run

API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxbGdxd3Bsb2ZibHBwdHJ3dWFxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU5Mjc0OTUsImV4cCI6MjA3MTUwMzQ5NX0.6YiKaZZIhyr_6nOaDfLvhsCNHvWMLkKaMU4zRkKGi3s"
MODEL_PATH="/home/frank/ml/models/microsoft/VibeVoice-1.5B"

# Get today's date in YYYY-MM-DD format
TODAY=$(date +%Y-%m-%d)

echo "Testing podcast pipeline with today's date: $TODAY"
echo ""

# Allow override of time parameter
TIME=${1:-morning}

echo "Running: ./run_podcast_pipeline.sh \"$TODAY\" \"$TIME\" \"[API_KEY]\" \"$MODEL_PATH\""
echo ""

cd /home/frank/ml/VibeVoice
./run_podcast_pipeline.sh "$TODAY" "$TIME" "$API_KEY" "$MODEL_PATH"
