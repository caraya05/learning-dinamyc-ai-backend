"""
Models for Visual Style module - Database schema representation
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from visual_style.enums import VisualStyleType, VisualStyleStatus


class VisualStyle(BaseModel):
    """Visual Style database model"""
    user_id: str = Field(..., example="user_id", description="User who created this visual style")
    name: str = Field(..., example="Fantasy Cartoon Style", description="Name of the visual style")
    description: Optional[str] = Field(None, example="A cartoon style inspired by fantasy games")

    # Original inputs
    original_prompt: str = Field(..., example="Create a cartoon style")
    reference_image_urls: List[str] = Field(default=[], example=["url1", "url2"])

    # Extracted style information
    primary_style: VisualStyleType = Field(..., example=VisualStyleType.CARTOON)
    secondary_styles: List[VisualStyleType] = Field(default=[], example=[VisualStyleType.TWO_D])

    # Generated style prompts for image generation
    style_prompts: dict = Field(
        default={},
        example={
            "character_style": "in cartoon style with 2D flat colors and vibrant tones",
            "location_style": "in 2D cartoon environment style with exaggerated proportions",
            "color_palette": "vibrant primary colors with bold outlines"
        }
    )

    # Metadata
    color_description: Optional[str] = Field(None, example="Vibrant colors with bold outlines")
    artistic_elements: List[str] = Field(default=[], example=["bold_outlines", "flat_colors", "exaggerated_features"])
    technical_details: Optional[dict] = Field(None, example={"resolution": "high", "contrast": "high"})

    # Status and tracking
    status: VisualStyleStatus = Field(default=VisualStyleStatus.PENDING)
    analysis_error: Optional[str] = Field(None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system")
    is_active: bool = Field(default=True)

    # Usage tracking
    times_used: int = Field(default=0, description="Number of times this style has been applied")
    games_using_style: List[str] = Field(default=[], description="IDs of games using this style")

