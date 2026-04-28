"""Utilities for integrating visual style into image generation prompts"""
import logging
from typing import Optional, Dict, Any
from bson import ObjectId
from core.database import db
from visual_style.enums import VisualStyleStatus

logger = logging.getLogger(__name__)


def _style_to_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()


def _normalize_text_list(values: Any) -> list[str]:
    if not values:
        return []

    normalized = []
    for item in values:
        text = _style_to_text(item)
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _build_shared_style_anchor(visual_style: Dict[str, Any]) -> str:
    style_prompts = visual_style.get("style_prompts", {}) or {}
    technical_details = visual_style.get("technical_details", {}) or {}

    style_name = _style_to_text(visual_style.get("style_name") or visual_style.get("name"))
    primary_style = _style_to_text(visual_style.get("primary_style"))
    secondary_styles = _normalize_text_list(visual_style.get("secondary_styles", []))
    color_palette = _style_to_text(
        style_prompts.get("color_palette") or visual_style.get("color_description") or ""
    )
    artistic_elements = _normalize_text_list(visual_style.get("artistic_elements", []))
    is_animated = bool(technical_details.get("is_animated", False))

    anchor_parts = [
        f"IDENTIDAD VISUAL UNIFICADA: {style_name or primary_style or 'estilo seleccionado'}.",
        f"Estilo base: {primary_style or 'coherente con la selección del usuario' }.",
    ]

    if secondary_styles:
        anchor_parts.append(f"Estilos secundarios permitidos: {', '.join(secondary_styles)}.")

    if color_palette:
        anchor_parts.append(f"Paleta cromática estable: {color_palette}.")

    if artistic_elements:
        anchor_parts.append(f"Elementos artísticos a preservar: {', '.join(artistic_elements)}.")

    anchor_parts.append(
        "Mantén contornos, grosor de línea, sombreado, iluminación, proporciones y nivel de detalle constantes entre personajes, locaciones y eventos."
    )
    anchor_parts.append(
        "No mezcles 2D con 3D, ni blanco y negro con color, ni cartoon con realista, salvo que el estilo maestro lo indique explícitamente."
    )
    anchor_parts.append(
        "Si el estilo maestro es animado, toda la serie visual debe verse animada de forma consistente; si no lo es, no introduzcas rasgos animados por accidente."
        if is_animated
        else "Mantén una lectura visual consistente y no introduzcas rasgos animados por accidente."
    )

    return " ".join(anchor_parts)


def _compose_consistent_prompt(visual_style: Dict[str, Any], base_prompt: str, domain: str) -> str:
    style_prompts = visual_style.get("style_prompts", {}) or {}
    shared_anchor = style_prompts.get("shared_style_anchor") or _build_shared_style_anchor(visual_style)

    domain_guidance = {
        "character": (
            "Para personajes: conserva silueta, vestuario, contorno y proporciones compatibles con el estilo maestro. "
            "Mantén el fondo transparente si el prompt base lo solicita."
        ),
        "location": (
            "Para locaciones: aplica la misma paleta, materialidad, iluminación y tratamiento visual del estilo maestro al entorno."
        ),
        "event": (
            "Para eventos: usa exactamente la misma identidad visual del universo del proyecto; no cambies a un lenguaje visual distinto."
        ),
    }.get(domain, "")

    domain_prompt = style_prompts.get(f"{domain}_style", "")
    fallback_prompt = ""
    if domain == "event":
        fallback_prompt = style_prompts.get("location_style") or style_prompts.get("character_style", "")

    prompt_sections = [
        shared_anchor,
        domain_guidance,
        f"Referencia de estilo para {domain}: {domain_prompt or fallback_prompt}" if (domain_prompt or fallback_prompt) else "",
        "El prompt base debe respetar este estilo maestro incluso si menciona otras preferencias secundarias.",
        base_prompt.strip(),
    ]

    return "\n".join(section for section in prompt_sections if section)


async def get_user_visual_style(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the user's selected visual style if available and completed.

    Args:
        user_id: User ID string

    Returns:
        Visual style document or None if not selected/completed
    """
    try:
        # Get user document
        user_doc = await db['user'].find_one({'_id': ObjectId(user_id)})
        if not user_doc:
            logger.warning(f"User not found: {user_id}")
            return None

        # Check if user has selected visual style
        selected_style_id = user_doc.get('selected_visual_style_id')
        if not selected_style_id:
            logger.debug(f"User {user_id} has no selected visual style")
            return None

        # Get visual style document
        visual_style = await db['visual_style'].find_one({
            '_id': ObjectId(selected_style_id),
            'is_active': True,
            'status': VisualStyleStatus.COMPLETED
        })

        if not visual_style:
            logger.warning(f"Visual style {selected_style_id} not found or not completed")
            return None

        return visual_style

    except Exception as e:
        logger.error(f"Error getting user visual style: {e}", exc_info=True)
        return None


async def get_character_style_prompt(user_id: str, base_prompt: str) -> str:
    """
    Enhance character image generation prompt with visual style if available.

    Args:
        user_id: User ID string
        base_prompt: Base prompt for character image generation

    Returns:
        Enhanced prompt with visual style, or original prompt if no style
    """
    try:
        visual_style = await get_user_visual_style(user_id)
        if not visual_style:
            return base_prompt

        enhanced_prompt = _compose_consistent_prompt(visual_style, base_prompt, "character")

        logger.info(f"Character prompt enhanced with visual style for user {user_id}")
        return enhanced_prompt

    except Exception as e:
        logger.error(f"Error enhancing character style prompt: {e}", exc_info=True)
        return base_prompt


async def get_location_style_prompt(user_id: str, base_prompt: str) -> str:
    """
    Enhance location image generation prompt with visual style if available.

    Args:
        user_id: User ID string
        base_prompt: Base prompt for location image generation

    Returns:
        Enhanced prompt with visual style, or original prompt if no style
    """
    try:
        visual_style = await get_user_visual_style(user_id)
        if not visual_style:
            return base_prompt

        enhanced_prompt = _compose_consistent_prompt(visual_style, base_prompt, "location")

        logger.info(f"Location prompt enhanced with visual style for user {user_id}")
        return enhanced_prompt

    except Exception as e:
        logger.error(f"Error enhancing location style prompt: {e}", exc_info=True)
        return base_prompt


async def get_event_style_prompt(user_id: str, base_prompt: str) -> str:
    """
    Enhance event image generation prompt with visual style if available.

    Args:
        user_id: User ID string
        base_prompt: Base prompt for event image generation

    Returns:
        Enhanced prompt with visual style, or original prompt if no style
    """
    try:
        visual_style = await get_user_visual_style(user_id)
        if not visual_style:
            return base_prompt

        enhanced_prompt = _compose_consistent_prompt(visual_style, base_prompt, "event")

        logger.info(f"Event prompt enhanced with visual style for user {user_id}")
        return enhanced_prompt

    except Exception as e:
        logger.error(f"Error enhancing event style prompt: {e}", exc_info=True)
        return base_prompt


async def get_style_metadata(user_id: str) -> Dict[str, Any]:
    """
    Get visual style metadata (is_animated, etc.) for image generation.

    Args:
        user_id: User ID string

    Returns:
        Dictionary with style metadata (is_animated, etc.)
    """
    try:
        visual_style = await get_user_visual_style(user_id)
        if not visual_style:
            return {'is_animated': False}

        technical_details = visual_style.get('technical_details', {})
        return {
            'is_animated': technical_details.get('is_animated', False),
            'primary_style': visual_style.get('primary_style'),
            'style_name': visual_style.get('style_name'),
            'artistic_elements': visual_style.get('artistic_elements', []),
            'shared_style_anchor': (visual_style.get('style_prompts', {}) or {}).get('shared_style_anchor')
                                    or _build_shared_style_anchor(visual_style)
        }

    except Exception as e:
        logger.error(f"Error getting style metadata: {e}", exc_info=True)
        return {'is_animated': False}

