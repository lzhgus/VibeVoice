#!/bin/bash

# Podcast Pipeline Script
# Runs three commands in sequence to download, process, and upload podcast

# Activate Python virtual environment
echo "Activating Python virtual environment..."
source /home/frank/ml/bin/activate

# Check if required arguments are provided
if [ $# -lt 4 ]; then
    echo "Usage: $0 <date> <time> <api_key> <model_path>"
    echo "Example: $0 2025-01-15 morning your_api_key /path/to/model"
    exit 1
fi

DATE=$1
TIME=$2
API_KEY=$3
MODEL_PATH=$4

echo "Starting podcast pipeline..."
echo "Date: $DATE"
echo "Time: $TIME"
echo "Model Path: $MODEL_PATH"
echo ""

# Step 1: Download podcast script
echo "Step 1: Downloading podcast script..."
NODE_OUTPUT=$(node ~/captital-sound/capital-sound/CapitalSoundApp/downloadPodcastScript.js -d "$DATE" -t "$TIME" -k "$API_KEY")
echo "Node script output: $NODE_OUTPUT"

# Extract filename from node output (look for "Script saved to: " pattern)
FILENAME=$(echo "$NODE_OUTPUT" | grep "Script saved to:" | awk -F': ' '{print $2}' | tr -d ' ')
echo "Extracted filename: $FILENAME"

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

# Step 3: Upload podcast audio
echo ""
echo "Step 3: Uploading podcast audio..."
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
