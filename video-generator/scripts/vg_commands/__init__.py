"""
Video Generator CLI Commands

All command modules for the vg CLI tool.
Each module provides functions and argument parsing for a specific command group.
"""

# Import all command modules for easy access
from . import record, audio, edit, compose, talking_head, quality, captions, utils, request, narration

__all__ = ['record', 'audio', 'edit', 'compose', 'talking_head', 'quality', 'captions', 'utils', 'request', 'narration']