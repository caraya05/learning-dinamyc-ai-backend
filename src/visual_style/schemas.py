"""
Schemas for Visual Style module - Request/Response DTOs
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from bson import ObjectId
from pydantic import BaseModel, Field

from core.database import PyObjectId
from visual_style.enums import VisualStyleType, VisualStyleStatus


class ResponseModel(BaseModel):
    """Base response model with _id → id aliasing"""
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class SchemaCreateVisualStyle(BaseModel):
    """Schema for creating a new visual style"""
    name: str = Field(..., min_length=1, max_length=200, example="Fantasy Cartoon")
    description: Optional[str] = Field(None, max_length=500)
    original_prompt: str = Field(..., min_length=10, example="Create a cartoon style with vibrant colors")


class SchemaVisualStyleBase(ResponseModel):
    """Base schema for visual style responses"""
    name: str
    description: Optional[str]
    primary_style: VisualStyleType
    secondary_styles: List[VisualStyleType]
    color_description: Optional[str]
    status: VisualStyleStatus
    created_at: datetime
    times_used: int


class SchemaVisualStyleDetail(SchemaVisualStyleBase):
    """Detailed visual style response with all information"""
    original_prompt: str
    reference_image_urls: List[str]
    style_prompts: Dict[str, Any]
    artistic_elements: List[str]
    technical_details: Optional[dict]
    analysis_error: Optional[str]
    games_using_style: List[str]


class SchemaVisualStyleList(BaseModel):
    """List response for visual styles"""
    results: List[SchemaVisualStyleDetail]
    count: int
    page: int
    total_pages: int


class SchemaApplyVisualStyleToCharacter(BaseModel):
    """Schema for applying visual style to character generation"""
    character_id: str = Field(..., example="character_id")
    visual_style_id: str = Field(..., example="style_id")


class SchemaApplyVisualStyleToLocation(BaseModel):
    """Schema for applying visual style to location generation"""
    location_id: str = Field(..., example="location_id")
    visual_style_id: str = Field(..., example="style_id")


class SchemaAnalysisResult(BaseModel):
    """Result of visual style analysis"""
    visual_style_id: str
    primary_style: VisualStyleType
    secondary_styles: List[VisualStyleType]
    style_prompts: Dict[str, Any]
    artistic_elements: List[str]
    color_description: str
    technical_details: Optional[dict]
    status: VisualStyleStatus


class SchemaUpdateVisualStyle(BaseModel):
    """Schema for updating visual style"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class SchemaVisualStyleAnalysisResponse(BaseModel):
    """Structured response from GPT-4 Vision visual style analysis - MUST match OpenAI requirements"""
    primary_style: str = Field(..., description="Primary visual style type (cartoon, realistic, watercolor, pixel_art, 3d, volumetric, anime, abstract, flat, oil_painting, comic, or sketched)")
    character_style_prompt: str = Field(..., description="Detailed prompt in Spanish for DALL-E to generate characters in this style")
    location_style_prompt: str = Field(..., description="Detailed prompt in Spanish for DALL-E to generate locations in this style")
    event_style_prompt: str = Field(..., description="Detailed prompt in Spanish for DALL-E to generate events in this style")
    color_description: str = Field(..., description="Description of dominant colors and color palettes")
    secondary_styles: List[str] = Field(default_factory=list, description="Secondary style types that complement the primary style")
    color_palette: List[str] = Field(default_factory=list, description="List of hex colors (#RRGGBB) or color names from the palette")
    artistic_elements: List[str] = Field(default_factory=list, description="Artistic techniques and visual elements (e.g., bold outlines, flat colors)")
    is_animated: bool = Field(default=False, description="Whether the style is animated or not (true for cartoon, anime, etc.; false for realistic, oil_painting, watercolor)")
    style_name: str = Field(..., description="A concise, descriptive name for this specific style that matches the user's request (e.g., 'Old School B&W Cartoon', 'Realistic Oil Painting')")

    class Config:
        # Minimal config for OpenAI compatibility
        use_enum_values = True






