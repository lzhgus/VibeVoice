"""
Enhanced VibeVoice Processor with Caption Generation

This module extends the VibeVoiceProcessor to include automatic caption generation
for generated audio, providing accessibility and content understanding features.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
import torch
from pathlib import Path

from .vibevoice_processor import VibeVoiceProcessor
from ..caption.caption_generator import CaptionGenerator
from ..caption.caption_formatter import CaptionFormatter

logger = logging.getLogger(__name__)


class VibeVoiceProcessorWithCaptions(VibeVoiceProcessor):
    """
    Enhanced VibeVoice processor with automatic caption generation.
    
    This processor extends the base VibeVoiceProcessor to automatically generate
    captions for all generated audio, providing accessibility features and
    content understanding capabilities.
    """
    
    def __init__(self, 
                 tokenizer=None, 
                 audio_processor=None, 
                 speech_tok_compress_ratio=3200, 
                 db_normalize=True,
                 caption_model="base",
                 caption_device=None,
                 caption_language=None,
                 **kwargs):
        """
        Initialize the enhanced processor with caption capabilities.
        
        Args:
            tokenizer: VibeVoice text tokenizer
            audio_processor: VibeVoice audio processor
            speech_tok_compress_ratio: Speech token compression ratio
            db_normalize: Whether to apply dB normalization
            caption_model: Whisper model size for caption generation
            caption_device: Device for caption generation
            caption_language: Language for caption generation
        """
        super().__init__(
            tokenizer=tokenizer,
            audio_processor=audio_processor,
            speech_tok_compress_ratio=speech_tok_compress_ratio,
            db_normalize=db_normalize,
            **kwargs
        )
        
        # Initialize caption components
        self.caption_generator = None
        self.caption_formatter = CaptionFormatter()
        self.caption_enabled = True
        
        # Caption configuration
        self.caption_model = caption_model
        self.caption_device = caption_device
        self.caption_language = caption_language
        
        # Initialize caption generator lazily
        self._caption_generator_initialized = False
    
    def _ensure_caption_generator(self):
        """Initialize caption generator if not already done."""
        if not self._caption_generator_initialized and self.caption_enabled:
            try:
                self.caption_generator = CaptionGenerator(
                    model_name=self.caption_model,
                    device=self.caption_device,
                    language=self.caption_language
                )
                self._caption_generator_initialized = True
                logger.info("Caption generator initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize caption generator: {e}")
                self.caption_enabled = False
    
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
        Save audio with automatic caption generation.
        
        Args:
            audio: Audio data to save
            output_path: Path to save the audio file
            sampling_rate: Sampling rate for the audio
            normalize: Whether to normalize audio before saving
            batch_prefix: Prefix for batch files
            original_script: Original script used for generation (for speaker identification)
            speaker_mapping: Mapping of speaker IDs to names
            generate_captions: Whether to generate captions
            caption_formats: List of caption formats to generate ('srt', 'vtt', 'json', 'transcript')
            
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
        if generate_captions and self.caption_enabled:
            try:
                self._ensure_caption_generator()
                
                if self.caption_generator:
                    # Generate captions for each audio file
                    caption_results = []
                    caption_files = {}
                    
                    for audio_path in audio_paths:
                        # Generate captions for this audio file
                        if original_script:
                            caption_result = self.caption_generator.generate_captions_for_script(
                                audio_path=audio_path,
                                original_script=original_script,
                                speaker_mapping=speaker_mapping
                            )
                        else:
                            # Simple transcription without speaker identification
                            transcription = self.caption_generator.transcribe_audio(audio_path)
                            caption_result = {
                                'transcription': transcription,
                                'caption_segments': [{
                                    'start_time': 0.0,
                                    'end_time': transcription['duration'],
                                    'text': transcription['text'],
                                    'speaker_id': 0,
                                    'speaker_name': 'Speaker',
                                    'confidence': 1.0
                                }],
                                'speaker_mapping': speaker_mapping or {},
                                'total_duration': transcription['duration']
                            }
                        
                        caption_results.append(caption_result)
                        
                        # Generate caption files in requested formats
                        if caption_formats is None:
                            caption_formats = ['srt', 'vtt', 'json', 'transcript']
                        
                        base_name = Path(audio_path).stem
                        caption_dir = Path(audio_path).parent / "captions"
                        
                        for format_name in caption_formats:
                            try:
                                if format_name == 'srt':
                                    caption_file = self.caption_formatter.format_srt(
                                        caption_result['caption_segments'],
                                        os.path.join(caption_dir, f"{base_name}.srt")
                                    )
                                elif format_name == 'vtt':
                                    caption_file = self.caption_formatter.format_vtt(
                                        caption_result['caption_segments'],
                                        os.path.join(caption_dir, f"{base_name}.vtt")
                                    )
                                elif format_name == 'json':
                                    caption_file = self.caption_formatter.format_json(
                                        caption_result['caption_segments'],
                                        os.path.join(caption_dir, f"{base_name}.json")
                                    )
                                elif format_name == 'transcript':
                                    caption_file = self.caption_formatter.format_transcript(
                                        caption_result['caption_segments'],
                                        os.path.join(caption_dir, f"{base_name}.txt")
                                    )
                                
                                caption_files[f"{base_name}_{format_name}"] = caption_file
                                
                            except Exception as e:
                                logger.warning(f"Failed to generate {format_name} captions: {e}")
                    
                    result['captions'] = caption_results
                    result['caption_files'] = caption_files
                    
                    logger.info(f"Generated captions for {len(audio_paths)} audio files")
                
            except Exception as e:
                logger.error(f"Caption generation failed: {e}")
                result['caption_error'] = str(e)
        
        return result
    
    def generate_podcast_with_captions(self,
                                     text: Union[str, List[str]],
                                     voice_samples: Optional[List[Union[str, np.ndarray]]] = None,
                                     output_path: str = "podcast.wav",
                                     speaker_names: Optional[List[str]] = None,
                                     generate_captions: bool = True,
                                     caption_formats: List[str] = None,
                                     **generation_kwargs) -> Dict[str, Any]:
        """
        Generate a complete podcast with captions.
        
        Args:
            text: Script text or list of scripts
            voice_samples: Voice samples for speakers
            output_path: Path to save the generated audio
            speaker_names: Names of speakers for caption identification
            generate_captions: Whether to generate captions
            caption_formats: Caption formats to generate
            **generation_kwargs: Additional generation parameters
            
        Returns:
            Dict containing generation results and caption information
        """
        # This is a placeholder for the full implementation
        # In practice, this would integrate with the model generation process
        
        logger.info("Generating podcast with captions")
        
        # Create speaker mapping if speaker names provided
        speaker_mapping = None
        if speaker_names:
            speaker_mapping = {i: name for i, name in enumerate(speaker_names)}
        
        # For now, return a placeholder result
        # In a full implementation, this would:
        # 1. Process the input text and voice samples
        # 2. Generate audio using the VibeVoice model
        # 3. Save audio with captions
        
        return {
            'audio_path': output_path,
            'captions': None,
            'caption_files': {},
            'speaker_mapping': speaker_mapping,
            'generation_parameters': generation_kwargs
        }
    
    def enable_captions(self, model_name: str = "base", device: str = None, language: str = None):
        """Enable caption generation with specified parameters."""
        self.caption_enabled = True
        self.caption_model = model_name
        self.caption_device = device
        self.caption_language = language
        self._caption_generator_initialized = False  # Force re-initialization
        logger.info("Caption generation enabled")
    
    def disable_captions(self):
        """Disable caption generation."""
        self.caption_enabled = False
        self.caption_generator = None
        self._caption_generator_initialized = False
        logger.info("Caption generation disabled")
    
    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, **kwargs):
        """Create processor instance from pretrained model with caption support."""
        # Get caption-specific parameters
        caption_model = kwargs.pop('caption_model', 'base')
        caption_device = kwargs.pop('caption_device', None)
        caption_language = kwargs.pop('caption_language', None)
        
        # Create base processor
        processor = super().from_pretrained(pretrained_model_name_or_path, **kwargs)
        
        # Convert to enhanced processor
        enhanced_processor = cls(
            tokenizer=processor.tokenizer,
            audio_processor=processor.audio_processor,
            speech_tok_compress_ratio=processor.speech_tok_compress_ratio,
            db_normalize=processor.db_normalize,
            caption_model=caption_model,
            caption_device=caption_device,
            caption_language=caption_language
        )
        
        return enhanced_processor
