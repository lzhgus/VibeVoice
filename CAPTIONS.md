# VibeVoice Caption Generation

This document provides comprehensive information about the caption generation features in VibeVoice, including both simple script-based captions and advanced speech-to-text transcription.

## 🎯 Overview

VibeVoice offers two approaches to caption generation:

1. **Simple Script-Based Captions** (Recommended) - Fast, accurate, no external dependencies
2. **Advanced Speech-to-Text Captions** - Uses OpenAI Whisper for transcription

## 🚀 Quick Start

### Simple Script-Based Captions (Recommended)

```bash
python demo/inference_simple_captions.py \
    --model_path microsoft/VibeVoice-1.5B \
    --txt_path demo/text_examples/2p_music.txt \
    --speaker_names Alice Frank \
    --generate_captions \
    --caption_formats srt vtt transcript
```

### Advanced Speech-to-Text Captions

```bash
# Install dependencies
pip install -r requirements_captions.txt

# Generate with Whisper transcription
python demo/inference_with_captions.py \
    --model_path microsoft/VibeVoice-1.5B \
    --txt_path demo/text_examples/2p_music.txt \
    --speaker_names Alice Frank \
    --caption_model base \
    --caption_formats srt vtt json transcript
```

## 📋 Features

### Simple Script-Based Captions

- ✅ **No External Dependencies**: No Whisper or speech-to-text required
- ✅ **Fast Generation**: Instant caption creation from script text
- ✅ **Perfect Accuracy**: Uses original script text (no transcription errors)
- ✅ **Customizable Timing**: Adjustable words-per-minute for different speaking rates
- ✅ **Multiple Formats**: SRT, VTT, JSON, transcript, and script-with-timing formats
- ✅ **Speaker Identification**: Automatic speaker matching from script
- ✅ **Word Limit Control**: Segments limited to ≤15 words for better readability

### Advanced Speech-to-Text Captions

- ✅ **Automatic Transcription**: Uses OpenAI Whisper for speech-to-text
- ✅ **Speaker Identification**: Matches speakers to original script
- ✅ **Multiple Formats**: SRT, VTT, JSON, and transcript formats
- ✅ **Enhanced Demo Interface**: Gradio interface with caption controls
- ✅ **Batch Processing**: Generate captions for multiple audio files

## 🛠️ Installation

### For Simple Captions (No Additional Dependencies)

Simple captions work with the existing VibeVoice installation. No additional packages required.

### For Advanced Captions

```bash
pip install -r requirements_captions.txt
```

Required packages:
- `openai-whisper`
- `ffmpeg-python`
- `librosa`
- `soundfile`

## 📖 Usage Examples

### 1. Basic Caption Generation

```python
from vibevoice.caption.simple_caption_generator import SimpleCaptionGenerator
from vibevoice.caption.simple_caption_formatter import SimpleCaptionFormatter

# Initialize generator
generator = SimpleCaptionGenerator(
    words_per_minute=150,
    min_segment_duration=1.0,
    max_segment_duration=60.0
)

# Generate captions from script
script = """
Speaker 1: Hello, welcome to our podcast.
Speaker 2: Thank you for having me.
"""

captions = generator.generate_captions_from_script(
    script=script,
    audio_duration=120.0,  # 2 minutes
    speaker_mapping={1: 'Alice', 2: 'Frank'}
)

# Format as SRT
formatter = SimpleCaptionFormatter()
srt_content = formatter.format_srt(captions, "output.srt")
```

### 2. Advanced Caption Generation with Whisper

```python
from vibevoice.caption.caption_generator import CaptionGenerator
from vibevoice.caption.caption_formatter import CaptionFormatter

# Initialize generator with Whisper
generator = CaptionGenerator(
    model_name="base",
    device="cuda" if torch.cuda.is_available() else "cpu"
)

# Generate captions from audio
captions = generator.generate_captions_from_audio(
    audio_path="output.wav",
    script_path="script.txt",
    speaker_mapping={1: 'Alice', 2: 'Frank'}
)

# Format in multiple formats
formatter = CaptionFormatter()
formatter.format_all(captions, "output", formats=['srt', 'vtt', 'json'])
```

### 3. Command Line Usage

#### Simple Captions
```bash
python generate_captions_for_existing_audio.py \
    --audio_path "output.wav" \
    --script_path "script.txt" \
    --speaker_names Alice Frank \
    --output_dir "./captions"
```

#### Advanced Captions
```bash
python demo/inference_with_captions.py \
    --model_path microsoft/VibeVoice-1.5B \
    --txt_path script.txt \
    --speaker_names Alice Frank \
    --caption_model base \
    --caption_formats srt vtt json transcript
```

## 📁 Output Formats

### SRT (SubRip)
```
1
00:00:00,000 --> 00:00:07,150
[Alice] Good evening, everyone, and welcome to Capital Sound!

2
00:00:07,450 --> 00:00:14,012
[Alice] I'm Mandy Prince, and tonight we're diving into what's been a pivotal day.
```

### VTT (WebVTT)
```
WEBVTT

00:00:00.000 --> 00:00:07.150
[Alice] Good evening, everyone, and welcome to Capital Sound!

00:00:07.450 --> 00:00:14.012
[Alice] I'm Mandy Prince, and tonight we're diving into what's been a pivotal day.
```

### JSON
```json
{
  "captions": [
    {
      "start_time": 0.0,
      "end_time": 7.15,
      "text": "Good evening, everyone, and welcome to Capital Sound!",
      "speaker_name": "Alice",
      "speaker_id": 1,
      "confidence": 1.0
    }
  ]
}
```

### Transcript
```
[00:00:00] Alice: Good evening, everyone, and welcome to Capital Sound!
[00:00:07] Alice: I'm Mandy Prince, and tonight we're diving into what's been a pivotal day.
```

## ⚙️ Configuration

### Simple Caption Generator Options

```python
generator = SimpleCaptionGenerator(
    words_per_minute=150,           # Speaking rate
    min_segment_duration=1.0,       # Minimum segment duration (seconds)
    max_segment_duration=60.0,      # Maximum segment duration (seconds)
    pause_between_speakers=0.5,     # Pause when speaker changes
    pause_between_segments=0.3      # Pause between segments
)
```

### Advanced Caption Generator Options

```python
generator = CaptionGenerator(
    model_name="base",              # Whisper model size
    device="cuda",                 # Device for processing
    language="en",                 # Language for transcription
    temperature=0.0,               # Temperature for generation
    beam_size=5                    # Beam size for decoding
)
```

## 🎛️ Advanced Features

### Custom Timing Adjustments

The simple caption generator includes intelligent timing adjustments:

- **Punctuation Pauses**: Automatic pauses for commas, periods, questions
- **Sentence Length**: Longer sentences get more time
- **Technical Terms**: Numbers and technical content get extra time
- **Speaker Changes**: Different pause lengths for speaker transitions

### Batch Processing

```python
# Process multiple files
audio_files = ["file1.wav", "file2.wav", "file3.wav"]
script_files = ["script1.txt", "script2.txt", "script3.txt"]

for audio, script in zip(audio_files, script_files):
    captions = generator.generate_captions_from_script(
        script=open(script).read(),
        audio_duration=get_audio_duration(audio),
        speaker_mapping={1: 'Alice', 2: 'Frank'}
    )
    formatter.format_srt(captions, f"{audio}.srt")
```

### Integration with Podcast Pipeline

The caption generation is integrated into the automated podcast pipeline:

```bash
# The run_podcast_pipeline.sh script automatically:
# 1. Downloads podcast script
# 2. Generates audio with VibeVoice
# 3. Creates captions from script
# 4. Uploads both audio and captions
```

## 🔧 Troubleshooting

### Common Issues

1. **Timing Mismatch**: Adjust `words_per_minute` parameter
2. **Speaker Mapping**: Ensure speaker names match script format
3. **File Not Found**: Check file paths and permissions
4. **Memory Issues**: Use smaller Whisper models for large files

### Debug Mode

```python
# Enable debug output
generator = SimpleCaptionGenerator()
generator.debug = True
```

### Performance Tips

- Use simple captions for better performance
- Adjust `max_segment_duration` for longer content
- Use GPU for Whisper processing when available
- Process files in batches for large datasets

## 📊 Performance Comparison

| Feature | Simple Captions | Advanced Captions |
|---------|----------------|-------------------|
| Speed | ⚡ Instant | 🐌 2-5x audio duration |
| Accuracy | ✅ Perfect (script-based) | ⚠️ ~95% (transcription) |
| Dependencies | ✅ None | ❌ Whisper + FFmpeg |
| Speaker ID | ✅ Perfect | ⚠️ ~90% accuracy |
| File Size | ✅ Small | ❌ Large (model files) |

## 🎯 Best Practices

1. **Use Simple Captions** when you have the original script
2. **Use Advanced Captions** only when script is unavailable
3. **Test timing** with a small sample first
4. **Adjust parameters** based on speaking rate and content
5. **Validate output** before production use

## 📚 API Reference

### SimpleCaptionGenerator

```python
class SimpleCaptionGenerator:
    def __init__(self, words_per_minute=150, min_segment_duration=1.0, 
                 max_segment_duration=60.0, pause_between_speakers=0.5, 
                 pause_between_segments=0.3):
        pass
    
    def generate_captions_from_script(self, script, audio_duration, 
                                     speaker_mapping=None):
        pass
```

### SimpleCaptionFormatter

```python
class SimpleCaptionFormatter:
    def format_srt(self, caption_segments, output_path=None):
        pass
    
    def format_vtt(self, caption_segments, output_path=None):
        pass
    
    def format_json(self, caption_segments, output_path=None):
        pass
    
    def format_transcript(self, caption_segments, output_path=None):
        pass
```

## 🤝 Contributing

To contribute to caption generation:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
