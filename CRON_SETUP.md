# Podcast Pipeline Cron Job Setup

This document explains how to set up automated daily podcast generation.

## Overview

The system runs twice daily:
- **7:10 AM PST**: Morning podcast generation
- **5:10 PM PST**: Evening podcast generation

Each run automatically:
1. Downloads the podcast script for today's date
2. Generates audio using VibeVoice AI
3. Uploads the generated audio to the server

## Installation

### Step 1: Run the Setup Script

```bash
cd /home/frank/ml/VibeVoice
./setup_cron.sh
```

This will:
- Install two cron jobs (morning and evening)
- Create a logs directory for output
- Display the installed cron schedule

### Step 2: Verify Installation

Check that the cron jobs are installed:

```bash
crontab -l
```

You should see two entries for the podcast pipeline.

## Testing

### Test the Command Manually

Before relying on cron, test the pipeline manually:

```bash
cd /home/frank/ml/VibeVoice

# Test morning run
./test_cron_command.sh morning

# Test evening run
./test_cron_command.sh evening
```

### Test with a Specific Date

```bash
./run_podcast_pipeline.sh "2025-10-15" "morning" "YOUR_API_KEY" "/home/frank/ml/models/microsoft/VibeVoice-1.5B"
```

## Log Files

Logs are automatically saved to:
- Morning runs: `/home/frank/ml/VibeVoice/logs/morning_YYYYMMDD.log`
- Evening runs: `/home/frank/ml/VibeVoice/logs/evening_YYYYMMDD.log`

### View Recent Logs

```bash
# View today's morning log
cat /home/frank/ml/VibeVoice/logs/morning_$(date +%Y%m%d).log

# View today's evening log
cat /home/frank/ml/VibeVoice/logs/evening_$(date +%Y%m%d).log

# Tail logs in real-time
tail -f /home/frank/ml/VibeVoice/logs/morning_*.log
```

## Cron Schedule Details

The cron jobs use the following schedule:

```
10 7 * * *   # 7:10 AM daily
10 17 * * *  # 5:10 PM daily
```

**Note about timezones:**
- The cron times assume your system is set to PST/PDT
- If your system uses UTC, you'll need to adjust:
  - PST (UTC-8): 7:10 AM PST = 15:10 UTC
  - PDT (UTC-7): 7:10 AM PDT = 14:10 UTC

Check your system timezone:
```bash
timedatectl
```

## Dynamic Date Generation

The cron jobs automatically generate today's date using:
```bash
$(date +%Y-%m-%d)
```

This means:
- On October 15, 2025, it runs with date "2025-10-15"
- On October 16, 2025, it runs with date "2025-10-16"
- And so on...

No manual date updates needed!

## Troubleshooting

### Cron Job Not Running

1. Check cron service is running:
   ```bash
   systemctl status cron
   ```

2. Check system logs:
   ```bash
   grep CRON /var/log/syslog
   ```

3. Verify script permissions:
   ```bash
   ls -la /home/frank/ml/VibeVoice/run_podcast_pipeline.sh
   ```
   Should show: `-rwxr-xr-x` (executable)

### Script Fails in Cron

If the script works manually but fails in cron:

1. Check the log files in `/home/frank/ml/VibeVoice/logs/`
2. Ensure all paths are absolute (not relative)
3. Verify environment variables are set (cron has minimal environment)

### Python Virtual Environment Issues

The script automatically activates the virtual environment:
```bash
source /home/frank/ml/bin/activate
```

Verify this path exists:
```bash
ls -la /home/frank/ml/bin/activate
```

## Modifying the Schedule

To change the schedule, edit and re-run the setup script:

```bash
nano /home/frank/ml/VibeVoice/setup_cron.sh
# Modify the cron times
./setup_cron.sh
```

Or manually edit crontab:
```bash
crontab -e
```

## Removing Cron Jobs

To remove the podcast pipeline cron jobs:

```bash
crontab -l | grep -v "run_podcast_pipeline.sh" | crontab -
```

Or remove all cron jobs:
```bash
crontab -r
```

## Configuration

API Key and Model Path are configured in:
- `setup_cron.sh` - for cron job installation
- `test_cron_command.sh` - for manual testing

Update these files if you need to change:
- API key
- Model path
- Script path
- Log directory

## Files

- `setup_cron.sh` - Installs the cron jobs
- `run_podcast_pipeline.sh` - Main pipeline script
- `test_cron_command.sh` - Manual testing script
- `logs/` - Directory for cron output logs

## Support

If you encounter issues:
1. Check the log files first
2. Run `test_cron_command.sh` to verify the command works
3. Verify all file paths and permissions
4. Check system timezone settings

