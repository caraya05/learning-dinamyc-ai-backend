"""Integration utilities for applying visual styles to character and location generation"""
from visual_style.services import VisualStyleService
service = VisualStyleService()
async def get_character_style_prompts(visual_style_id: str, character_id: str) -> dict:
    """Get style prompts optimized for character generation"""
    return await service.apply_style_to_character(visual_style_id, character_id)
async def get_location_style_prompts(visual_style_id: str, location_id: str) -> dict:
    """Get style prompts optimized for location generation"""
    return await service.apply_style_to_location(visual_style_id, location_id)
def build_character_prompt_with_style(base_prompt: str, style_info: dict) -> str:
    """Build final prompt for character image generation with style"""
    style_part = style_info.get('character_style', '')
    color_part = style_info.get('color_palette', '')
    prompt = f"{base_prompt} {style_part}"
    if color_part:
        prompt += f", with {color_part}"
    return prompt.strip()
def build_location_prompt_with_style(base_prompt: str, style_info: dict) -> str:
    """Build final prompt for location image generation with style"""
    style_part = style_info.get('location_style', '')
    color_part = style_info.get('color_palette', '')
    prompt = f"{base_prompt} {style_part}"
    if color_part:
        prompt += f", with {color_part}"
    return prompt.strip()
