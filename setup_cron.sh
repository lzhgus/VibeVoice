#!/bin/bash

# Script to set up cron jobs for podcast pipeline
# Runs twice daily: 7:10 AM PST (morning) and 5:10 PM PST (evening)

# Configuration
API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxbGdxd3Bsb2ZibHBwdHJ3dWFxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU5Mjc0OTUsImV4cCI6MjA3MTUwMzQ5NX0.6YiKaZZIhyr_6nOaDfLvhsCNHvWMLkKaMU4zRkKGi3s"
MODEL_PATH="/home/frank/ml/models/microsoft/VibeVoice-1.5B"
SCRIPT_PATH="/home/frank/ml/VibeVoice/run_podcast_pipeline.sh"
STOCK_SCRIPT_PATH="/home/frank/ml/VibeVoice/run_stock_digest_pipeline.sh"
# Update the ticker list as needed
# STOCK_TICKERS=("MSFT" "NVDA")

# Remove existing cron jobs for this script
echo "Setting up cron jobs for podcast pipeline..."

# Create a temporary file with the new cron jobs
TEMP_CRON=$(mktemp)

# Get existing crontab (excluding our podcast pipeline jobs)
crontab -l 2>/dev/null | grep -v "run_podcast_pipeline.sh" | grep -v "run_stock_digest_pipeline.sh" > "$TEMP_CRON"

# Add new cron jobs with UTC times
# Morning: 12:35 PM UTC (Monday-Friday only, excludes weekends)
# Evening: 21:35 PM UTC (Monday-Friday only, excludes weekends)
# Since system is now in UTC, we can use simple daily schedules

echo "# Podcast Pipeline - Morning (12:35 PM UTC, Monday-Friday)" >> "$TEMP_CRON"
echo "35 12 * * 1-5 cd /home/frank/ml/VibeVoice && ./run_podcast_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"morning\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/morning_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

echo "# Podcast Pipeline - Evening (21:35 PM UTC, Monday-Friday)" >> "$TEMP_CRON"
echo "35 21 * * 1-5 cd /home/frank/ml/VibeVoice && ./run_podcast_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"evening\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/evening_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

# Add weekly cron jobs for Saturday and Sunday (morning only)
echo "# Podcast Pipeline - Weekly Saturday (12:35 PM UTC)" >> "$TEMP_CRON"
echo "35 12 * * 6 cd /home/frank/ml/VibeVoice && ./run_podcast_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"weekly\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/weekly_saturday_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

echo "# Podcast Pipeline - Weekly Sunday (12:35 PM UTC)" >> "$TEMP_CRON"
echo "35 12 * * 0 cd /home/frank/ml/VibeVoice && ./run_podcast_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"weekly\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/weekly_sunday_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

# Add stock digest cron jobs at 13:00 UTC
# Process all available digests for the date (no ticker filter)
echo "# Stock Digest Pipeline (13:00 UTC) - Batch processing all available digests" >> "$TEMP_CRON"
echo "0 13 * * * cd /home/frank/ml/VibeVoice && ./run_stock_digest_pipeline.sh \"\$(date +\%Y-\%m-\%d)\" \"$API_KEY\" \"$MODEL_PATH\" >> /home/frank/ml/VibeVoice/logs/stock_digest_\$(date +\%Y\%m\%d).log 2>&1" >> "$TEMP_CRON"

# Install the new crontab
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "Scheduled jobs (UTC times):"
echo "- Morning: 12:35 PM UTC (Monday-Friday only)"
echo "- Evening: 21:35 PM UTC (Monday-Friday only)"
echo "- Weekly Saturday: 12:35 PM UTC (morning only, weekly)"
echo "- Weekly Sunday: 12:35 PM UTC (morning only, weekly)"
echo "- Stock Digest: 13:00 UTC (daily, processes all available digests for the date)"
echo ""
echo "Note: Since system is now in UTC, no DST adjustments needed!"
echo ""
echo "Current crontab:"
crontab -l

# Create logs directory if it doesn't exist
mkdir -p /home/frank/ml/VibeVoice/logs
mkdir -p /home/frank/ml/VibeVoice/logs/stock_digests

echo ""
echo "Logs will be saved to: /home/frank/ml/VibeVoice/logs/"
