"""
Enums for Visual Style module
"""
from enum import Enum


class VisualStyleType(str, Enum):
    """Enum for visual style types"""
    CARTOON = "cartoon"
    TWO_D = "2d"
    THREE_D = "3d"
    VOLUMETRIC = "volumetric"
    REALISTIC = "realistic"
    ANIME = "anime"
    PIXEL_ART = "pixel_art"
    WATERCOLOR = "watercolor"
    OIL_PAINTING = "oil_painting"
    COMIC = "comic"
    FLAT = "flat"
    SKETCHED = "sketched"


class VisualStyleStatus(str, Enum):
    """Enum for visual style analysis status"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

