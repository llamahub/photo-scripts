"""
File Manager for handling file type classification and operations.

This module provides centralized file type classification for images, videos,
and other files. It serves as the single source of truth for supported file
extensions.
"""

from pathlib import Path
from typing import Set


class FileManager:
    """Handles file type classification and file operations."""

    # Supported image file extensions
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".heic",
        ".heif",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
        ".dng",
        ".orf",
        ".rw2",
        ".pef",
        ".srw",
        ".x3f",
    }

    # Supported video file extensions
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".3gp",
        ".mpg",
        ".mpeg",
        ".mts",
        ".m2ts",
        ".ts",
    }

    @classmethod
    def get_image_extensions(cls) -> Set[str]:
        """Get set of supported image file extensions."""
        return cls.IMAGE_EXTENSIONS.copy()

    @classmethod
    def get_video_extensions(cls) -> Set[str]:
        """Get set of supported video file extensions."""
        return cls.VIDEO_EXTENSIONS.copy()

    @classmethod
    def get_all_media_extensions(cls) -> Set[str]:
        """Get set of all supported media file extensions (images + videos)."""
        return cls.IMAGE_EXTENSIONS | cls.VIDEO_EXTENSIONS

    @classmethod
    def is_image_file(cls, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        return file_path.suffix.lower() in cls.IMAGE_EXTENSIONS

    @classmethod
    def is_video_file(cls, file_path: Path) -> bool:
        """Check if file is a supported video format."""
        return file_path.suffix.lower() in cls.VIDEO_EXTENSIONS

    @classmethod
    def is_media_file(cls, file_path: Path) -> bool:
        """Check if file is a supported media format (image or video)."""
        return cls.is_image_file(file_path) or cls.is_video_file(file_path)

    @classmethod
    def classify_file(cls, file_path: Path) -> str:
        """
        Classify file into type: 'image', 'video', or 'other'.

        Args:
            file_path: Path to the file to classify

        Returns:
            str: 'image', 'video', or 'other'
        """
        if cls.is_image_file(file_path):
            return "image"
        elif cls.is_video_file(file_path):
            return "video"
        else:
            return "other"
