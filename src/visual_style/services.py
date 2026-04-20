"""Services for Visual Style module"""
import logging
import json
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple
from bson import ObjectId
from fastapi import HTTPException
from core.database import db
from visual_style.enums import VisualStyleType, VisualStyleStatus

from gpt_ai.utils import openai_generator
from utils import upload_image
from uuid import uuid4
import base64
import httpx
from visual_style.schemas import SchemaVisualStyleAnalysisResponse

logger = logging.getLogger(__name__)


async def get_image_as_base64(image_url: str) -> tuple[str, str]:
    """Download image from URL and convert to base64

    Args:
        image_url: URL to download image from

    Returns:
        Tuple of (base64_string, mime_type)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url, timeout=30.0)
            response.raise_for_status()

            # Get MIME type from Content-Type header
            content_type = response.headers.get('content-type', 'image/jpeg').lower()
            # Extract just the mime type (e.g., 'image/jpeg' from 'image/jpeg; charset=utf-8')
            mime_type = content_type.split(';')[0].strip()

            # Convert to base64 using BytesIO buffer
            buffer = BytesIO()
            buffer.write(response.content)
            buffer.seek(0)
            base64_string = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return base64_string, mime_type
    except Exception as e:
        logger.error(f"Error downloading/encoding image {image_url}: {e}")
        raise


class VisualStyleService:
    """Service for visual styles"""

    def __init__(self, db_instance=None):
        self.db = db_instance or db

    async def create_visual_style(self, name: str, description: Optional[str],
                                  original_prompt: str, user_id: str) -> dict:
        """Create visual style"""
        doc = {
            'user_id': user_id,
            'name': name,
            'description': description,
            'original_prompt': original_prompt,
            'reference_image_urls': [],
            'primary_style': VisualStyleType.CARTOON,
            'secondary_styles': [],
            'style_prompts': {},
            'color_description': None,
            'artistic_elements': [],
            'technical_details': {},
            'status': VisualStyleStatus.PENDING,
            'analysis_error': None,
            'created_at': datetime.utcnow(),
            'created_by': user_id,
            'updated_at': datetime.utcnow(),
            'updated_by': user_id,
            'is_active': True,
            'times_used': 0,
            'games_using_style': [],
            # Task tracking fields
            'task_status': 'pending',
            'task_progress': 0,
            'task_message': '',
            'task_updated_at': datetime.utcnow()
        }
        result = await self.db['visual_style'].insert_one(doc)
        created_doc = await self.db['visual_style'].find_one({'_id': result.inserted_id})
        created_doc['_id'] = str(created_doc['_id'])
        return created_doc

    async def add_reference_images(self, visual_style_id: str, image_urls: List[str]) -> dict:
        """Add reference images"""
        if not ObjectId.is_valid(visual_style_id):
            raise HTTPException(status_code=400, detail="Invalid ID")
        current_doc = await self.db['visual_style'].find_one({'_id': ObjectId(visual_style_id)})
        if not current_doc:
            raise HTTPException(status_code=404, detail="Not found")
        current_urls = current_doc.get('reference_image_urls', [])
        new_urls = (current_urls + image_urls)[:5]
        updated_doc = await self.db['visual_style'].find_one_and_update(
            {'_id': ObjectId(visual_style_id)},
            {'$set': {'reference_image_urls': new_urls, 'updated_at': datetime.utcnow()}},
            return_document=True
        )
        updated_doc['_id'] = str(updated_doc['_id'])
        return updated_doc

    async def get_visual_style(self, visual_style_id: str) -> dict:
        """Get by ID"""
        if not ObjectId.is_valid(visual_style_id):
            raise HTTPException(status_code=400, detail="Invalid ID")
        vs = await self.db['visual_style'].find_one({'_id': ObjectId(visual_style_id)})
        if not vs:
            raise HTTPException(status_code=404, detail="Not found")
        vs['_id'] = str(vs['_id'])
        return vs

    async def get_user_visual_styles(self, user_id: str, skip: int = 0,
                                     limit: int = 10) -> Tuple[List[dict], int]:
        """Get user styles"""
        total = await self.db['visual_style'].count_documents({'created_by': user_id, 'is_active': True})
        styles = await self.db['visual_style'].find(
            {'created_by': user_id, 'is_active': True}
        ).sort('updated_at', -1).skip(skip).limit(limit).to_list(None)
        for s in styles:
            s['_id'] = str(s['_id'])
        return styles, total

    async def get_user_completed_visual_styles(self, user_id: str, skip: int = 0,
                                               limit: int = 10) -> Tuple[List[dict], int]:
        """Get only completed user styles, ordered by updated_at"""
        total = await self.db['visual_style'].count_documents(
            {'created_by': user_id, 'is_active': True, 'status': VisualStyleStatus.COMPLETED}
        )
        styles = await self.db['visual_style'].find(
            {'created_by': user_id, 'is_active': True, 'status': VisualStyleStatus.COMPLETED}
        ).sort('updated_at', -1).skip(skip).limit(limit).to_list(None)
        for s in styles:
            s['_id'] = str(s['_id'])
        return styles, total

    async def delete_visual_style(self, visual_style_id: str) -> bool:
        """Soft delete"""
        if not ObjectId.is_valid(visual_style_id):
            raise HTTPException(status_code=400, detail="Invalid ID")
        result = await self.db['visual_style'].update_one(
            {'_id': ObjectId(visual_style_id)},
            {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def apply_style_to_character(self, visual_style_id: str, character_id: str) -> Dict[str, str]:
        """Apply to character"""
        if not ObjectId.is_valid(visual_style_id):
            raise HTTPException(status_code=400, detail="Invalid ID")
        vs = await self.get_visual_style(visual_style_id)
        if vs['status'] != VisualStyleStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Not analyzed")
        await self.db['visual_style'].update_one(
            {'_id': ObjectId(visual_style_id)},
            {'$inc': {'times_used': 1}, '$addToSet': {'games_using_style': character_id}}
        )
        return {
            'style_id': visual_style_id,
            'character_style': vs.get('style_prompts', {}).get('character_style', ''),
            'color_palette': vs.get('style_prompts', {}).get('color_palette', ''),
            'primary_style': vs.get('primary_style', '')
        }

    async def apply_style_to_location(self, visual_style_id: str, location_id: str) -> Dict[str, str]:
        """Apply to location"""
        if not ObjectId.is_valid(visual_style_id):
            raise HTTPException(status_code=400, detail="Invalid ID")
        vs = await self.get_visual_style(visual_style_id)
        if vs['status'] != VisualStyleStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Not analyzed")
        await self.db['visual_style'].update_one(
            {'_id': ObjectId(visual_style_id)},
            {'$inc': {'times_used': 1}, '$addToSet': {'games_using_style': location_id}}
        )
        return {
            'style_id': visual_style_id,
            'location_style': vs.get('style_prompts', {}).get('location_style', ''),
            'color_palette': vs.get('style_prompts', {}).get('color_palette', ''),
            'primary_style': vs.get('primary_style', '')
        }

    async def analyze_visual_style(self, visual_style_id: str, user_id: str) -> dict:
        """Analyze visual style using GPT-4 Vision

        This method:
        1. Retrieves the style document and reference images
        2. Calls GPT-4 Vision API to analyze the images
        3. Extracts visual style type, colors, techniques
        4. Generates optimized prompts for DALL-E
        5. Updates the database with analysis results

        Args:
            visual_style_id: String ID of visual style
            user_id: String ID of user

        Returns:
            dict with analysis results
        """
        try:
            print(f"\n{'='*70}")
            print(f"🔍 ANALYZE VISUAL STYLE - START")
            print(f"{'='*70}")
            print(f"📝 Style ID: {visual_style_id}")
            print(f"👤 User ID: {user_id}")

            # Validate and retrieve document
            if not ObjectId.is_valid(visual_style_id):
                print(f"❌ Invalid ObjectId: {visual_style_id}")
                raise HTTPException(status_code=400, detail="Invalid ID")

            print(f"✅ Valid ObjectId")
            print(f"🔄 Fetching style from database...")

            vs = await self.db['visual_style'].find_one({'_id': ObjectId(visual_style_id)})
            if not vs:
                print(f"❌ Style not found in database")
                raise HTTPException(status_code=404, detail="Not found")

            print(f"✅ Style found: {vs.get('name', 'Unknown')}")

            # Check if has reference images
            images = vs.get('reference_image_urls', [])
            print(f"📸 Reference images count: {len(images)}")

            # Validate image formats - GPT-4 Vision only supports: png, jpeg, gif, webp
            valid_formats = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            valid_images = []

            if len(images) > 0:
                for idx, img in enumerate(images, 1):
                    print(f"   - Image {idx}: {img[:60]}...")
                    # Check if image has valid format
                    img_lower = img.lower()
                    if any(img_lower.endswith(fmt) for fmt in valid_formats):
                        valid_images.append(img)
                        print(f"      ✅ Valid format")
                    else:
                        print(f"      ⚠️ Invalid format (not in {valid_formats})")

            if len(valid_images) > 0:
                print(f"✅ Valid images to process: {len(valid_images)}/{len(images)}")
            else:
                print(f"ℹ️ No reference images or all images have invalid formats - will analyze using description only")

            logger.info(f"Starting analysis for style {visual_style_id}")
            print(f"\n🚀 ANALYSIS IN PROGRESS...")

            # ============================================================
            # PASO 1: Analizar imagen con visión para extraer descripción
            # ============================================================
            print(f"📤 STEP 1: Analyzing visual style...")

            # Build content prompt for image analysis
            analysis_prompt = [
                {
                    "role": "system",
                    "content": """You are an expert visual style analyzer. Analyze the provided reference images very carefully and extract:
1. Primary visual style type (e.g., cartoon, realistic, watercolor, pixel_art, 3d, anime, abstract, volumetric, etc.)
2. Secondary style types that complement the primary style
3. Dominant color palette with specific hex colors or detailed color names
4. Artistic techniques and elements used (e.g., bold outlines, flat colors, cell shading, realistic lighting, etc.)
5. Technical details about rendering (resolution, quality, rendering style)

Provide a detailed, comprehensive analysis that captures the essence of the visual style."""
                }
            ]

            # Prepare user content - start with analysis request
            user_content = [
                {
                    "type": "text",
                    "text": f"Please analyze this visual style based on the following description:\n\n{vs.get('description', vs.get('original_prompt', 'Visual style to analyze'))}\n\nProvide a comprehensive analysis of the visual elements, colors, techniques, and style characteristics."
                }
            ]

            # Download images and add as base64 if available
            if len(valid_images) > 0:
                print(f"📸 Found {len(valid_images)} reference images to analyze")
                valid_count = 0
                for idx, image_url in enumerate(valid_images, 1):
                    print(f"   📸 Processing image {idx}/{len(valid_images)}: {image_url[:60]}...")
                    try:
                        # Download and convert to base64
                        base64_string, mime_type = await get_image_as_base64(image_url)

                        # Determine the media type for the data URI
                        if 'png' in mime_type.lower():
                            media_type = 'image/png'
                        elif 'gif' in mime_type.lower():
                            media_type = 'image/gif'
                        elif 'webp' in mime_type.lower():
                            media_type = 'image/webp'
                        else:
                            media_type = 'image/jpeg'  # Default to JPEG

                        data_uri = f"data:{media_type};base64,{base64_string}"

                        # Add image to user content
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri,
                                "detail": "high"
                            }
                        })
                        valid_count += 1
                        print(f"      ✅ Downloaded and encoded as base64 ({len(base64_string)} chars)")

                    except Exception as e:
                        print(f"      ❌ Failed to process image: {str(e)}")
                        logger.warning(f"Failed to process image {image_url}: {e}")
                        continue

                if valid_count > 0:
                    print(f"✅ Processed {valid_count} images")
                else:
                    print(f"⚠️ No images could be downloaded, analysis will use description only")
            else:
                print(f"ℹ️ No reference images provided, analysis will use description only")

            # Add user message to prompt
            analysis_prompt.append({
                "role": "user",
                "content": user_content
            })

            print(f"⏳ Waiting for GPT-4 Vision analysis...")

            # Call GPT-4 Vision to analyze images and get text description
            analysis_text = await openai_generator.generate_gpt(
                content_prompt=analysis_prompt,
                model="gpt-4o",
                user_id=user_id,
                type_generation="visual_style_analysis_step1",
                vision=True,
                max_tokens=2000
            )

            # Check if analysis_text is an HTTPException
            if isinstance(analysis_text, HTTPException):
                print(f"❌ GPT-4 Vision returned error")
                # Extract error message to see what went wrong
                error_msg = str(analysis_text.detail) if hasattr(analysis_text, 'detail') else str(analysis_text)
                print(f"   Error details: {error_msg}")

                # If it's an image format error, provide helpful message
                if "invalid_image_format" in error_msg.lower() or "unsupported image" in error_msg.lower():
                    print(f"   ⚠️ One or more images may have corrupted format or be inaccessible")
                    print(f"   ℹ️ Make sure image URLs are publicly accessible and return correct MIME types")
                    raise HTTPException(
                        status_code=400,
                        detail="Image format error from OpenAI. Check that all image URLs are publicly accessible and valid."
                    )
                else:
                    raise analysis_text
            elif analysis_text is None:
                print(f"❌ GPT-4 Vision returned None")
                raise HTTPException(status_code=500, detail="GPT-4 Vision analysis returned no response")

            print(f"✅ Analysis received from GPT-4 Vision!")
            print(f"📝 Analysis text preview: {analysis_text[:300]}...")

            # ============================================================
            # PASO 2: Procesar análisis para generar JSON estructurado
            # ============================================================
            print(f"\n🚀 STEP 2: Generating structured analysis...")

            generation_prompt = [
                {
                    "role": "system",
                    "content": """You are an expert visual style analyzer. Based on the provided image analysis AND the ORIGINAL USER REQUEST, generate a structured JSON response 
with detailed visual style information. Include specific hex colors, detailed prompts for DALL-E, and all artistic elements detected.

CRITICAL REQUIREMENTS:
1. Respect the original user description - if they said "black and white animated cartoon", ensure is_animated=true, colors reflect B&W, style reflects old cartoon
2. Create a descriptive style_name that captures the essence of what the user asked for
3. Set is_animated to true for: cartoon, anime, manga, animated, motion, moving, animation styles
4. Provide accurate color values in hex format (#RRGGBB) and create character/location prompts that capture the essence of the style for DALL-E image generation.
5. Make character and location prompts VERY SPECIFIC about animation style, colors, and techniques mentioned by user"""
                },
                {
                    "role": "user",
                    "content": f"""Based on this visual style analysis AND considering the original user request below, generate a comprehensive structured response:

ORIGINAL USER REQUEST:
{vs.get('original_prompt', 'No original request')}

USER DESCRIPTION:
{vs.get('description', vs.get('original_prompt', 'Visual style to analyze'))}

VISUAL ANALYSIS:
{analysis_text}

Please ensure:
1. primary_style is ONE of: cartoon, 2d, realistic, watercolor, pixel_art, 3d, volumetric, anime, abstract, flat, oil_painting, comic, sketched
2. is_animated is TRUE if: cartoon, anime, manga, animation, motion, or user mentioned "animated"
3. style_name captures the ESSENCE of user request (e.g., if user said "black and white old cartoon" → "Old School B&W Cartoon")
4. character_style_prompt is detailed and MUST include animation style, color constraints, and specific techniques
5. location_style_prompt is detailed and MUST include animation style, color constraints, and environment techniques
6. All prompts should be in Spanish and include specific style details, colors, animation status, and techniques
7. color_palette must include actual hex colors or specific color names mentioned in user request (if "black and white" then use #000000, #FFFFFF, #808080)"""
                }
            ]

            print(f"📤 Generating structured JSON...")
            print(f"⏳ Waiting for response with response_format...")

            # Call GPT to generate structured JSON
            structured_response = await openai_generator.generate_gpt(
                content_prompt=generation_prompt,
                model="gpt-4o-mini",
                user_id=user_id,
                type_generation="visual_style_analysis_step2",
                response_format=SchemaVisualStyleAnalysisResponse,
                max_tokens=4096
            )

            # Check if structured_response is an HTTPException
            if isinstance(structured_response, HTTPException):
                print(f"❌ GPT-4o-mini returned error")
                error_msg = str(structured_response.detail) if hasattr(structured_response, 'detail') else str(structured_response)
                print(f"   Error details: {error_msg}")
                raise structured_response
            elif structured_response is None:
                print(f"❌ GPT-4o-mini returned None")
                raise HTTPException(status_code=500, detail="Structured response generation failed")

            print(f"✅ Structured analysis generated!")
            print(f"   - Primary Style: {structured_response.primary_style}")
            print(f"   - Secondary Styles: {structured_response.secondary_styles}")
            print(f"   - Color Palette: {structured_response.color_palette}")
            print(f"   - Is Animated: {structured_response.is_animated}")
            print(f"   - Style Name: {structured_response.style_name}")
            print(f"   - Artistic Elements: {structured_response.artistic_elements}")

            # Map styles to enum values
            primary_style_str = structured_response.primary_style.lower()
            style_mapping = {
                'cartoon': VisualStyleType.CARTOON,
                '2d': VisualStyleType.TWO_D,
                'realistic': VisualStyleType.REALISTIC,
                'watercolor': VisualStyleType.WATERCOLOR,
                'pixel_art': VisualStyleType.PIXEL_ART,
                'pixel': VisualStyleType.PIXEL_ART,
                '3d': VisualStyleType.THREE_D,
                'three_d': VisualStyleType.THREE_D,
                'volumetric': VisualStyleType.VOLUMETRIC,
                'anime': VisualStyleType.ANIME,
                'manga': VisualStyleType.ANIME,
                'abstract': VisualStyleType.FLAT,
                'flat': VisualStyleType.FLAT,
                'oil_painting': VisualStyleType.OIL_PAINTING,
                'oil': VisualStyleType.OIL_PAINTING,
                'comic': VisualStyleType.COMIC,
                'sketched': VisualStyleType.SKETCHED,
            }
            primary_style = style_mapping.get(primary_style_str, VisualStyleType.CARTOON)

            secondary_styles_list = []
            if structured_response.secondary_styles:
                for style in structured_response.secondary_styles:
                    style_lower = style.lower()
                    if style_lower in style_mapping:
                        secondary_styles_list.append(style_mapping[style_lower])

            analysis_result = {
                'primary_style': primary_style,
                'secondary_styles': secondary_styles_list,
                'is_animated': structured_response.is_animated,
                'style_name': structured_response.style_name,
                'style_prompts': {
                    'character_style': structured_response.character_style_prompt,
                    'location_style': structured_response.location_style_prompt,
                    'color_palette': ', '.join(structured_response.color_palette) if structured_response.color_palette else structured_response.color_description
                },
                'color_description': structured_response.color_description,
                'artistic_elements': structured_response.artistic_elements or [],
                'technical_details': {
                    'is_animated': structured_response.is_animated
                }
            }

            print(f"✅ Analysis mapping completed!")

            # Update document with analysis
            update_data = {
                **analysis_result,
                'status': VisualStyleStatus.COMPLETED,
                'updated_at': datetime.utcnow(),
                'updated_by': user_id
            }

            print(f"\n💾 Updating database...")

            updated_doc = await self.db['visual_style'].find_one_and_update(
                {'_id': ObjectId(visual_style_id)},
                {'$set': update_data},
                return_document=True
            )

            print(f"✅ Database updated!")
            print(f"📊 New status: {updated_doc.get('status')}")

            updated_doc['_id'] = str(updated_doc['_id'])
            logger.info(f"Analysis completed for style {visual_style_id}")

            print(f"\n✨ ANALYSIS COMPLETE!")
            print(f"{'='*70}\n")

            return updated_doc

        except HTTPException:
            print(f"❌ HTTP Exception occurred")
            raise
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            logger.error(f"Error analyzing style {visual_style_id}: {e}", exc_info=True)
            # Update with error status
            await self.db['visual_style'].update_one(
                {'_id': ObjectId(visual_style_id)},
                {'$set': {
                    'status': VisualStyleStatus.FAILED,
                    'analysis_error': str(e),
                    'updated_at': datetime.utcnow()
                }}
            )
            print(f"📊 Status updated to FAILED")
            print(f"❌ Error saved to database")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    async def generate_character_image_with_style(self, character_prompt: str, character_genre: str,
                                                  style_prompts: dict, user_id: str,
                                                  is_animated: bool = False) -> dict:
        """Generate character image using visual style

        Args:
            character_prompt: Description of the character
            character_genre: Character genre/type
            style_prompts: Visual style information (character_style, color_palette)
            user_id: User ID for tracking
            is_animated: Whether the style is animated

        Returns:
            dict with image_url and success status
        """
        try:
            print(f"\n{'=' * 70}")
            print(f"🎨 GENERATE CHARACTER IMAGE WITH STYLE")
            print(f"{'=' * 70}")

            character_style = style_prompts.get('character_style', '')
            color_palette = style_prompts.get('color_palette', '')

            # Add animation instruction if needed
            animation_instruction = "ESTILO ANIMADO: " if is_animated else "ESTILO ESTÁTICO/REALISTA: "

            prompt = (
                f"{animation_instruction}Genera una imagen en vista frontal cuadrada de 1024x1024 de un personaje, "
                f"({character_prompt}) {character_style}, "
                f"de la cintura para arriba mirando al frente con los brazos hacia abajo, "
                f"con fondo transparente, colores a usar: {color_palette}, "
                f"genero: {character_genre}"
            )

            print(f"📤 Generating character image...")
            print(f"   Animation: {'Yes' if is_animated else 'No'}")

            image_face = await openai_generator.generate_image(
                prompt=prompt,
                size="1024x1024",
                user_id=user_id,
                model="gpt-image-1",
                style=None,
                type_generation="character_face",
                background="transparent"
            )

            # Check if image_face is an HTTPException
            if isinstance(image_face, HTTPException):
                print(f"❌ Image generation returned error")
                error_msg = str(image_face.detail) if hasattr(image_face, 'detail') else str(image_face)
                print(f"   Error details: {error_msg}")
                raise image_face
            elif image_face is None:
                print(f"❌ Image generation returned None")
                raise HTTPException(status_code=500, detail="Character image generation returned no response")

            print(f"✅ Character image generated!")
            image_bytes = base64.b64decode(image_face)

            print(f"📤 Uploading to Digital Ocean...")
            image_generated = upload_image(
                img_byte_arr=image_bytes,
                file_name=f"characters/{uuid4()}.jpg",
                size=(512, 512),
            )

            print(f"✅ Character image uploaded!")
            return {"image_url": image_generated, "success": True}

        except Exception as e:
            print(f"❌ Error generating character image: {str(e)}")
            logger.error(f"Error generating character image: {e}", exc_info=True)
            return {"image_url": None, "success": False, "error": str(e)}

    async def generate_location_image_with_style(self, location_prompt: str,
                                                 style_prompts: dict, user_id: str,
                                                 personajes: List[dict] = None,
                                                 is_animated: bool = False) -> dict:
        """Generate location image using visual style with character images

        Args:
            location_prompt: Description of the location
            style_prompts: Visual style information (location_style, color_palette)
            user_id: User ID for tracking
            personajes: Optional list of character documents with image data
            is_animated: Whether the style is animated

        Returns:
            dict with image_url and success status
        """
        try:
            print(f"\n{'=' * 70}")
            print(f"🏢 GENERATE LOCATION IMAGE WITH STYLE")
            print(f"{'=' * 70}")

            location_style = style_prompts.get('location_style', '')
            color_palette = style_prompts.get('color_palette', '')

            # Add animation instruction if needed
            animation_instruction = "ESTILO ANIMADO: " if is_animated else "ESTILO ESTÁTICO/REALISTA: "

            # Build content prompt
            content_prompt = [
                {
                    "role": "user",
                    "content": []
                }
            ]

            # Build text instruction with character info
            personajes_info = []
            personajes_images = []

            if personajes:
                print(f"📸 Processing {len(personajes)} characters...")
                for idx, personaje in enumerate(personajes, 1):
                    # Handle both nested (data) and flat structures
                    data = personaje.get('data', personaje)
                    nombre = data.get('name', 'Personaje')
                    prompt_personaje = data.get('prompt_user', '') or data.get('prompt', '')
                    imagen = data.get('image') or data.get('image_reference')

                    if prompt_personaje:
                        personajes_info.append(f"{nombre}: {prompt_personaje}")
                        print(f"   ✅ Character {idx}: {nombre}")

                    # Download and add character image
                    if imagen:
                        print(f"      📥 Downloading image: {imagen[:50]}...")
                        try:
                            base64_string, mime_type = await get_image_as_base64(imagen)

                            # Determine media type
                            if 'png' in mime_type.lower():
                                media_type = 'image/png'
                            elif 'gif' in mime_type.lower():
                                media_type = 'image/gif'
                            elif 'webp' in mime_type.lower():
                                media_type = 'image/webp'
                            else:
                                media_type = 'image/jpeg'

                            data_uri = f"data:{media_type};base64,{base64_string}"
                            personajes_images.append(data_uri)
                            print(f"      ✅ Image converted to base64 ({len(base64_string)} chars)")

                        except Exception as e:
                            print(f"      ⚠️ Failed to download image: {str(e)}")
                            logger.warning(f"Failed to download character image {imagen}: {e}")
                            continue

            # Build main text instruction with animation status
            text_instruction = f"""{animation_instruction}Genera una imagen en vista isométrica, {location_style}, detallada y resolución wide.
            
Descripción de ubicación: {location_prompt}
Colores: {color_palette}"""

            if personajes_info:
                text_instruction += f"\n\nPersonajes en la escena:\n" + "\n".join(personajes_info)
                text_instruction += "\n\nColoca los personajes provistos en esta ubicación de forma natural y contextual."

            # Add text instruction
            content_prompt[0]["content"].append({
                "type": "input_text",
                "text": text_instruction
            })

            # Add character images as base64
            for idx, data_uri in enumerate(personajes_images, 1):
                print(f"   📍 Adding character image {idx} to prompt...")
                content_prompt[0]["content"].append({
                    "type": "input_image",
                    "image_url":  data_uri
                })

            if personajes_images:
                print(f"✅ {len(personajes_images)} character images included in prompt")

            print(f"📤 Generating location image...")
            print(f"   Animation: {'Yes' if is_animated else 'No'}")

            image_location = await openai_generator.generate_gpt(
                content_prompt=content_prompt,
                model="gpt-4o",
                user_id=user_id,
                type_generation="location_image_with_style",
                image=True,
                tools=[{"type": "image_generation", "size": "1536x1024", "quality": "high"}]
            )

            # Check if image_location is an HTTPException
            if isinstance(image_location, HTTPException):
                print(f"❌ GPT-4 returned error")
                error_msg = str(image_location.detail) if hasattr(image_location, 'detail') else str(image_location)
                print(f"   Error details: {error_msg}")
                raise image_location
            elif image_location is None:
                print(f"❌ GPT-4 returned None")
                raise HTTPException(status_code=500, detail="Location image generation returned no response")

            print(f"✅ Location image generated!")
            image_data = base64.b64decode(image_location)
            image_file = BytesIO(image_data)

            print(f"📤 Uploading to Digital Ocean...")
            image_generated = upload_image(
                img_byte_arr=image_file,
                file_name=f"locations/{uuid4()}.jpg",
                size=(2436, 1372),
            )

            print(f"✅ Location image uploaded!")
            return {"image_url": image_generated, "success": True}

        except Exception as e:
            print(f"❌ Error generating location image: {str(e)}")
            logger.error(f"Error generating location image: {e}", exc_info=True)
            return {"image_url": None, "success": False, "error": str(e)}

    async def save_generated_images(self, visual_style_id: str, character_image_url: str,
                                    location_image_url: str, user_id: str) -> dict:
        """Save generated character and location images to visual style document

        Args:
            visual_style_id: String ID of visual style
            character_image_url: URL of generated character image
            location_image_url: URL of generated location image
            user_id: String ID of user

        Returns:
            Updated document with saved image URLs
        """
        try:
            print(f"\n{'=' * 70}")
            print(f"💾 SAVE GENERATED IMAGES")
            print(f"{'=' * 70}")
            print(f"📝 Style ID: {visual_style_id}")
            print(f"👤 User ID: {user_id}")

            # Validate ID
            if not ObjectId.is_valid(visual_style_id):
                print(f"❌ Invalid ObjectId: {visual_style_id}")
                raise HTTPException(status_code=400, detail="Invalid ID")

            # Check if document exists
            vs = await self.db['visual_style'].find_one({'_id': ObjectId(visual_style_id)})
            if not vs:
                print(f"❌ Visual style not found")
                raise HTTPException(status_code=404, detail="Visual style not found")

            print(f"✅ Visual style found: {vs.get('name', 'Unknown')}")

            # Prepare update data
            generated_images = {
                'character_image_url': character_image_url,
                'location_image_url': location_image_url,
                'generated_at': datetime.utcnow()
            }

            print(f"📤 Saving character image URL: {character_image_url[:60]}...")
            print(f"📤 Saving location image URL: {location_image_url[:60]}...")

            # Update document with generated images
            updated_doc = await self.db['visual_style'].find_one_and_update(
                {'_id': ObjectId(visual_style_id)},
                {
                    '$set': {
                        'generated_images': generated_images,
                        'updated_at': datetime.utcnow(),
                        'updated_by': user_id
                    }
                },
                return_document=True
            )

            print(f"✅ Images saved to database!")
            print(f"📊 Generated images field updated")

            # Convert ObjectId to string for JSON response
            updated_doc['_id'] = str(updated_doc['_id'])
            logger.info(f"Saved generated images for style {visual_style_id}")

            print(f"\n✨ SAVE COMPLETE!")
            print(f"{'=' * 70}\n")

            return updated_doc

        except HTTPException:
            print(f"❌ HTTP Exception occurred")
            raise
        except Exception as e:
            print(f"❌ Error saving generated images: {str(e)}")
            logger.error(f"Error saving generated images for style {visual_style_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to save images: {str(e)}")

    async def update_visual_style(self, visual_style_id: str, updates: dict) -> dict:
        """Update visual style fields

        Args:
            visual_style_id: String ID of visual style
            updates: Dictionary with fields to update
                Allowed fields: name, description, original_prompt

        Returns:
            Updated document
        """
        if not ObjectId.is_valid(visual_style_id):
            raise HTTPException(status_code=400, detail="Invalid ID")

        # Only allow specific fields to be updated
        allowed_fields = ['name', 'description', 'original_prompt']
        update_data = {}

        for field in allowed_fields:
            if field in updates and updates[field] is not None:
                update_data[field] = updates[field]

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Add metadata
        update_data['updated_at'] = datetime.utcnow()

        updated_doc = await self.db['visual_style'].find_one_and_update(
            {'_id': ObjectId(visual_style_id)},
            {'$set': update_data},
            return_document=True
        )

        if not updated_doc:
            raise HTTPException(status_code=404, detail="Visual style not found")

        updated_doc['_id'] = str(updated_doc['_id'])
        return updated_doc

    async def select_user_visual_style(self, user_id: str, visual_style_id: str) -> dict:
        """Select a visual style for user

        Args:
            user_id: User ID
            visual_style_id: Visual style ID to select

        Returns:
            Updated user document
        """
        try:
            print(f"\n{'='*70}")
            print(f"🎨 SELECT USER VISUAL STYLE")
            print(f"{'='*70}")
            print(f"👤 User ID: {user_id}")
            print(f"🎨 Style ID: {visual_style_id}")

            # Validate visual style exists and is completed
            if not ObjectId.is_valid(visual_style_id):
                raise HTTPException(status_code=400, detail="Invalid style ID")

            vs = await self.db['visual_style'].find_one({'_id': ObjectId(visual_style_id)})
            if not vs:
                raise HTTPException(status_code=404, detail="Visual style not found")

            if vs.get('status') != VisualStyleStatus.COMPLETED:
                raise HTTPException(status_code=400, detail="Visual style not completed yet")

            print(f"✅ Visual style found: {vs.get('name')}")

            # Update visual style with updated_at timestamp
            print(f"📤 Updating visual style updated_at...")
            await self.db['visual_style'].update_one(
                {'_id': ObjectId(visual_style_id)},
                {'$set': {'updated_at': datetime.utcnow()}}
            )
            print(f"✅ Visual style updated_at timestamp updated!")

            # Update user with selected visual style
            print(f"📤 Updating user profile...")
            user_update = await self.db['user'].find_one_and_update(
                {'_id': ObjectId(user_id)},
                {'$set': {'selected_visual_style_id': visual_style_id}},
                return_document=True
            )

            if not user_update:
                raise HTTPException(status_code=404, detail="User not found")

            print(f"✅ Visual style selected successfully!")
            print(f"{'='*70}\n")

            return {
                'user_id': str(user_update.get('_id')),
                'selected_visual_style_id': visual_style_id,
                'style_name': vs.get('name'),
                'message': 'Visual style selected successfully'
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error selecting visual style: {e}")
            logger.error(f"Error selecting visual style: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error selecting visual style: {str(e)}")

    async def get_user_selected_visual_style(self, user_id: str) -> dict:
        """Get selected visual style for user

        Args:
            user_id: User ID

        Returns:
            Selected visual style or empty dict if none selected
        """
        try:
            print(f"\n{'='*70}")
            print(f"🎨 GET USER SELECTED VISUAL STYLE")
            print(f"{'='*70}")
            print(f"👤 User ID: {user_id}")

            # Get user
            user = await self.db['user'].find_one({'_id': ObjectId(user_id)})
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            selected_style_id = user.get('selected_visual_style_id')

            if not selected_style_id:
                print(f"ℹ️ No visual style selected")
                print(f"{'='*70}\n")
                return {'selected_visual_style_id': None}

            # Get visual style
            vs = await self.db['visual_style'].find_one({'_id': ObjectId(selected_style_id)})

            if not vs:
                print(f"⚠️ Selected style not found, clearing selection")
                # Clear invalid selection
                await self.db['user'].update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'selected_visual_style_id': None}}
                )
                return {'selected_visual_style_id': None}

            vs['_id'] = str(vs['_id'])

            print(f"✅ Selected style found: {vs.get('name')}")
            print(f"{'='*70}\n")

            return vs

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error getting selected visual style: {e}")
            logger.error(f"Error getting selected visual style: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error getting selected visual style: {str(e)}")

    async def clear_user_visual_style_selection(self, user_id: str) -> dict:
        """Clear selected visual style for user

        Args:
            user_id: User ID

        Returns:
            Confirmation dict
        """
        try:
            print(f"\n{'='*70}")
            print(f"🗑️ CLEAR USER VISUAL STYLE SELECTION")
            print(f"{'='*70}")
            print(f"👤 User ID: {user_id}")

            # Update user to clear selection
            result = await self.db['user'].update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'selected_visual_style_id': None}}
            )

            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="User not found")

            print(f"✅ Visual style selection cleared!")
            print(f"{'='*70}\n")

            return {'cleared': True, 'message': 'Visual style selection cleared'}

        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error clearing visual style selection: {e}")
            logger.error(f"Error clearing visual style selection: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error clearing selection: {str(e)}")
