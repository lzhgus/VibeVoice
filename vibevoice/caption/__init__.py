"""
VibeVoice Caption Module

This module provides caption generation functionality for VibeVoice audio outputs.
It includes speech-to-text transcription and caption formatting capabilities.
"""

from .caption_generator import CaptionGenerator
from .caption_formatter import CaptionFormatter

__all__ = ["CaptionGenerator", "CaptionFormatter"]
