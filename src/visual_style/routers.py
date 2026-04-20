"""Routers for Visual Style module"""
import logging
from fastapi import APIRouter, Depends, status, Form, File, UploadFile, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from auth.auth import auth
from auth.utils import auth_schema
from utils import upload_file
from visual_style.services import VisualStyleService
from celery_worker import celery

# HTTPException ya está importado arriba en el import de FastAPI

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


@router.get("/{style_id}/task-status", status_code=status.HTTP_200_OK)
async def get_task_status(
        style_id: str,
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get current task status for visual style analysis

    Returns:
        {
            "style_id": "...",
            "task_status": "analyzing|generating_character|generating_location|saving|completed|failed",
            "task_progress": 0-100,
            "task_message": "Current status message",
            "task_updated_at": "ISO timestamp"
        }
    """
    try:
        print(f"\n{'='*70}")
        print(f"📊 GET TASK STATUS")
        print(f"{'='*70}")
        print(f"📝 Style ID: {style_id}")
        print(f"👤 User ID: {user.get('_id')}")
        
        style = await service.get_visual_style(style_id)
        
        print(f"✅ Style found: {style.get('name')}")
        print(f"   task_status: {style.get('task_status', 'pending')}")
        print(f"   task_progress: {style.get('task_progress', 0)}")
        print(f"   task_message: {style.get('task_message', '')}")
        print(f"   task_updated_at: {style.get('task_updated_at', None)}")
        print(f"{'='*70}\n")
        
        return {
            "style_id": style.get('_id'),
            "task_status": style.get('task_status', 'pending'),
            "task_progress": style.get('task_progress', 0),
            "task_message": style.get('task_message', ''),
            "task_updated_at": style.get('task_updated_at', None)
        }
    except Exception as e:
        print(f"❌ Error getting task status: {e}")
        logger.error(f"Error getting task status: {e}", exc_info=True)
        raise


@router.get("/user/styles", status_code=status.HTTP_200_OK)
async def get_user_styles_v2(
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        limit: int = 10,
        status_filter: str = None,
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get all user visual styles (improved version with filtering)

    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10, max: 50)
        - status_filter: Filter by status (pending, analyzing, completed, failed)

    Returns:
        {
            "results": [...],
            "count": total_count,
            "page": page,
            "total_pages": total_pages,
            "limit": limit,
            "has_next": bool,
            "has_prev": bool
        }
    """
    try:
        print(f"\n{'='*70}")
        print(f"📋 GET USER VISUAL STYLES")
        print(f"{'='*70}")
        print(f"👤 User ID: {user.get('_id')}")
        print(f"📄 Page: {page}, Limit: {limit}")
        if status_filter:
            print(f"🔍 Status filter: {status_filter}")

        user_id = str(user.get("_id"))
        limit = min(limit, 50)  # Max 50 items per page
        skip = (page - 1) * limit

        styles, total = await service.get_user_visual_styles(user_id, skip, limit)
        total_pages = (total + limit - 1) // limit

        print(f"✅ Retrieved {len(styles)} styles")
        print(f"📊 Total: {total}, Total pages: {total_pages}")
        print(f"{'='*70}\n")

        return {
            "results": styles,
            "count": total,
            "page": page,
            "total_pages": total_pages,
            "limit": limit,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    except Exception as e:
        logger.error(f"Error listing visual styles: {e}")
        raise


@router.get("/user/styles-summary", status_code=status.HTTP_200_OK)
async def get_user_styles_summary(
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get summary of user visual styles

    Returns:
        {
            "total_styles": 5,
            "completed": 3,
            "analyzing": 1,
            "failed": 1,
            "pending": 0,
            "recently_updated": [...]
        }
    """
    try:
        print(f"\n{'='*70}")
        print(f"📊 GET USER STYLES SUMMARY")
        print(f"{'='*70}")
        print(f"👤 User ID: {user.get('_id')}")

        user_id = str(user.get("_id"))

        # Get all styles for this user (no pagination for summary)
        styles, total = await service.get_user_visual_styles(user_id, 0, 1000)

        # Calculate status counts
        status_counts = {
            'pending': 0,
            'analyzing': 0,
            'generating_character': 0,
            'generating_location': 0,
            'saving': 0,
            'completed': 0,
            'failed': 0
        }

        for style in styles:
            task_status = style.get('task_status', 'pending')
            if task_status in status_counts:
                status_counts[task_status] += 1

        # Sort by recently updated
        recently_updated = sorted(
            styles,
            key=lambda x: x.get('task_updated_at') or x.get('updated_at'),
            reverse=True
        )[:5]

        print(f"✅ Total styles: {total}")
        print(f"   - Completed: {status_counts['completed']}")
        print(f"   - Analyzing: {status_counts['analyzing']}")
        print(f"   - Failed: {status_counts['failed']}")
        print(f"{'='*70}\n")

        return {
            "total_styles": total,
            "pending": status_counts['pending'],
            "analyzing": status_counts['analyzing'],
            "generating_character": status_counts['generating_character'],
            "generating_location": status_counts['generating_location'],
            "saving": status_counts['saving'],
            "completed": status_counts['completed'],
            "failed": status_counts['failed'],
            "recently_updated": recently_updated
        }
    except Exception as e:
        logger.error(f"Error getting styles summary: {e}")
        raise


@router.get("/user/completed", status_code=status.HTTP_200_OK)
async def get_user_completed_styles(
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        page: int = 1,
        limit: int = 10,
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get only completed user visual styles

    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10, max: 50)

    Returns:
        {
            "results": [...],
            "count": total_count,
            "page": page,
            "total_pages": total_pages
        }
    """
    try:
        print(f"\n{'='*70}")
        print(f"✅ GET COMPLETED STYLES")
        print(f"{'='*70}")
        print(f"👤 User ID: {user.get('_id')}")

        user_id = str(user.get("_id"))
        limit = min(limit, 50)
        skip = (page - 1) * limit

        # Use the new method that filters by status and orders by updated_at
        styles, total = await service.get_user_completed_visual_styles(user_id, skip, limit)

        total_pages = (total + limit - 1) // limit

        print(f"✅ Retrieved {len(styles)} completed styles")
        print(f"{'='*70}\n")

        return {
            "results": styles,
            "count": len(styles),
            "page": page,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error getting completed styles: {e}")
        raise


@router.patch("/{style_id}", status_code=status.HTTP_200_OK)
async def update_visual_style(
        style_id: str,
        name: str = Form(None),
        description: str = Form(None),
        original_prompt: str = Form(None),
        re_analyze: bool = Form(False),
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Update visual style fields and optionally trigger re-analysis

    Form Parameters:
        - name: Updated style name (optional)
        - description: Updated description (optional)
        - original_prompt: Updated prompt (optional)
        - re_analyze: If true, will trigger analysis task after update (default: false)

    Returns:
        {
            "updated": {...},
            "task_sent": false or task_id,
            "message": "Updated successfully" or "Updated and re-analysis started"
        }
    """
    try:
        print(f"\n{'='*70}")
        print(f"📝 UPDATE VISUAL STYLE")
        print(f"{'='*70}")
        print(f"📝 Style ID: {style_id}")
        print(f"👤 User ID: {user.get('_id')}")
        print(f"🔄 Re-analyze: {re_analyze}")

        user_id = str(user.get("_id"))

        # Prepare update data
        updates = {}
        if name:
            updates['name'] = name
        if description:
            updates['description'] = description
        if original_prompt:
            updates['original_prompt'] = original_prompt

        # Update the style
        updated_doc = await service.update_visual_style(style_id, updates)
        print(f"✅ Style updated successfully!")

        response = {
            "updated": updated_doc,
            "task_sent": False,
            "message": "Updated successfully"
        }

        # If re_analyze is True, send the analysis task
        if re_analyze:
            print(f"\n📤 Re-sending analysis task...")
            task_result = celery.send_task('analyze_visual_style_task', args=[style_id, user_id])
            response['task_sent'] = task_result.id
            response['message'] = "Updated and re-analysis started"
            print(f"✅ Analysis task sent!")
            print(f"📋 Task ID: {task_result.id}")

        print(f"{'='*70}\n")
        return response

    except Exception as e:
        print(f"❌ Error updating visual style: {e}")
        logger.error(f"Error updating visual style: {e}")
        raise


@router.post("/{style_id}/re-analyze", status_code=status.HTTP_202_ACCEPTED)
async def re_analyze_visual_style(
        style_id: str,
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Re-send analysis task for a visual style (without updating fields)

    Returns:
        {
            "status": "re-analyzing",
            "style_id": "...",
            "task_id": "...",
            "message": "Re-analysis started"
        }
    """
    try:
        print(f"\n{'='*70}")
        print(f"🔄 RE-ANALYZE VISUAL STYLE")
        print(f"{'='*70}")
        print(f"📝 Style ID: {style_id}")
        print(f"👤 User ID: {user.get('_id')}")

        user_id = str(user.get("_id"))

        # Verify style exists
        style = await service.get_visual_style(style_id)
        print(f"✅ Style found: {style.get('name')}")

        # Send re-analysis task
        print(f"\n📤 Sending re-analysis task...")
        task_result = celery.send_task('analyze_visual_style_task', args=[style_id, user_id])

        print(f"✅ Re-analysis task sent!")
        print(f"📋 Task ID: {task_result.id}")
        print(f"{'='*70}\n")

        return {
            "status": "re-analyzing",
            "style_id": style_id,
            "task_id": task_result.id,
            "message": "Re-analysis started"
        }
    except Exception as e:
        print(f"❌ Error re-analyzing visual style: {e}")
        logger.error(f"Error re-analyzing visual style: {e}")
        raise


@router.post("/{style_id}/select", status_code=status.HTTP_200_OK)
async def select_visual_style_for_user(
        style_id: str,
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Select a visual style for the current user

    Args:
        style_id: Visual style ID to select

    Returns:
        {
            "user_id": "...",
            "selected_visual_style_id": "...",
            "style_name": "...",
            "message": "Visual style selected successfully"
        }
    """
    try:
        user_id = str(user.get("_id"))
        result = await service.select_user_visual_style(user_id, style_id)
        return result
    except Exception as e:
        logger.error(f"Error selecting visual style: {e}")
        raise


@router.get("/user/selected", status_code=status.HTTP_200_OK)
async def get_user_selected_visual_style(
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Get the selected visual style for the current user

    Returns:
        {
            "selected_visual_style_id": "..." or null,
            "_id": "...",
            "name": "...",
            "description": "...",
            ... (full style document if selected)
        }
    """
    try:
        user_id = str(user.get("_id"))
        result = await service.get_user_selected_visual_style(user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting selected visual style: {e}")
        raise


@router.post("/user/selected/clear", status_code=status.HTTP_200_OK)
async def clear_user_visual_style_selection(
        user: dict = Depends(auth),
        token: HTTPAuthorizationCredentials = Depends(auth_schema),
        service: VisualStyleService = Depends(get_visual_style_service)
):
    """Clear the selected visual style for the current user

    Returns:
        {
            "cleared": true,
            "message": "Visual style selection cleared"
        }
    """
    try:
        user_id = str(user.get("_id"))
        result = await service.clear_user_visual_style_selection(user_id)
        return result
    except Exception as e:
        logger.error(f"Error clearing visual style selection: {e}")
        raise

