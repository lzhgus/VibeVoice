"""
Caption Generator for VibeVoice Audio

This module provides speech-to-text transcription capabilities for generated audio,
creating captions that can be used for accessibility and content understanding.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
import torch
from pathlib import Path

logger = logging.getLogger(__name__)


class CaptionGenerator:
    """
    Generates captions from audio using speech-to-text transcription.
    
    This class provides functionality to transcribe audio files and generate
    captions with timing information for accessibility and content understanding.
    """
    
    def __init__(self, 
                 model_name: str = "base",
                 device: Optional[str] = None,
                 language: Optional[str] = None):
        """
        Initialize the caption generator.
        
        Args:
            model_name (str): Whisper model size ('tiny', 'base', 'small', 'medium', 'large').
                              Default: 'base' for good balance of speed and accuracy.
            device (str, optional): Device to run inference on ('cpu', 'cuda', 'mps').
                                   If None, auto-detects best available device.
            language (str, optional): Language code for transcription (e.g., 'en', 'zh').
                                    If None, auto-detects language.
        """
        self.model_name = model_name
        self.device = device or self._get_best_device()
        self.language = language
        self.model = None
        self._load_model()
        
    def _get_best_device(self) -> str:
        """Determine the best available device for inference."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def _load_model(self):
        """Load the Whisper model for transcription."""
        try:
            import whisper
            logger.info(f"Loading Whisper model '{self.model_name}' on device '{self.device}'")
            self.model = whisper.load_model(self.model_name, device=self.device)
            logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.error("Whisper not installed. Install with: pip install openai-whisper")
            raise ImportError(
                "Whisper is required for caption generation. "
                "Install it with: pip install openai-whisper"
            )
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe_audio(self, 
                        audio_path: str,
                        return_timestamps: bool = True,
                        return_word_timestamps: bool = False) -> Dict[str, Any]:
        """
        Transcribe audio file to text with optional timing information.
        
        Args:
            audio_path (str): Path to the audio file to transcribe.
            return_timestamps (bool): Whether to include segment timestamps.
            return_word_timestamps (bool): Whether to include word-level timestamps.
            
        Returns:
            Dict[str, Any]: Transcription result containing:
                - 'text': Full transcribed text
                - 'segments': List of segments with timestamps (if return_timestamps=True)
                - 'language': Detected language
                - 'duration': Audio duration in seconds
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio: {audio_path}")
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_path,
                language=self.language,
                word_timestamps=return_word_timestamps,
                verbose=False
            )
            
            # Extract basic information
            transcription_result = {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'duration': self._get_audio_duration(audio_path)
            }
            
            # Add segments if timestamps requested
            if return_timestamps and 'segments' in result:
                transcription_result['segments'] = result['segments']
            
            # Add word timestamps if requested
            if return_word_timestamps:
                transcription_result['word_timestamps'] = self._extract_word_timestamps(result)
            
            logger.info(f"Transcription completed. Duration: {transcription_result['duration']:.2f}s")
            return transcription_result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_audio_array(self, 
                              audio_array: np.ndarray,
                              sample_rate: int = 24000,
                              return_timestamps: bool = True) -> Dict[str, Any]:
        """
        Transcribe audio array directly without saving to file.
        
        Args:
            audio_array (np.ndarray): Audio data as numpy array.
            sample_rate (int): Sample rate of the audio data.
            return_timestamps (bool): Whether to include segment timestamps.
            
        Returns:
            Dict[str, Any]: Transcription result (same format as transcribe_audio).
        """
        logger.info(f"Transcribing audio array with shape {audio_array.shape}")
        
        try:
            # Whisper expects audio as float32 in range [-1, 1]
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)
            
            # Normalize if needed
            if np.max(np.abs(audio_array)) > 1.0:
                audio_array = audio_array / np.max(np.abs(audio_array))
            
            # Transcribe directly
            result = self.model.transcribe(
                audio_array,
                language=self.language,
                verbose=False
            )
            
            # Extract information
            transcription_result = {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'duration': len(audio_array) / sample_rate
            }
            
            if return_timestamps and 'segments' in result:
                transcription_result['segments'] = result['segments']
            
            logger.info(f"Array transcription completed. Duration: {transcription_result['duration']:.2f}s")
            return transcription_result
            
        except Exception as e:
            logger.error(f"Array transcription failed: {e}")
            raise
    
    def _extract_word_timestamps(self, whisper_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract word-level timestamps from Whisper result."""
        word_timestamps = []
        
        for segment in whisper_result.get('segments', []):
            for word_info in segment.get('words', []):
                word_timestamps.append({
                    'word': word_info.get('word', '').strip(),
                    'start': word_info.get('start', 0.0),
                    'end': word_info.get('end', 0.0),
                    'confidence': word_info.get('probability', 0.0)
                })
        
        return word_timestamps
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
            return duration
        except Exception:
            # Fallback: estimate from file size (rough approximation)
            file_size = os.path.getsize(audio_path)
            # Rough estimate: 1MB ≈ 10 seconds for typical audio
            return file_size / (1024 * 1024) * 10
    
    def generate_captions_for_script(self, 
                                   audio_path: str,
                                   original_script: str,
                                   speaker_mapping: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
        """
        Generate captions with speaker identification based on original script.
        
        Args:
            audio_path (str): Path to generated audio file.
            original_script (str): Original script used for generation.
            speaker_mapping (Dict[int, str], optional): Mapping of speaker IDs to names.
            
        Returns:
            Dict[str, Any]: Caption result with speaker identification.
        """
        logger.info("Generating captions with speaker identification")
        
        # Transcribe the audio
        transcription = self.transcribe_audio(audio_path, return_timestamps=True)
        
        # Parse original script to get speaker information
        script_segments = self._parse_script_segments(original_script)
        
        # Match transcription segments to script segments
        caption_segments = self._match_transcription_to_script(
            transcription['segments'],
            script_segments,
            speaker_mapping
        )
        
        return {
            'transcription': transcription,
            'caption_segments': caption_segments,
            'speaker_mapping': speaker_mapping or {},
            'total_duration': transcription['duration']
        }
    
    def _parse_script_segments(self, script: str) -> List[Dict[str, Any]]:
        """Parse script into segments with speaker information."""
        import re
        
        segments = []
        lines = script.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Match "Speaker X: text" format
            match = re.match(r'^Speaker\s+(\d+)\s*:\s*(.*)$', line, re.IGNORECASE)
            if match:
                speaker_id = int(match.group(1))
                text = match.group(2).strip()
                if text:
                    segments.append({
                        'speaker_id': speaker_id,
                        'text': text,
                        'length': len(text)
                    })
        
        return segments
    
    def _match_transcription_to_script(self, 
                                    transcription_segments: List[Dict[str, Any]],
                                    script_segments: List[Dict[str, Any]],
                                    speaker_mapping: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
        """Match transcription segments to script segments for speaker identification."""
        caption_segments = []
        
        # Simple matching: assign speakers based on text similarity and timing
        for i, trans_segment in enumerate(transcription_segments):
            trans_text = trans_segment.get('text', '').strip().lower()
            
            # Find best matching script segment
            best_match = None
            best_score = 0
            
            for script_segment in script_segments:
                script_text = script_segment['text'].strip().lower()
                
                # Calculate similarity (simple word overlap)
                trans_words = set(trans_text.split())
                script_words = set(script_text.split())
                
                if trans_words and script_words:
                    overlap = len(trans_words.intersection(script_words))
                    similarity = overlap / max(len(trans_words), len(script_words))
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = script_segment
            
            # Create caption segment
            speaker_id = best_match['speaker_id'] if best_match else 0
            speaker_name = speaker_mapping.get(speaker_id, f"Speaker {speaker_id}") if speaker_mapping else f"Speaker {speaker_id}"
            
            caption_segments.append({
                'start_time': trans_segment.get('start', 0.0),
                'end_time': trans_segment.get('end', 0.0),
                'text': trans_segment.get('text', '').strip(),
                'speaker_id': speaker_id,
                'speaker_name': speaker_name,
                'confidence': trans_segment.get('no_speech_prob', 0.0)
            })
        
        return caption_segments
