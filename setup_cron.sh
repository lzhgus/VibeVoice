#!/bin/bash

# Script to set up cron jobs for podcast pipeline
# Runs twice daily: 7:10 AM PST (morning) and 5:10 PM PST (evening)

# Configuration
API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxbGdxd3Bsb2ZibHBwdHJ3dWFxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU5Mjc0OTUsImV4cCI6MjA3MTUwMzQ5NX0.6YiKaZZIhyr_6nOaDfLvhsCNHvWMLkKaMU4zRkKGi3s"
MODEL_PATH="/home/frank/ml/models/microsoft/VibeVoice-1.5B"
SCRIPT_PATH="/home/frank/ml/VibeVoice/run_podcast_pipeline.sh"

# Remove existing cron jobs for this script
echo "Setting up cron jobs for podcast pipeline..."

# Create a temporary file with the new cron jobs
TEMP_CRON=$(mktemp)

# Get existing crontab (excluding our podcast pipeline jobs)
crontab -l 2>/dev/null | grep -v "run_podcast_pipeline.sh" > "$TEMP_CRON"

# Add new cron jobs with UTC times
# Morning: 12:35 PM UTC (constant year-round)
# Evening: 20:35 PM UTC (constant year-round)
# Since system is now in UTC, we can use simple daily schedules

echo "# Podcast Pipeline - Morning (12:35 PM UTC)" >> "$TEMP_CRON"
echo "35 12 * * * cd /home/frank/ml/VibeVoice && ./run_podcast_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"morning\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/morning_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

echo "# Podcast Pipeline - Evening (21:35 PM UTC)" >> "$TEMP_CRON"
echo "35 21 * * * cd /home/frank/ml/VibeVoice && ./run_podcast_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"evening\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/evening_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "Scheduled jobs (UTC times):"
echo "- Morning: 12:35 PM UTC (daily, year-round)"
echo "- Evening: 20:35 PM UTC (daily, year-round)"
echo ""
echo "Note: Since system is now in UTC, no DST adjustments needed!"
echo ""
echo "Current crontab:"
crontab -l

# Create logs directory if it doesn't exist
mkdir -p /home/frank/ml/VibeVoice/logs

echo ""
echo "Logs will be saved to: /home/frank/ml/VibeVoice/logs/"
