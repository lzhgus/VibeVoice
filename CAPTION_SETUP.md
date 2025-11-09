# VibeVoice Caption Generation Setup

This guide explains how to set up and use the caption generation functionality in VibeVoice.

## Overview

The caption generation feature automatically transcribes generated audio and creates captions in multiple formats (SRT, VTT, JSON, and transcript) for accessibility and content understanding.

## Installation

### 1. Install Caption Dependencies

```bash
pip install -r requirements_captions.txt
```

### 2. Verify Installation

```python
import whisper
print("Whisper installed successfully")
```

## Usage

### 1. Using the Enhanced Demo

Run the demo with caption support:

```bash
python demo/gradio_demo_with_captions.py --model_path microsoft/VibeVoice-1.5B --caption_model base
```

### 2. Using the Enhanced Processor

```python
from vibevoice.processor.vibevoice_processor_with_captions import VibeVoiceProcessorWithCaptions

# Initialize processor with caption support
processor = VibeVoiceProcessorWithCaptions.from_pretrained(
    "microsoft/VibeVoice-1.5B",
    caption_model="base",
    caption_language="en"
)

# Generate audio with captions
result = processor.save_audio_with_captions(
    audio=generated_audio,
    output_path="podcast.wav",
    original_script=script_text,
    speaker_mapping={0: "Alice", 1: "Bob"},
    generate_captions=True,
    caption_formats=["srt", "vtt", "json", "transcript"]
)

print(f"Audio saved to: {result['audio_paths']}")
print(f"Caption files: {result['caption_files']}")
```

### 3. Direct Caption Generation

```python
from vibevoice.caption.caption_generator import CaptionGenerator
from vibevoice.caption.caption_formatter import CaptionFormatter

# Initialize caption generator
generator = CaptionGenerator(model_name="base", language="en")

# Transcribe audio
result = generator.transcribe_audio("audio.wav", return_timestamps=True)

# Format captions
formatter = CaptionFormatter()
srt_content = formatter.format_srt(result['segments'])
```

## Caption Formats

### SRT (SubRip)
```
1
00:00:00,000 --> 00:00:03,000
[Alice] Welcome to our podcast today!

2
00:00:03,000 --> 00:00:06,000
[Bob] Thanks for having me. I'm excited to discuss...
```

### VTT (WebVTT)
```
WEBVTT

00:00:00.000 --> 00:00:03.000
<v Alice>Welcome to our podcast today!

00:00:03.000 --> 00:00:06.000
<v Bob>Thanks for having me. I'm excited to discuss...
```

### JSON
```json
{
  "format": "vibevoice_captions",
  "version": "1.0",
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 3.0,
      "text": "Welcome to our podcast today!",
      "speaker_id": 0,
      "speaker_name": "Alice",
      "confidence": 0.95
    }
  ]
}
```

### Transcript
```
[00:00] Alice: Welcome to our podcast today!
[00:03] Bob: Thanks for having me. I'm excited to discuss...
```

## Configuration Options

### Caption Model Sizes

- **tiny**: Fastest, least accurate (~39 MB)
- **base**: Good balance (~74 MB) - **Recommended**
- **small**: Better accuracy (~244 MB)
- **medium**: High accuracy (~769 MB)
- **large**: Best accuracy (~1550 MB)

### Supported Languages

The system auto-detects language, but you can specify:
- `"en"` - English
- `"zh"` - Chinese
- `"es"` - Spanish
- `"fr"` - French
- `"de"` - German
- And many more...

### Device Support

- **CPU**: Works on all systems
- **CUDA**: Faster on NVIDIA GPUs
- **MPS**: Apple Silicon Macs

## Integration with Existing Pipeline

### 1. Update run_podcast_pipeline.sh

```bash
# Add caption generation to your pipeline
python demo/inference_from_file.py \
    --model_path "$MODEL_PATH" \
    --txt "$FILENAME" \
    --speaker_names Alice Frank \
    --device cuda \
    --generate_captions \
    --caption_formats srt vtt transcript
```

### 2. Batch Processing

```python
# Process multiple files with captions
for script_file in script_files:
    result = processor.save_audio_with_captions(
        audio=generate_audio(script_file),
        output_path=f"outputs/{script_file.stem}.wav",
        original_script=script_file.read_text(),
        generate_captions=True
    )
```

## Troubleshooting

### Common Issues

1. **Whisper not installed**
   ```bash
   pip install openai-whisper
   ```

2. **CUDA out of memory**
   - Use smaller caption model (`tiny` or `base`)
   - Use CPU for caption generation: `caption_device="cpu"`

3. **Slow caption generation**
   - Use smaller model (`tiny` or `base`)
   - Use GPU if available
   - Process shorter audio segments

### Performance Tips

1. **For real-time generation**: Use `tiny` model
2. **For high accuracy**: Use `large` model
3. **For batch processing**: Use `base` model
4. **For production**: Consider using a dedicated transcription service

## API Reference

### CaptionGenerator

```python
generator = CaptionGenerator(
    model_name="base",      # Whisper model size
    device="cuda",          # Device for inference
    language="en"           # Language code
)

# Transcribe audio file
result = generator.transcribe_audio("audio.wav")

# Transcribe audio array
result = generator.transcribe_audio_array(audio_array, sample_rate=24000)

# Generate captions with speaker identification
result = generator.generate_captions_for_script(
    audio_path="audio.wav",
    original_script="Speaker 1: Hello\nSpeaker 2: Hi there",
    speaker_mapping={0: "Alice", 1: "Bob"}
)
```

### CaptionFormatter

```python
formatter = CaptionFormatter()

# Format as SRT
srt_content = formatter.format_srt(segments, "output.srt")

# Format as VTT
vtt_content = formatter.format_vtt(segments, "output.vtt")

# Format as JSON
json_content = formatter.format_json(segments, "output.json")

# Format as transcript
transcript = formatter.format_transcript(segments, "output.txt")

# Create complete caption package
files = formatter.create_caption_package(
    segments, "podcast", "captions/"
)
```

## Examples

See the `demo/` directory for complete examples of caption generation with VibeVoice.
