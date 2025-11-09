# VibeVoice with Caption Generation

This enhanced version of VibeVoice includes automatic caption generation for accessibility and content understanding.

## 🆕 New Features

- **Automatic Caption Generation**: Transcribes generated audio using OpenAI Whisper
- **Multiple Caption Formats**: SRT, VTT, JSON, and transcript formats
- **Speaker Identification**: Matches speakers to original script for accurate attribution
- **Enhanced Demo Interface**: Gradio interface with caption controls
- **Batch Processing**: Generate captions for multiple audio files

## 🚀 Quick Start

### 1. Install Caption Dependencies

```bash
pip install -r requirements_captions.txt
```

### 2. Run Enhanced Demo

```bash
python demo/gradio_demo_with_captions.py --model_path microsoft/VibeVoice-1.5B --caption_model base
```

### 3. Generate Audio with Captions

```bash
python demo/inference_with_captions.py \
    --model_path microsoft/VibeVoice-1.5B \
    --txt_path demo/text_examples/2p_music.txt \
    --speaker_names Alice Frank \
    --generate_captions \
    --caption_formats srt vtt transcript
```

## 📝 Caption Formats

### SRT (SubRip)
```
1
00:00:00,000 --> 00:00:03,000
[Alice] Welcome to our podcast today!

2
00:00:03,000 --> 00:00:06,000
[Frank] Thanks for having me. I'm excited to discuss...
```

### VTT (WebVTT)
```
WEBVTT

00:00:00.000 --> 00:00:03.000
<v Alice>Welcome to our podcast today!

00:00:03.000 --> 00:00:06.000
<v Frank>Thanks for having me. I'm excited to discuss...
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
[00:03] Frank: Thanks for having me. I'm excited to discuss...
```

## 🎛️ Configuration Options

### Caption Model Sizes
- **tiny**: Fastest, least accurate (~39 MB)
- **base**: Good balance (~74 MB) - **Recommended**
- **small**: Better accuracy (~244 MB)
- **medium**: High accuracy (~769 MB)
- **large**: Best accuracy (~1550 MB)

### Supported Languages
- Auto-detection (default)
- English (`en`)
- Chinese (`zh`)
- Spanish (`es`)
- French (`fr`)
- German (`de`)
- And many more...

## 🔧 API Usage

### Basic Caption Generation

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
```

### Direct Caption Generation

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

## 🎯 Use Cases

### Accessibility
- Generate captions for hearing-impaired users
- Create accessible podcast content
- Support multiple caption formats for different platforms

### Content Understanding
- Analyze generated content
- Extract key topics and speakers
- Create searchable transcripts

### Content Creation
- Generate subtitles for videos
- Create transcript files for documentation
- Batch process multiple audio files

## 🚀 Performance Tips

### For Real-time Generation
- Use `tiny` model for fastest processing
- Enable GPU acceleration if available
- Process shorter audio segments

### For High Accuracy
- Use `large` model for best results
- Specify language if known
- Use high-quality audio input

### For Batch Processing
- Use `base` model for good balance
- Process files in parallel
- Consider using dedicated transcription services for large volumes

## 🔍 Troubleshooting

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

### Performance Optimization

1. **Model Selection**
   - `tiny`: ~1x real-time speed, basic accuracy
   - `base`: ~0.5x real-time speed, good accuracy
   - `large`: ~0.1x real-time speed, excellent accuracy

2. **Device Selection**
   - CPU: Universal compatibility
   - CUDA: Fastest on NVIDIA GPUs
   - MPS: Apple Silicon Macs

## 📚 Examples

See the `demo/` directory for complete examples:
- `gradio_demo_with_captions.py`: Enhanced web interface
- `inference_with_captions.py`: Command-line interface
- `test_captions.py`: Functionality testing

## 🤝 Contributing

To contribute to the caption functionality:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This caption functionality follows the same license as VibeVoice. See the main LICENSE file for details.
