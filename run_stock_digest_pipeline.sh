#!/bin/bash

# Stock Digest Pipeline Script
# Runs three commands in sequence to download, process, and upload stock digest

# Activate Python virtual environment
echo "Activating Python virtual environment..."
source /home/frank/ml/bin/activate

# Check if required arguments are provided
if [ $# -lt 4 ]; then
    echo "Usage: $0 <ticker> <date> <api_key> <model_path>"
    echo "Example: $0 AAPL 2025-01-15 your_api_key /path/to/model"
    exit 1
fi

TICKER=$1
DATE=$2
API_KEY=$3
MODEL_PATH=$4

echo "Starting stock digest pipeline..."
echo "Ticker: $TICKER"
echo "Date: $DATE"
echo "Model Path: $MODEL_PATH"
echo ""

# Step 1: Download stock digest script
echo "Step 1: Downloading stock digest script..."
NODE_OUTPUT=$(node ~/captital-sound/capital-sound/CapitalSoundApp/downloadStockDigestScript.js -t "$TICKER" -d "$DATE" -k "$API_KEY")
echo "Node script output: $NODE_OUTPUT"

# Extract filename from node output (look for "Script saved to: " pattern)
FILENAME=$(echo "$NODE_OUTPUT" | grep "Script saved to:" | awk -F': ' '{print $2}' | tr -d ' ')

# If not found, try alternative patterns (check for default format: stock_digests/{ticker}_MM_DD_YY.txt)
if [ -z "$FILENAME" ]; then
    # Try to extract from output or construct default path
    FILENAME=$(echo "$NODE_OUTPUT" | grep -oP 'stock_digests/[^[:space:]]+\.txt' | head -1)
fi

# If still not found, construct default filename based on date and ticker
if [ -z "$FILENAME" ]; then
    DATE_FORMATTED=$(echo "$DATE" | sed 's/-/_/g' | sed 's/\([0-9]\{4\}\)_\([0-9]\{2\}\)_\([0-9]\{2\}\)/\2_\3_\1/' | sed 's/^20//')
    FILENAME="stock_digests/${TICKER}_${DATE_FORMATTED}.txt"
    echo "Using default filename: $FILENAME"
else
    echo "Extracted filename: $FILENAME"
fi

# Step 2: Run Python inference
echo ""
echo "Step 2: Running Python inference..."
PYTHON_OUTPUT=$(python demo/inference_simple_captions.py --model_path "$MODEL_PATH" --txt_path "$FILENAME" --speaker_names Alice Frank --device cuda --generate_captions --caption_formats srt)
echo "Python script output: $PYTHON_OUTPUT"

# Check if PYTHON_FILENAME is empty or none
if [ -z "$PYTHON_OUTPUT" ] || [ "$PYTHON_OUTPUT" = "none" ]; then
    echo "❌ Error: Python script produced no output. Exiting."
    exit 1
fi

# Extract output filename from python output (look for "Saved audio to:" pattern)
PYTHON_FILENAME=$(echo "$PYTHON_OUTPUT" | grep "Saved audio to:" | sed 's/.*Saved audio to: //' | sed 's|^\./||' | sed 's/\[//g' | sed 's/\]//g' | sed "s/'//g" | tr -d ' ')
echo "Extracted Python output filename: $PYTHON_FILENAME"

# Check if PYTHON_FILENAME is empty or none
if [ -z "$PYTHON_FILENAME" ] || [ "$PYTHON_FILENAME" = "none" ]; then
    echo "❌ Error: Could not extract Python output filename. Exiting."
    exit 1
fi

# Extract ID from PYTHON_FILENAME (part before "_generated" and after last "_")
FILENAME_BASE=$(basename "$PYTHON_FILENAME")
ID=$(echo "$FILENAME_BASE" | sed 's/_generated.*//' | sed 's/.*_//')
echo "Extracted ID: $ID"

# Step 3: Upload stock digest audio
echo ""
echo "Step 3: Uploading stock digest audio..."
echo "Uploading file: $PYTHON_FILENAME"

# Check if file exists
if [ ! -f "$PYTHON_FILENAME" ]; then
    echo "❌ Error: File not found: $PYTHON_FILENAME"
    echo "Current directory: $(pwd)"
    echo "Files in current directory:"
    ls -la
    exit 1
fi

node ~/captital-sound/capital-sound/CapitalSoundApp/uploadPodcastAudio.js -f "$PYTHON_FILENAME" -d "$ID" -k "$API_KEY" -m '{"duration": 900}'

# Step 4: Upload SRT caption file
echo ""
echo "Step 4: Uploading SRT caption file..."

# Extract the base filename without extension and path
AUDIO_BASENAME=$(basename "$PYTHON_FILENAME" .wav)
SRT_FILENAME="outputs/captions/${AUDIO_BASENAME}.srt"

# Check if SRT file exists
if [ -f "$SRT_FILENAME" ]; then
    echo "Uploading SRT file: $SRT_FILENAME"
    node ~/captital-sound/capital-sound/CapitalSoundApp/uploadTranscription.js -f "$SRT_FILENAME" -d "$ID" -k "$API_KEY"
    echo "✅ SRT caption file uploaded successfully!"
else
    echo "⚠️  Warning: SRT caption file not found: $SRT_FILENAME"
    echo "Available files in captions directory:"
    ls -la outputs/captions/ 2>/dev/null || echo "Captions directory not found"
fi

echo ""
echo "Pipeline completed!"

