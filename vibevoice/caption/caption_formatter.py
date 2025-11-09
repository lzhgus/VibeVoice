"""
Caption Formatter for VibeVoice

This module provides various caption formatting options including SRT, VTT,
and custom formats for different use cases.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import timedelta

logger = logging.getLogger(__name__)


class CaptionFormatter:
    """
    Formats captions into various subtitle and caption formats.
    
    Supports SRT, VTT, and custom formats for different applications.
    """
    
    def __init__(self):
        """Initialize the caption formatter."""
        pass
    
    def format_srt(self, caption_segments: List[Dict[str, Any]], 
                   output_path: Optional[str] = None) -> str:
        """
        Format captions as SRT (SubRip) subtitle file.
        
        Args:
            caption_segments (List[Dict[str, Any]]): List of caption segments with timing.
            output_path (str, optional): Path to save SRT file. If None, returns content as string.
            
        Returns:
            str: SRT content or path to saved file.
        """
        srt_content = []
        
        for i, segment in enumerate(caption_segments, 1):
            start_time = self._format_srt_time(segment.get('start_time', 0.0))
            end_time = self._format_srt_time(segment.get('end_time', 0.0))
            text = segment.get('text', '').strip()
            speaker = segment.get('speaker_name', '')
            
            # Format with speaker name if available
            if speaker:
                display_text = f"[{speaker}] {text}"
            else:
                display_text = text
            
            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(display_text)
            srt_content.append("")  # Empty line between segments
        
        srt_text = "\n".join(srt_content)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_text)
            logger.info(f"SRT captions saved to: {output_path}")
            return output_path
        
        return srt_text
    
    def format_vtt(self, caption_segments: List[Dict[str, Any]], 
                   output_path: Optional[str] = None) -> str:
        """
        Format captions as VTT (WebVTT) subtitle file.
        
        Args:
            caption_segments (List[Dict[str, Any]]): List of caption segments with timing.
            output_path (str, optional): Path to save VTT file. If None, returns content as string.
            
        Returns:
            str: VTT content or path to saved file.
        """
        vtt_content = ["WEBVTT", ""]  # VTT header
        
        for segment in caption_segments:
            start_time = self._format_vtt_time(segment.get('start_time', 0.0))
            end_time = self._format_vtt_time(segment.get('end_time', 0.0))
            text = segment.get('text', '').strip()
            speaker = segment.get('speaker_name', '')
            
            # Format with speaker name if available
            if speaker:
                display_text = f"<v {speaker}>{text}"
            else:
                display_text = text
            
            vtt_content.append(f"{start_time} --> {end_time}")
            vtt_content.append(display_text)
            vtt_content.append("")  # Empty line between segments
        
        vtt_text = "\n".join(vtt_content)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(vtt_text)
            logger.info(f"VTT captions saved to: {output_path}")
            return output_path
        
        return vtt_text
    
    def format_json(self, caption_segments: List[Dict[str, Any]], 
                    output_path: Optional[str] = None) -> str:
        """
        Format captions as JSON for programmatic use.
        
        Args:
            caption_segments (List[Dict[str, Any]]): List of caption segments with timing.
            output_path (str, optional): Path to save JSON file. If None, returns content as string.
            
        Returns:
            str: JSON content or path to saved file.
        """
        import json
        
        caption_data = {
            'format': 'vibevoice_captions',
            'version': '1.0',
            'segments': caption_segments,
            'total_segments': len(caption_segments),
            'total_duration': max(seg.get('end_time', 0.0) for seg in caption_segments) if caption_segments else 0.0
        }
        
        json_text = json.dumps(caption_data, indent=2, ensure_ascii=False)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_text)
            logger.info(f"JSON captions saved to: {output_path}")
            return output_path
        
        return json_text
    
    def format_transcript(self, caption_segments: List[Dict[str, Any]], 
                          output_path: Optional[str] = None,
                          include_timestamps: bool = True,
                          include_speakers: bool = True) -> str:
        """
        Format captions as a readable transcript.
        
        Args:
            caption_segments (List[Dict[str, Any]]): List of caption segments with timing.
            output_path (str, optional): Path to save transcript file. If None, returns content as string.
            include_timestamps (bool): Whether to include timestamps in the transcript.
            include_speakers (bool): Whether to include speaker names in the transcript.
            
        Returns:
            str: Transcript content or path to saved file.
        """
        transcript_lines = []
        
        for segment in caption_segments:
            text = segment.get('text', '').strip()
            speaker = segment.get('speaker_name', '')
            start_time = segment.get('start_time', 0.0)
            
            if not text:
                continue
            
            # Build transcript line
            line_parts = []
            
            if include_timestamps:
                timestamp = self._format_readable_time(start_time)
                line_parts.append(f"[{timestamp}]")
            
            if include_speakers and speaker:
                line_parts.append(f"{speaker}:")
            
            line_parts.append(text)
            
            transcript_lines.append(" ".join(line_parts))
        
        transcript_text = "\n".join(transcript_lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            logger.info(f"Transcript saved to: {output_path}")
            return output_path
        
        return transcript_text
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time in SRT format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time in VTT format (HH:MM:SS.mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{int(hours):02d}:{int(minutes):02d}:{seconds:06.3f}"
    
    def _format_readable_time(self, seconds: float) -> str:
        """Format time in readable format (MM:SS)."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def create_caption_package(self, 
                              caption_segments: List[Dict[str, Any]],
                              base_filename: str,
                              output_dir: str = "captions") -> Dict[str, str]:
        """
        Create a complete caption package with multiple formats.
        
        Args:
            caption_segments (List[Dict[str, Any]]): List of caption segments.
            base_filename (str): Base filename for caption files.
            output_dir (str): Directory to save caption files.
            
        Returns:
            Dict[str, str]: Dictionary mapping format names to file paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        caption_files = {}
        
        # Generate different formats
        formats = {
            'srt': self.format_srt,
            'vtt': self.format_vtt,
            'json': self.format_json,
            'transcript': self.format_transcript
        }
        
        for format_name, formatter_func in formats.items():
            output_path = os.path.join(output_dir, f"{base_filename}.{format_name}")
            formatter_func(caption_segments, output_path)
            caption_files[format_name] = output_path
        
        logger.info(f"Caption package created with {len(caption_files)} formats")
        return caption_files
