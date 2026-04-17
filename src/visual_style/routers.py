"""Routers for Visual Style module"""
import logging
from fastapi import APIRouter, Depends, status, Form, File, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from auth.auth import auth
from auth.utils import auth_schema
from utils import upload_file
from visual_style.services import VisualStyleService
from celery_worker import celery

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visual-style", tags=["Visual Style"])


def get_visual_style_service():
    return VisualStyleService()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_visual_style(
        name: str = Form(..., min_length=1, max_length=200),
        description: str = Form(None),
        prompt: str = Form(..., min_length=10),
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Create a new visual style"""
    try:
        print(f"\n{'='*70}")
        print(f"📝 CREATE VISUAL STYLE")
        print(f"{'='*70}")
        print(f"👤 User ID: {user.get('_id')}")
        print(f"📝 Name: {name}")
        print(f"📄 Prompt: {prompt[:50]}...")

        user_id = str(user.get("_id"))
        vs = await service.create_visual_style(name, description, prompt, user_id)

        print(f"✅ Style created successfully!")
        print(f"📊 Style ID: {vs.get('_id')}")
        print(f"📊 Status: {vs.get('status')}")
        print(f"{'='*70}\n")

        return vs
    except Exception as e:
        print(f"❌ Error creating visual style: {e}")
        logger.error(f"Error creating visual style: {e}")
        raise


@router.post("/{style_id}/upload-reference-images", status_code=status.HTTP_200_OK)
async def upload_reference_images(
        style_id: str,
        images: list[UploadFile] = File(...),
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Upload reference images"""
    try:
        print(f"\n{'='*70}")
        print(f"📸 UPLOAD REFERENCE IMAGES")
        print(f"{'='*70}")
        print(f"📝 Style ID: {style_id}")
        print(f"📸 Number of images: {len(images)}")

        # Validate image formats - GPT-4 Vision only supports: png, jpeg, gif, webp
        valid_formats = ('.png', '.jpg', '.jpeg', '.gif', '.webp')

        image_urls = []
        for idx, img in enumerate(images[:5], 1):
            print(f"   📤 Uploading image {idx}...")

            # Check file extension
            if img.filename:
                filename_lower = img.filename.lower()
                if not any(filename_lower.endswith(fmt) for fmt in valid_formats):
                    print(f"      ⚠️ Skipping unsupported format: {img.filename}")
                    print(f"         Supported formats: png, jpg, jpeg, gif, webp")
                    continue

            url = upload_file(img)
            image_urls.append(url)
            print(f"      ✅ Uploaded: {url[:60]}...")

        if not image_urls:
            print(f"❌ No valid images to upload")
            logger.error("No valid images provided for upload")
            raise HTTPException(status_code=400, detail="No valid images with supported formats (png, jpg, jpeg, gif, webp)")

        print(f"\n💾 Saving to database...")
        result = await service.add_reference_images(style_id, image_urls)

        print(f"✅ Images uploaded successfully!")
        print(f"📊 Status: {result.get('status')}")
        print(f"{'='*70}\n")

        return result
    except Exception as e:
        print(f"❌ Error uploading images: {e}")
        logger.error(f"Error uploading images: {e}")
        raise


@router.post("/{style_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_visual_style(
        style_id: str,
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Trigger visual style analysis (async)"""
    try:
        print(f"\n{'='*70}")
        print(f"🔍 TRIGGER ANALYSIS")
        print(f"{'='*70}")
        print(f"📝 Style ID: {style_id}")
        print(f"👤 User ID: {user.get('_id')}")

        user_id = str(user.get("_id"))

        print(f"\n📤 Sending task to Celery...")
        task_result = celery.send_task('analyze_visual_style_task', args=[style_id, user_id])

        print(f"✅ Task sent to Celery!")
        print(f"📋 Task ID: {task_result.id}")
        print(f"⏳ Status: analyzing (background processing)")
        print(f"{'='*70}\n")

        return {"status": "analyzing", "style_id": style_id}
    except Exception as e:
        print(f"❌ Error triggering analysis: {e}")
        logger.error(f"Error triggering analysis: {e}")
        raise


@router.get("/{style_id}", status_code=status.HTTP_200_OK)
async def get_visual_style(
        style_id: str,
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get visual style by ID"""
    try:
        return await service.get_visual_style(style_id)
    except Exception as e:
        logger.error(f"Error getting visual style: {e}")
        raise


@router.get("/user/my-styles", status_code=status.HTTP_200_OK)
async def get_user_visual_styles(
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        limit: int = 10,
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get all user visual styles"""
    try:
        user_id = str(user.get("_id"))
        skip = (page - 1) * limit
        styles, total = await service.get_user_visual_styles(user_id, skip, limit)
        total_pages = (total + limit - 1) // limit
        return {
            "results": styles,
            "count": total,
            "page": page,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error listing visual styles: {e}")
        raise


@router.delete("/{style_id}", status_code=status.HTTP_200_OK)
async def delete_visual_style(
        style_id: str,
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Delete a visual style"""
    try:
        result = await service.delete_visual_style(style_id)
        return {"deleted": result, "style_id": style_id}
    except Exception as e:
        logger.error(f"Error deleting visual style: {e}")
        raise


@router.post("/{style_id}/apply-to-character", status_code=status.HTTP_200_OK)
async def apply_style_to_character(
        style_id: str,
        character_id: str = Form(...),
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Apply visual style to character"""
    try:
        result = await service.apply_style_to_character(style_id, character_id)
        return result
    except Exception as e:
        logger.error(f"Error applying style: {e}")
        raise


@router.post("/{style_id}/apply-to-location", status_code=status.HTTP_200_OK)
async def apply_style_to_location(
        style_id: str,
        location_id: str = Form(...),
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Apply visual style to location"""
    try:
        result = await service.apply_style_to_location(style_id, location_id)
        return result
    except Exception as e:
        logger.error(f"Error applying style: {e}")
        raise



