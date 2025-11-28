#!/bin/bash

# Stock Digest Pipeline Script
# Runs three commands in sequence to download, process, and upload stock digest

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

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

# Extract ID from node output (look for "ID: " pattern)
DIGEST_ID=$(echo "$NODE_OUTPUT" | grep "ID:" | awk -F': ' '{print $2}' | tr -d ' ')
if [ -n "$DIGEST_ID" ]; then
    echo "Extracted Digest ID: $DIGEST_ID"
else
    echo "⚠️  Warning: Could not extract Digest ID from node output"
fi

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
PYTHON_OUTPUT=$(python demo/batch_inference_simple_captions.py --model_path "$MODEL_PATH" --txt_path "$FILENAME" --speaker_names Alice --device cuda --generate_captions --caption_formats srt)
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

# Use Digest ID from node output if available, otherwise extract from filename
if [ -n "$DIGEST_ID" ]; then
    ID="$DIGEST_ID"
    echo "Using Digest ID from node output: $ID"
else
    # Extract ID from PYTHON_FILENAME (part before "_generated" and after last "_")
    FILENAME_BASE=$(basename "$PYTHON_FILENAME")
    ID=$(echo "$FILENAME_BASE" | sed 's/_generated.*//' | sed 's/.*_//')
    echo "Extracted ID from filename: $ID"
fi

# Validate ID is not empty
if [ -z "$ID" ]; then
    echo "❌ Error: Could not determine ID for upload. Exiting."
    exit 1
fi

# Step 2.5: Convert WAV to MP3 to reduce file size
echo ""
echo "Step 2.5: Converting WAV to MP3..."

# Check if file exists
if [ ! -f "$PYTHON_FILENAME" ]; then
    echo "❌ Error: File not found: $PYTHON_FILENAME"
    echo "Current directory: $(pwd)"
    echo "Files in current directory:"
    ls -la
    exit 1
fi

# Check if ffmpeg is available
if command -v ffmpeg &> /dev/null; then
    # Convert WAV to MP3
    MP3_FILENAME="${PYTHON_FILENAME%.wav}.mp3"
    echo "Converting $PYTHON_FILENAME to $MP3_FILENAME..."
    
    # Get original file size
    WAV_SIZE=$(stat -f%z "$PYTHON_FILENAME" 2>/dev/null || stat -c%s "$PYTHON_FILENAME" 2>/dev/null || echo "0")
    WAV_SIZE_MB=$(echo "scale=2; $WAV_SIZE / 1024 / 1024" | bc 2>/dev/null || echo "0")
    echo "Original WAV file size: ${WAV_SIZE_MB} MB"
    
    # Convert to MP3 with good quality (192kbps)
    if ffmpeg -i "$PYTHON_FILENAME" -codec:a libmp3lame -b:a 192k -y "$MP3_FILENAME" 2>/dev/null; then
        # Get MP3 file size
        MP3_SIZE=$(stat -f%z "$MP3_FILENAME" 2>/dev/null || stat -c%s "$MP3_FILENAME" 2>/dev/null || echo "0")
        MP3_SIZE_MB=$(echo "scale=2; $MP3_SIZE / 1024 / 1024" | bc 2>/dev/null || echo "0")
        REDUCTION=$(echo "scale=1; (1 - $MP3_SIZE / $WAV_SIZE) * 100" | bc 2>/dev/null || echo "0")
        echo "✅ Converted to MP3: ${MP3_SIZE_MB} MB (${REDUCTION}% reduction)"
        
        # Use MP3 file for upload
        UPLOAD_FILENAME="$MP3_FILENAME"
    else
        echo "⚠️  Warning: MP3 conversion failed, using original WAV file"
        UPLOAD_FILENAME="$PYTHON_FILENAME"
    fi
else
    echo "⚠️  Warning: ffmpeg not found. Install ffmpeg to convert WAV to MP3 and reduce file size."
    echo "   Install with: sudo apt-get install ffmpeg (Ubuntu/Debian) or brew install ffmpeg (macOS)"
    UPLOAD_FILENAME="$PYTHON_FILENAME"
fi

# Step 3: Upload stock digest audio
echo ""
echo "Step 3: Uploading stock digest audio..."
echo "Uploading file: $UPLOAD_FILENAME"

# Check if upload file exists
if [ ! -f "$UPLOAD_FILENAME" ]; then
    echo "❌ Error: File not found: $UPLOAD_FILENAME"
    echo "Current directory: $(pwd)"
    echo "Files in current directory:"
    ls -la
    exit 1
fi

node ~/captital-sound/capital-sound/CapitalSoundApp/uploadPodcastAudio.js -f "$UPLOAD_FILENAME" -d "$ID" -k "$API_KEY" -s "stock_summaries"

# Step 4: Upload SRT caption file
echo ""
echo "Step 4: Uploading SRT caption file..."

# Extract the base filename without extension and path (use original WAV filename for SRT)
AUDIO_BASENAME=$(basename "$PYTHON_FILENAME" .wav)
SRT_FILENAME="outputs/captions/${AUDIO_BASENAME}.srt"

# Check if SRT file exists
if [ -f "$SRT_FILENAME" ]; then
    echo "Uploading SRT file: $SRT_FILENAME"
    node ~/captital-sound/capital-sound/CapitalSoundApp/uploadTranscription.js -f "$SRT_FILENAME" -d "$ID" -k "$API_KEY" -s "stock_summaries"
    echo "✅ SRT caption file uploaded successfully!"
else
    echo "⚠️  Warning: SRT caption file not found: $SRT_FILENAME"
    echo "Available files in captions directory:"
    ls -la outputs/captions/ 2>/dev/null || echo "Captions directory not found"
fi

echo ""
echo "Pipeline completed!"

