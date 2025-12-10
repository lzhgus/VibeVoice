"""
VibeVoice Processor with Simple Caption Generation

This processor generates captions directly from script text and audio timing,
without requiring speech-to-text transcription. Perfect for cases where you
already have the script and just need to add timing information.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
import torch
from pathlib import Path

from .vibevoice_processor import VibeVoiceProcessor
from ..caption.simple_caption_generator import SimpleCaptionGenerator
from ..caption.simple_caption_formatter import SimpleCaptionFormatter

logger = logging.getLogger(__name__)


class VibeVoiceProcessorSimpleCaptions(VibeVoiceProcessor):
    """
    VibeVoice processor with simple script-based caption generation.
    
    This processor generates captions directly from the script text and
    audio timing, without requiring speech-to-text transcription.
    """
    
    def __init__(self, 
                 tokenizer=None, 
                 audio_processor=None, 
                 speech_tok_compress_ratio=3200, 
                 db_normalize=True,
                 words_per_minute=150,
                 min_segment_duration=1.0,
                 max_segment_duration=10.0,
                 **kwargs):
        """
        Initialize the processor with simple caption capabilities.
        
        Args:
            tokenizer: VibeVoice text tokenizer
            audio_processor: VibeVoice audio processor
            speech_tok_compress_ratio: Speech token compression ratio
            db_normalize: Whether to apply dB normalization
            words_per_minute: Average speaking rate for timing estimation
            min_segment_duration: Minimum duration for a caption segment
            max_segment_duration: Maximum duration for a caption segment
        """
        super().__init__(
            tokenizer=tokenizer,
            audio_processor=audio_processor,
            speech_tok_compress_ratio=speech_tok_compress_ratio,
            db_normalize=db_normalize,
            **kwargs
        )
        
        # Initialize simple caption components
        self.caption_generator = SimpleCaptionGenerator(
            words_per_minute=words_per_minute,
            min_segment_duration=min_segment_duration,
            max_segment_duration=max_segment_duration
        )
        self.caption_formatter = SimpleCaptionFormatter()
        self.caption_enabled = True
        
        # Caption configuration
        self.words_per_minute = words_per_minute
        self.min_segment_duration = min_segment_duration
        self.max_segment_duration = max_segment_duration
    
    def save_audio_with_captions(self, 
                                audio: Union[torch.Tensor, np.ndarray, List[Union[torch.Tensor, np.ndarray]]],
                                output_path: str = "output.wav",
                                sampling_rate: Optional[int] = None,
                                normalize: bool = False,
                                batch_prefix: str = "audio_",
                                original_script: Optional[str] = None,
                                speaker_mapping: Optional[Dict[int, str]] = None,
                                generate_captions: bool = True,
                                caption_formats: List[str] = None) -> Dict[str, Any]:
        """
        Save audio with automatic script-based caption generation.
        
        Args:
            audio: Audio data to save
            output_path: Path to save the audio file
            sampling_rate: Sampling rate for the audio
            normalize: Whether to normalize audio before saving
            batch_prefix: Prefix for batch files
            original_script: Original script used for generation (required for captions)
            speaker_mapping: Mapping of speaker IDs to names
            generate_captions: Whether to generate captions
            caption_formats: List of caption formats to generate ('srt', 'vtt', 'json', 'transcript', 'script_timing')
            
        Returns:
            Dict containing audio file path and caption information
        """
        # Save audio using parent method
        audio_paths = self.save_audio(
            audio=audio,
            output_path=output_path,
            sampling_rate=sampling_rate,
            normalize=normalize,
            batch_prefix=batch_prefix
        )
        
        result = {
            'audio_paths': audio_paths,
            'captions': None,
            'caption_files': {}
        }
        
        # Generate captions if requested and enabled
        if generate_captions and self.caption_enabled and original_script:
            try:
                logger.info("🎬 Generating script-based captions...")
                
                # Calculate audio duration
                if isinstance(audio, (list, tuple)):
                    # For batch audio, use the first item for duration calculation
                    audio_item = audio[0]
                else:
                    audio_item = audio
                
                # Convert to numpy if needed
                if torch.is_tensor(audio_item):
                    # Convert BFloat16 to float32 to avoid numpy conversion issues
                    if audio_item.dtype == torch.bfloat16:
                        audio_item = audio_item.float()
                    audio_np = audio_item.detach().cpu().numpy()
                else:
                    audio_np = np.array(audio_item)
                
                # Calculate duration
                if sampling_rate is None:
                    sampling_rate = 24000  # Default sample rate
                
                if len(audio_np.shape) > 1:
                    audio_np = audio_np.squeeze()
                
                audio_duration = len(audio_np) / sampling_rate
                
                # Generate captions from script
                caption_segments = self.caption_generator.generate_captions_from_script(
                    script=original_script,
                    audio_duration=audio_duration,
                    speaker_mapping=speaker_mapping,
                    audio_path=audio_paths[0] if audio_paths else None
                )
                
                if caption_segments:
                    # Split long segments if needed
                    caption_segments = self.caption_generator.split_long_segments(
                        caption_segments, 
                        max_duration=self.max_segment_duration
                    )
                    
                    # Generate caption files in requested formats
                    if caption_formats is None:
                        caption_formats = ['srt', 'vtt', 'transcript']
                    
                    for audio_path in audio_paths:
                        base_name = Path(audio_path).stem
                        caption_dir = Path(audio_path).parent / "captions"
                        
                        # Create captions directory if it doesn't exist
                        caption_dir.mkdir(parents=True, exist_ok=True)
                        
                        for format_name in caption_formats:
                            try:
                                if format_name == 'srt':
                                    caption_file = self.caption_formatter.format_srt(
                                        caption_segments,
                                        os.path.join(caption_dir, f"{base_name}.srt")
                                    )
                                elif format_name == 'vtt':
                                    caption_file = self.caption_formatter.format_vtt(
                                        caption_segments,
                                        os.path.join(caption_dir, f"{base_name}.vtt")
                                    )
                                elif format_name == 'json':
                                    caption_file = self.caption_formatter.format_json(
                                        caption_segments,
                                        os.path.join(caption_dir, f"{base_name}.json")
                                    )
                                elif format_name == 'transcript':
                                    caption_file = self.caption_formatter.format_transcript(
                                        caption_segments,
                                        os.path.join(caption_dir, f"{base_name}.txt")
                                    )
                                elif format_name == 'script_timing':
                                    caption_file = self.caption_formatter.format_script_with_timing(
                                        caption_segments,
                                        os.path.join(caption_dir, f"{base_name}_timing.txt")
                                    )
                                
                                result['caption_files'][f"{base_name}_{format_name}"] = caption_file
                                
                            except Exception as e:
                                logger.warning(f"Failed to generate {format_name} captions: {e}")
                    
                    result['captions'] = caption_segments
                    logger.info(f"✅ Generated {len(caption_segments)} caption segments")
                    logger.info(f"📝 Caption files: {list(result['caption_files'].keys())}")
                else:
                    logger.warning("No caption segments generated")
                    
            except Exception as e:
                logger.error(f"Caption generation failed: {e}")
                result['caption_error'] = str(e)
        elif generate_captions and not original_script:
            logger.warning("Caption generation requested but no original script provided")
            result['caption_error'] = "No original script provided for caption generation"
        
        return result
    
    def generate_captions_for_audio(self,
                                   audio_path: str,
                                   original_script: str,
                                   speaker_mapping: Optional[Dict[int, str]] = None,
                                   caption_formats: List[str] = None) -> Dict[str, Any]:
        """
        Generate captions for an existing audio file.
        
        Args:
            audio_path: Path to the audio file
            original_script: Original script text
            speaker_mapping: Mapping of speaker IDs to names
            caption_formats: List of caption formats to generate
            
        Returns:
            Dict containing caption information
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Get audio duration
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
        except ImportError:
            # Fallback: estimate from file size
            file_size = os.path.getsize(audio_path)
            duration = file_size / (1024 * 1024) * 10  # Rough estimate
        
        # Generate captions
        caption_segments = self.caption_generator.generate_captions_from_script(
            script=original_script,
            audio_duration=duration,
            speaker_mapping=speaker_mapping,
            audio_path=audio_path
        )
        
        # Split long segments
        caption_segments = self.caption_generator.split_long_segments(
            caption_segments, 
            max_duration=self.max_segment_duration
        )
        
        # Generate caption files
        result = {
            'caption_segments': caption_segments,
            'caption_files': {}
        }
        
        if caption_formats is None:
            caption_formats = ['srt', 'vtt', 'transcript']
        
        base_name = Path(audio_path).stem
        caption_dir = Path(audio_path).parent / "captions"
        
        for format_name in caption_formats:
            try:
                if format_name == 'srt':
                    caption_file = self.caption_formatter.format_srt(
                        caption_segments,
                        os.path.join(caption_dir, f"{base_name}.srt")
                    )
                elif format_name == 'vtt':
                    caption_file = self.caption_formatter.format_vtt(
                        caption_segments,
                        os.path.join(caption_dir, f"{base_name}.vtt")
                    )
                elif format_name == 'json':
                    caption_file = self.caption_formatter.format_json(
                        caption_segments,
                        os.path.join(caption_dir, f"{base_name}.json")
                    )
                elif format_name == 'transcript':
                    caption_file = self.caption_formatter.format_transcript(
                        caption_segments,
                        os.path.join(caption_dir, f"{base_name}.txt")
                    )
                elif format_name == 'script_timing':
                    caption_file = self.caption_formatter.format_script_with_timing(
                        caption_segments,
                        os.path.join(caption_dir, f"{base_name}_timing.txt")
                    )
                
                result['caption_files'][f"{base_name}_{format_name}"] = caption_file
                
            except Exception as e:
                logger.warning(f"Failed to generate {format_name} captions: {e}")
        
        return result
    
    def enable_captions(self, words_per_minute: int = 150, 
                       min_segment_duration: float = 1.0, 
                       max_segment_duration: float = 10.0):
        """Enable caption generation with specified parameters."""
        self.caption_enabled = True
        self.words_per_minute = words_per_minute
        self.min_segment_duration = min_segment_duration
        self.max_segment_duration = max_segment_duration
        
        # Update caption generator
        self.caption_generator = SimpleCaptionGenerator(
            words_per_minute=words_per_minute,
            min_segment_duration=min_segment_duration,
            max_segment_duration=max_segment_duration
        )
        
        logger.info("Simple caption generation enabled")
    
    def disable_captions(self):
        """Disable caption generation."""
        self.caption_enabled = False
        logger.info("Caption generation disabled")
    
    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, **kwargs):
        """Create processor instance from pretrained model with simple caption support."""
        # Get caption-specific parameters
        words_per_minute = kwargs.pop('words_per_minute', 150)
        min_segment_duration = kwargs.pop('min_segment_duration', 1.0)
        max_segment_duration = kwargs.pop('max_segment_duration', 10.0)
        
        # Create base processor
        processor = super().from_pretrained(pretrained_model_name_or_path, **kwargs)
        
        # Convert to enhanced processor
        enhanced_processor = cls(
            tokenizer=processor.tokenizer,
            audio_processor=processor.audio_processor,
            speech_tok_compress_ratio=processor.speech_tok_compress_ratio,
            db_normalize=processor.db_normalize,
            words_per_minute=words_per_minute,
            min_segment_duration=min_segment_duration,
            max_segment_duration=max_segment_duration
        )
        
        return enhanced_processor

