"""
Simple Caption Generator for VibeVoice

This module generates captions directly from the script text and audio timing,
without requiring speech-to-text transcription. Perfect for cases where you
already have the script and just need to add timing information.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleCaptionGenerator:
    """
    Generates captions from script text and audio timing information.
    
    This class creates captions by parsing the original script and estimating
    timing based on text length and audio duration, without requiring
    speech-to-text transcription.
    """
    
    def __init__(self, 
                 words_per_minute: int = 150,
                 min_segment_duration: float = 1.0,
                 max_segment_duration: float = 60.0,
                 pause_between_speakers: float = 0.5,
                 pause_between_segments: float = 0.3):
        """
        Initialize the simple caption generator.
        
        Args:
            words_per_minute (int): Average speaking rate for timing estimation.
            min_segment_duration (float): Minimum duration for a caption segment.
            max_segment_duration (float): Maximum duration for a caption segment.
            pause_between_speakers (float): Pause duration when speaker changes.
            pause_between_segments (float): Pause duration between segments from same speaker.
        """
        self.words_per_minute = words_per_minute
        self.min_segment_duration = min_segment_duration
        self.max_segment_duration = max_segment_duration
        self.pause_between_speakers = pause_between_speakers
        self.pause_between_segments = pause_between_segments
    
    def generate_captions_from_script(self, 
                                    script: str,
                                    audio_duration: float,
                                    speaker_mapping: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
        """
        Generate captions from script text and audio duration.
        
        Args:
            script (str): Original script text with speaker labels.
            audio_duration (float): Total duration of the audio in seconds.
            speaker_mapping (Dict[int, str], optional): Mapping of speaker IDs to names.
            
        Returns:
            List[Dict[str, Any]]: List of caption segments with timing.
        """
        logger.info(f"Generating captions from script (duration: {audio_duration:.2f}s)")
        
        # Parse script into segments
        script_segments = self._parse_script_segments(script)
        
        if not script_segments:
            logger.warning("No script segments found")
            return []
        
        # Calculate timing for each segment
        caption_segments = self._calculate_timing(script_segments, audio_duration, speaker_mapping)
        
        logger.info(f"Generated {len(caption_segments)} caption segments")
        return caption_segments
    
    def _parse_script_segments(self, script: str) -> List[Dict[str, Any]]:
        """Parse script into segments with speaker information."""
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
                    # Split long segments into smaller chunks (max 15 words)
                    segments.extend(self._split_long_segment(speaker_id, text))
        
        return segments
    
    def _split_long_segment(self, speaker_id: int, text: str, max_words: int = 15) -> List[Dict[str, Any]]:
        """Split long text segments into smaller chunks."""
        words = text.split()
        segments = []
        
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = ' '.join(chunk_words)
            
            segments.append({
                'speaker_id': speaker_id,
                'text': chunk_text,
                'word_count': len(chunk_words),
                'char_count': len(chunk_text)
            })
        
        return segments
    
    def _calculate_timing(self, 
                         script_segments: List[Dict[str, Any]], 
                         audio_duration: float,
                         speaker_mapping: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
        """Calculate timing for each script segment."""
        if not script_segments:
            return []
        
        # Calculate total words and characters
        total_words = sum(seg['word_count'] for seg in script_segments)
        total_chars = sum(seg['char_count'] for seg in script_segments)
        
        # Estimate timing based on words per minute
        words_per_second = self.words_per_minute / 60.0
        estimated_duration = total_words / words_per_second
        
        # Add estimated pauses between segments
        estimated_pauses = len(script_segments) * 0.5  # 0.5 seconds average pause
        estimated_duration += estimated_pauses
        
        # Scale timing to match actual audio duration
        if estimated_duration > 0:
            time_scale = audio_duration / estimated_duration
        else:
            time_scale = 1.0
        
        # Debug: print timing info
        print(f"Timing: estimated={estimated_duration:.1f}s, audio={audio_duration:.1f}s, scale={time_scale:.2f}")
        
        # Generate caption segments with timing
        caption_segments = []
        current_time = 0.0
        
        # Pre-calculate all segment durations to ensure proper distribution
        segment_durations = []
        for i, segment in enumerate(script_segments):
            # Calculate base segment duration based on word count (without time scale)
            base_duration = segment['word_count'] / words_per_second
            
            # Apply text-based adjustments for more natural timing
            segment_duration = self._calculate_natural_timing(segment, base_duration, i, script_segments, time_scale)
            
            # Apply duration constraints
            segment_duration = max(self.min_segment_duration, segment_duration)
            segment_duration = min(segment_duration, self.max_segment_duration)
            
            segment_durations.append(segment_duration)
        
        # Calculate total estimated duration including pauses
        total_estimated = sum(segment_durations)
        estimated_pauses = len(script_segments) * 0.5  # Average pause
        total_estimated += estimated_pauses
        
        # If we're over the audio duration, scale down all segments proportionally
        if total_estimated > audio_duration:
            scale_factor = audio_duration / total_estimated
            segment_durations = [d * scale_factor for d in segment_durations]
        
        # Generate caption segments with corrected timing
        for i, segment in enumerate(script_segments):
            segment_duration = segment_durations[i]
            
            # Debug: print timing for first few segments
            if i < 3:
                print(f"Segment {i+1}: duration={segment_duration:.1f}s")
            
            # Debug: print final timing for last few segments
            if i >= len(script_segments) - 3:
                print(f"Final Segment {i+1}: start={current_time:.1f}s, end={current_time + segment_duration:.1f}s, duration={segment_duration:.1f}s")
            
            # Ensure we don't exceed total audio duration
            if current_time + segment_duration > audio_duration:
                segment_duration = max(0.1, audio_duration - current_time)
            
            end_time = current_time + segment_duration
            
            # Final safety check - ensure end_time doesn't exceed audio duration
            if end_time > audio_duration:
                end_time = audio_duration
                segment_duration = end_time - current_time
            
            # Get speaker name
            speaker_id = segment['speaker_id']
            speaker_name = speaker_mapping.get(speaker_id, f"Speaker {speaker_id}") if speaker_mapping else f"Speaker {speaker_id}"
            
            caption_segments.append({
                'start_time': current_time,
                'end_time': end_time,
                'text': segment['text'],
                'speaker_id': speaker_id,
                'speaker_name': speaker_name,
                'confidence': 1.0,  # Perfect confidence since we have the original text
                'word_count': segment['word_count'],
                'char_count': segment['char_count']
            })
            
            current_time = end_time
            
            # Add appropriate pause based on speaker change
            if i < len(script_segments) - 1:
                next_speaker = script_segments[i + 1]['speaker_id']
                current_speaker = segment['speaker_id']
                
                # Calculate remaining time and segments
                remaining_time = audio_duration - current_time
                remaining_segments = len(script_segments) - i - 1
                
                if remaining_time > 0 and remaining_segments > 0:
                    if next_speaker != current_speaker:
                        # Different speaker - longer pause
                        pause_duration = min(self.pause_between_speakers, remaining_time / remaining_segments)
                    else:
                        # Same speaker - shorter pause
                        pause_duration = min(self.pause_between_segments, remaining_time / remaining_segments)
                    
                    # Ensure we don't exceed audio duration
                    if current_time + pause_duration > audio_duration:
                        pause_duration = max(0, audio_duration - current_time)
                    
                    current_time += pause_duration
        
        return caption_segments
    
    def _calculate_natural_timing(self, segment: Dict[str, Any], base_duration: float, 
                                segment_index: int, all_segments: List[Dict[str, Any]], 
                                time_scale: float = 1.0) -> float:
        """Calculate more natural timing based on text characteristics."""
        text = segment['text']
        word_count = segment['word_count']
        
        # Base duration from word count
        duration = base_duration
        
        # Adjust for punctuation (pauses at commas, periods, etc.)
        punctuation_pauses = text.count(',') * 0.3 + text.count('.') * 0.5 + text.count('!') * 0.4 + text.count('?') * 0.4
        duration += punctuation_pauses
        
        # Adjust for sentence length (longer sentences need more time)
        sentences = text.split('.')
        if len(sentences) > 1:
            avg_sentence_length = word_count / len(sentences)
            if avg_sentence_length > 15:  # Long sentences
                duration *= 1.1
            elif avg_sentence_length < 8:  # Short sentences
                duration *= 0.9
        
        # Adjust for question marks (questions often have pauses)
        if '?' in text:
            duration *= 1.05
        
        # Adjust for exclamation marks (emphasis takes time)
        if '!' in text:
            duration *= 1.03
        
        # Adjust for numbers and technical terms (slower reading)
        if any(char.isdigit() for char in text):
            duration *= 1.05
        
        # Adjust for very long segments (need breathing room)
        if word_count > 30:
            duration *= 1.1
        
        # Adjust for very short segments (might be spoken faster)
        if word_count < 5:
            duration *= 0.95
        
        # Apply the time scale to match audio duration
        duration *= time_scale
        
        return duration
    
    def generate_captions_with_custom_timing(self,
                                           script: str,
                                           timing_info: List[Dict[str, Any]],
                                           speaker_mapping: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
        """
        Generate captions with custom timing information.
        
        Args:
            script (str): Original script text.
            timing_info (List[Dict[str, Any]]): Custom timing for each segment.
            speaker_mapping (Dict[int, str], optional): Speaker name mapping.
            
        Returns:
            List[Dict[str, Any]]: Caption segments with custom timing.
        """
        script_segments = self._parse_script_segments(script)
        
        if len(script_segments) != len(timing_info):
            logger.warning(f"Mismatch between script segments ({len(script_segments)}) and timing info ({len(timing_info)})")
            # Fall back to automatic timing
            return self.generate_captions_from_script(script, sum(t['duration'] for t in timing_info), speaker_mapping)
        
        caption_segments = []
        
        for i, (segment, timing) in enumerate(zip(script_segments, timing_info)):
            speaker_id = segment['speaker_id']
            speaker_name = speaker_mapping.get(speaker_id, f"Speaker {speaker_id}") if speaker_mapping else f"Speaker {speaker_id}"
            
            caption_segments.append({
                'start_time': timing.get('start_time', 0.0),
                'end_time': timing.get('end_time', timing.get('start_time', 0.0) + timing.get('duration', 3.0)),
                'text': segment['text'],
                'speaker_id': speaker_id,
                'speaker_name': speaker_name,
                'confidence': 1.0,
                'word_count': segment['word_count'],
                'char_count': segment['char_count']
            })
        
        return caption_segments
    
    def adjust_timing_for_audio(self,
                               caption_segments: List[Dict[str, Any]],
                               actual_audio_duration: float) -> List[Dict[str, Any]]:
        """
        Adjust caption timing to match actual audio duration.
        
        Args:
            caption_segments (List[Dict[str, Any]]): Original caption segments.
            actual_audio_duration (float): Actual audio duration in seconds.
            
        Returns:
            List[Dict[str, Any]]: Adjusted caption segments.
        """
        if not caption_segments:
            return []
        
        # Calculate current total duration
        current_duration = max(seg['end_time'] for seg in caption_segments)
        
        if current_duration <= 0:
            return caption_segments
        
        # Calculate scale factor
        scale_factor = actual_audio_duration / current_duration
        
        # Adjust timing for each segment
        adjusted_segments = []
        for segment in caption_segments:
            adjusted_segment = segment.copy()
            adjusted_segment['start_time'] = segment['start_time'] * scale_factor
            adjusted_segment['end_time'] = segment['end_time'] * scale_factor
            adjusted_segments.append(adjusted_segment)
        
        return adjusted_segments
    
    def split_long_segments(self, 
                           caption_segments: List[Dict[str, Any]], 
                           max_duration: float = 8.0) -> List[Dict[str, Any]]:
        """
        Split caption segments that are too long.
        
        Args:
            caption_segments (List[Dict[str, Any]]): Original caption segments.
            max_duration (float): Maximum duration for a single segment.
            
        Returns:
            List[Dict[str, Any]]: Split caption segments.
        """
        split_segments = []
        
        for segment in caption_segments:
            duration = segment['end_time'] - segment['start_time']
            
            if duration <= max_duration:
                split_segments.append(segment)
            else:
                # Split the segment
                text = segment['text']
                words = text.split()
                num_words = len(words)
                
                # Calculate how many segments we need
                num_segments = max(1, int(duration / max_duration))
                words_per_segment = num_words // num_segments
                
                start_time = segment['start_time']
                segment_duration = duration / num_segments
                
                for i in range(num_segments):
                    start_word = i * words_per_segment
                    end_word = start_word + words_per_segment if i < num_segments - 1 else num_words
                    
                    segment_text = ' '.join(words[start_word:end_word])
                    segment_start = start_time + i * segment_duration
                    segment_end = segment_start + segment_duration
                    
                    split_segments.append({
                        'start_time': segment_start,
                        'end_time': segment_end,
                        'text': segment_text,
                        'speaker_id': segment['speaker_id'],
                        'speaker_name': segment['speaker_name'],
                        'confidence': segment['confidence'],
                        'word_count': len(segment_text.split()),
                        'char_count': len(segment_text)
                    })
        
        return split_segments

