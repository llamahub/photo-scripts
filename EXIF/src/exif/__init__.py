"""
EXIF module for photo processing and organization.

This module provides classes and utilities for working with photo metadata
and organizing photos based on EXIF data.
"""

from .image_data import ImageData
from .photo_organizer import PhotoOrganizer

__all__ = ['ImageData', 'PhotoOrganizer']