#!/bin/bash

# Stock Digest Pipeline Script (Batch Version)
# Downloads, processes, and uploads multiple stock digests for a given date
# Supports processing all digests or specific tickers

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Activate Python virtual environment
echo "Activating Python virtual environment..."
source /home/frank/ml/bin/activate

# Check if required arguments are provided
if [ $# -lt 3 ]; then
    echo "Usage: $0 <date> <api_key> <model_path> [tickers]"
    echo "  date: Date to process (YYYY-MM-DD)"
    echo "  api_key: Supabase API key"
    echo "  model_path: Path to VibeVoice model"
    echo "  tickers: (optional) Comma-separated list of tickers (e.g., AAPL,MSFT,GOOGL)"
    echo "          If not provided, processes all digests for the date"
    echo ""
    echo "Examples:"
    echo "  $0 2025-01-15 your_api_key /path/to/model"
    echo "  $0 2025-01-15 your_api_key /path/to/model AAPL,MSFT"
    exit 1
fi

DATE=$1
API_KEY=$2
MODEL_PATH=$3
TICKERS=$4  # Optional: comma-separated tickers

echo "=========================================="
echo "Stock Digest Batch Pipeline"
echo "=========================================="
echo "Date: $DATE"
echo "Model Path: $MODEL_PATH"
if [ -n "$TICKERS" ]; then
    echo "Tickers: $TICKERS"
else
    echo "Tickers: All available"
fi
echo "=========================================="
echo ""

# Step 1: Download stock digest scripts
echo "Step 1: Downloading stock digest scripts..."
if [ -n "$TICKERS" ]; then
    NODE_OUTPUT=$(node ~/captital-sound/capital-sound/CapitalSoundApp/batchDownloadStockDigests.js -d "$DATE" -t "$TICKERS" -k "$API_KEY")
else
    NODE_OUTPUT=$(node ~/captital-sound/capital-sound/CapitalSoundApp/batchDownloadStockDigests.js -d "$DATE" -k "$API_KEY")
fi

# Save full output for debugging
echo "$NODE_OUTPUT"

# Extract all downloaded filenames - FILTER BY DATE FIRST
# The batch script outputs: "   ✅ TICKER - size KB" for each successful download
# Files are saved to stock_digests/ directory with format: TICKER_MM_DD_YY_ID.txt

# Convert date from YYYY-MM-DD to MM_DD_YY format for filename matching
# Example: 2025-11-28 -> 11_28_25
DATE_FORMATTED=$(echo "$DATE" | awk -F'-' '{printf "%02d_%02d_%s", $2, $3, substr($1,3,2)}')

echo "Filtering files for date: $DATE (pattern: *_${DATE_FORMATTED}*.txt)"
echo ""

# Method 1: Try to extract from node output, but filter by date pattern
FILENAMES=$(echo "$NODE_OUTPUT" | grep -E "✅|stock_digests/" | grep -oE "stock_digests/[^[:space:]]+\.txt" | grep "_${DATE_FORMATTED}" | sort -u)

# Method 2: Find files by date pattern in stock_digests directory (PRIMARY METHOD)
if [ -z "$FILENAMES" ]; then
    FILENAMES=$(find stock_digests -name "*_${DATE_FORMATTED}*.txt" -type f 2>/dev/null | sort)
fi

# Method 3: If still no files, show warning and exit (don't process all files)
if [ -z "$FILENAMES" ]; then
    echo "⚠️  Warning: No files found with date pattern *_${DATE_FORMATTED}*.txt"
    echo "   Checking what files exist in stock_digests/ for debugging:"
    find stock_digests -name "*.txt" -type f 2>/dev/null | head -5 | while read -r file; do
        echo "   - $file"
    done
    echo ""
    echo "❌ Error: No stock digest files found for date $DATE"
    echo "   Expected pattern: *_${DATE_FORMATTED}*.txt"
    exit 1
fi

# Count files properly (handle empty case)
if [ -z "$FILENAMES" ]; then
    FILE_COUNT=0
else
    FILE_COUNT=$(echo "$FILENAMES" | wc -l | tr -d ' ')
    # If wc returns 0 but FILENAMES is not empty, it's a single file
    if [ "$FILE_COUNT" -eq 0 ] && [ -n "$FILENAMES" ]; then
        FILE_COUNT=1
    fi
fi

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "❌ Error: No stock digest files found for date $DATE"
    echo "   Check the batch download output above for errors"
    exit 1
fi

echo ""
echo "Found $FILE_COUNT stock digest file(s) to process:"
echo "$FILENAMES" | while read -r file; do
    echo "  - $file"
done
echo ""

# Step 2: Process stock digests in PARALLEL for better GPU utilization
echo "Step 2: Processing stock digests in parallel (batch mode)..."
echo ""

SUCCESS_COUNT=0
FAILED_COUNT=0
FAILED_FILES=()

# Convert newline-separated list to array
mapfile -t FILE_ARRAY < <(echo "$FILENAMES" | grep -v '^$')

# Step 2.1: Run batch inference on all files in parallel
echo "Step 2.1: Running batch inference (processing ${#FILE_ARRAY[@]} files in parallel)..."
echo "   Note: For better GPU utilization, process more files at once (batch_size=8-16 recommended)"
echo ""

# Run batch inference with all files at once (this processes them in parallel)
# Use tee to show progress in real-time while capturing output
echo "Running batch inference (progress bars will be shown below)..."
echo ""

# Create temporary file for output
TEMP_OUTPUT="/tmp/batch_inference_output_$$"

# Run with unbuffered Python output to show progress bars in real-time
# Pass files as array elements directly to avoid expansion issues
PYTHONUNBUFFERED=1 python demo/batch_inference_simple_captions.py \
    --model_path "$MODEL_PATH" \
    --txt_files "${FILE_ARRAY[@]}" \
    --speaker_names Alice \
    --device cuda \
    --batch_size 16 \
    --generate_captions \
    --caption_formats srt \
    2>&1 | tee "$TEMP_OUTPUT"
PYTHON_EXIT_CODE=${PIPESTATUS[0]}

# Read output from temp file
PYTHON_OUTPUT=$(cat "$TEMP_OUTPUT")
rm -f "$TEMP_OUTPUT"

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    echo "❌ Error: Batch inference failed"
    echo "Output: $PYTHON_OUTPUT"
    exit 1
fi

# Extract all output filenames from python output
# The batch script outputs "Saved audio to: <filename>" for each file (one per line)
mapfile -t OUTPUT_FILES_ARRAY < <(echo "$PYTHON_OUTPUT" | grep "Saved audio to:" | sed 's/.*Saved audio to: //' | sed 's|^\./||' | sed 's/\[//g' | sed 's/\]//g' | sed "s/'//g" | tr -d ' ' | grep -v '^$')

if [ ${#OUTPUT_FILES_ARRAY[@]} -eq 0 ]; then
    echo "❌ Error: No output files generated from batch inference"
    echo "Python output:"
    echo "$PYTHON_OUTPUT" | tail -20
    exit 1
fi

echo "✅ Batch inference completed. Generated ${#OUTPUT_FILES_ARRAY[@]} audio file(s):"
for output_file in "${OUTPUT_FILES_ARRAY[@]}"; do
    echo "  - $output_file"
done
echo ""

# Step 2.2: Process each file for upload (convert, upload audio, upload captions)
echo "Step 2.2: Processing uploads for each file..."
echo ""

# Process each file
for FILENAME in "${FILE_ARRAY[@]}"; do
    if [ -z "$FILENAME" ] || [ ! -f "$FILENAME" ]; then
        echo "⚠️  Skipping: File not found - $FILENAME"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_FILES+=("$FILENAME")
        continue
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Processing: $FILENAME"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Extract ticker and full digest ID from filename
    # Format: stock_digests/TICKER_MM_DD_YY_FULLID.txt (full ID is complete UUID)
    # Example: DOCU_11_28_25_5711e948-e79d-414a-9ee3-b260953b2a17.txt
    FILENAME_BASE=$(basename "$FILENAME" .txt)
    TICKER=$(echo "$FILENAME_BASE" | cut -d'_' -f1)
    
    # Extract full UUID from filename (format: TICKER_MM_DD_YY_UUID)
    # Try to match full UUID pattern first (new format with full ID)
    ID=$(echo "$FILENAME_BASE" | grep -oE '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)
    
    # If no full UUID found, try to extract 8-char short ID (for backward compatibility with old files)
    # Old format: TICKER_MM_DD_YY_SHORTID.txt (e.g., DOCU_11_28_25_5711e948.txt)
    if [ -z "$ID" ]; then
        SHORT_ID=$(echo "$FILENAME_BASE" | grep -oE '[a-f0-9]{8}$' | head -1)
        if [ -n "$SHORT_ID" ]; then
            ID="$SHORT_ID"
            echo "  ⚠️  Warning: Only short ID (8 chars) found: $SHORT_ID"
            echo "  ⚠️  This file may have been created with old batch download script."
            echo "  ⚠️  New files should include full UUID in filename."
        fi
    fi
    
    if [ -z "$ID" ]; then
        echo "  ❌ Error: Could not extract digest ID from filename: $FILENAME"
        echo "  Filename format should be: TICKER_MM_DD_YY_ID.txt"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_FILES+=("$FILENAME")
        continue
    fi
    
    echo "  Ticker: $TICKER"
    echo "  Digest ID: $ID"
    
    # Find the corresponding output file for this input file
    # Extract base name from input filename to match output
    FILENAME_BASE=$(basename "$FILENAME" .txt)
    PYTHON_FILENAME=""
    
    # Try to match by filename base (without extension)
    for output_file in "${OUTPUT_FILES_ARRAY[@]}"; do
        OUTPUT_BASE=$(basename "$output_file" .wav | sed 's/_generated$//')
        if [ "$OUTPUT_BASE" = "$FILENAME_BASE" ]; then
            PYTHON_FILENAME="$output_file"
            break
        fi
    done
    
    # If not found, try matching by ID
    if [ -z "$PYTHON_FILENAME" ] && [ -n "$ID" ]; then
        for output_file in "${OUTPUT_FILES_ARRAY[@]}"; do
            if echo "$output_file" | grep -q "$ID"; then
                PYTHON_FILENAME="$output_file"
                break
            fi
        done
    fi
    
    # If still not found, try matching by ticker and date
    if [ -z "$PYTHON_FILENAME" ]; then
        TICKER_DATE_PATTERN="${TICKER}_${DATE_FORMATTED}"
        for output_file in "${OUTPUT_FILES_ARRAY[@]}"; do
            if echo "$output_file" | grep -q "$TICKER_DATE_PATTERN"; then
                PYTHON_FILENAME="$output_file"
                break
            fi
        done
    fi
    
    if [ -z "$PYTHON_FILENAME" ]; then
        echo "  ❌ Error: Could not find output file for $FILENAME"
        echo "  Available output files:"
        for output_file in "${OUTPUT_FILES_ARRAY[@]}"; do
            echo "    - $output_file"
        done
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_FILES+=("$FILENAME")
        continue
    fi
    
    echo "  ✅ Found generated audio: $PYTHON_FILENAME"
    
    # Step 2.3: Convert WAV to MP3
    echo ""
    echo "  Step 2.3: Converting WAV to MP3..."
    
    if [ ! -f "$PYTHON_FILENAME" ]; then
        echo "  ❌ Error: Audio file not found: $PYTHON_FILENAME"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_FILES+=("$FILENAME")
        continue
    fi
    
    if command -v ffmpeg &> /dev/null; then
        MP3_FILENAME="${PYTHON_FILENAME%.wav}.mp3"
        if ffmpeg -i "$PYTHON_FILENAME" -codec:a libmp3lame -b:a 192k -y "$MP3_FILENAME" 2>/dev/null; then
            UPLOAD_FILENAME="$MP3_FILENAME"
            echo "  ✅ Converted to MP3: $MP3_FILENAME"
        else
            UPLOAD_FILENAME="$PYTHON_FILENAME"
            echo "  ⚠️  MP3 conversion failed, using WAV"
        fi
    else
        UPLOAD_FILENAME="$PYTHON_FILENAME"
        echo "  ⚠️  ffmpeg not found, using WAV"
    fi
    
    # Step 2.4: Upload audio
    echo ""
    echo "  Step 2.4: Uploading audio..."
    if node ~/captital-sound/capital-sound/CapitalSoundApp/uploadPodcastAudio.js -f "$UPLOAD_FILENAME" -d "$ID" -k "$API_KEY" -s "stock_summaries" 2>&1; then
        echo "  ✅ Audio uploaded successfully"
    else
        echo "  ❌ Error: Audio upload failed"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_FILES+=("$FILENAME")
        continue
    fi
    
    # Step 2.5: Upload SRT caption
    echo ""
    echo "  Step 2.5: Uploading SRT caption..."
    AUDIO_BASENAME=$(basename "$PYTHON_FILENAME" .wav)
    SRT_FILENAME="outputs/captions/${AUDIO_BASENAME}.srt"
    
    if [ -f "$SRT_FILENAME" ]; then
        if node ~/captital-sound/capital-sound/CapitalSoundApp/uploadTranscription.js -f "$SRT_FILENAME" -d "$ID" -k "$API_KEY" -s "stock_summaries" 2>&1; then
            echo "  ✅ SRT caption uploaded successfully"
        else
            echo "  ⚠️  Warning: SRT upload failed (continuing anyway)"
        fi
    else
        echo "  ⚠️  Warning: SRT file not found: $SRT_FILENAME"
    fi
    
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    echo "  ✅ Completed: $FILENAME"
    echo ""
done

# Final summary
echo ""
echo "=========================================="
echo "Pipeline Summary"
echo "=========================================="
echo "Total files processed: $FILE_COUNT"
echo "✅ Successful: $SUCCESS_COUNT"
echo "❌ Failed: $FAILED_COUNT"

if [ $FAILED_COUNT -gt 0 ] && [ ${#FAILED_FILES[@]} -gt 0 ]; then
    echo ""
    echo "Failed files:"
    for file in "${FAILED_FILES[@]}"; do
        echo "  - $file"
    done
fi

echo "=========================================="
echo "Pipeline completed!"

