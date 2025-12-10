#!/usr/bin/env python3
"""
Generate captions for existing VibeVoice audio files

This script creates captions for audio files that were already generated,
using the simple caption system that doesn't require speech-to-text.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def generate_captions_for_audio(audio_path, script_path, speaker_names, output_dir=None):
    """Generate captions for an existing audio file."""
    
    try:
        from vibevoice.caption.simple_caption_generator import SimpleCaptionGenerator
        from vibevoice.caption.simple_caption_formatter import SimpleCaptionFormatter
        import librosa
        
        print(f"🎬 Generating captions for: {audio_path}")
        print(f"📝 Using script: {script_path}")
        
        # Read the script
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Get audio duration
        try:
            duration = librosa.get_duration(filename=audio_path)
            print(f"🎵 Audio duration: {duration:.2f} seconds")
        except ImportError:
            print("⚠️  librosa not available, estimating duration from file size")
            file_size = os.path.getsize(audio_path)
            duration = file_size / (1024 * 1024) * 10  # Rough estimate
            print(f"🎵 Estimated duration: {duration:.2f} seconds")
        
        # Create speaker mapping
        speaker_mapping = {i: name for i, name in enumerate(speaker_names)}
        print(f"👥 Speaker mapping: {speaker_mapping}")
        
        # Initialize caption generator
        generator = SimpleCaptionGenerator(
            words_per_minute=150,
            min_segment_duration=1.0,
            max_segment_duration=60.0
        )
        
        # Generate captions
        caption_segments = generator.generate_captions_from_script(
            script=script_content,
            audio_duration=duration,
            speaker_mapping=speaker_mapping,
            audio_path=audio_path
        )
        
        print(f"✅ Generated {len(caption_segments)} caption segments")
        
        # Display caption segments
        print("\n📋 Caption Segments:")
        for i, segment in enumerate(caption_segments, 1):
            print(f"  {i}. [{segment['start_time']:.1f}s - {segment['end_time']:.1f}s] {segment['speaker_name']}: {segment['text']}")
        
        # Create output directory
        if output_dir is None:
            output_dir = Path(audio_path).parent / "captions"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # Initialize formatter
        formatter = SimpleCaptionFormatter()
        
        # Generate different caption formats
        base_name = Path(audio_path).stem
        caption_files = {}
        
        formats = {
            'srt': formatter.format_srt,
            'vtt': formatter.format_vtt,
            'json': formatter.format_json,
            'transcript': formatter.format_transcript,
            'script_timing': formatter.format_script_with_timing
        }
        
        print(f"\n📝 Generating caption files in: {output_dir}")
        
        for format_name, formatter_func in formats.items():
            try:
                output_path = output_dir / f"{base_name}.{format_name}"
                formatter_func(caption_segments, str(output_path))
                caption_files[format_name] = str(output_path)
                print(f"✅ {format_name.upper()}: {output_path}")
            except Exception as e:
                print(f"❌ Failed to generate {format_name}: {e}")
        
        print(f"\n🎉 Caption generation completed!")
        print(f"📁 Caption files saved to: {output_dir}")
        
        return caption_files
        
    except Exception as e:
        print(f"❌ Error generating captions: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate captions for existing VibeVoice audio files")
    parser.add_argument("--audio_path", type=str, required=True, help="Path to the audio file")
    parser.add_argument("--script_path", type=str, required=True, help="Path to the script file")
    parser.add_argument("--speaker_names", nargs='+', required=True, help="Speaker names in order")
    parser.add_argument("--output_dir", type=str, help="Output directory for caption files")
    
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.audio_path):
        print(f"❌ Audio file not found: {args.audio_path}")
        return
    
    if not os.path.exists(args.script_path):
        print(f"❌ Script file not found: {args.script_path}")
        return
    
    # Generate captions
    caption_files = generate_captions_for_audio(
        audio_path=args.audio_path,
        script_path=args.script_path,
        speaker_names=args.speaker_names,
        output_dir=args.output_dir
    )
    
    if caption_files:
        print(f"\n📊 Summary:")
        print(f"   Audio file: {args.audio_path}")
        print(f"   Script file: {args.script_path}")
        print(f"   Speakers: {', '.join(args.speaker_names)}")
        print(f"   Caption files: {len(caption_files)}")
        for format_name, file_path in caption_files.items():
            print(f"     - {format_name}: {file_path}")

if __name__ == "__main__":
    main()

