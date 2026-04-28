"""Celery tasks for Visual Style module"""
from core.database import db
from visual_style.services import VisualStyleService
from bson import ObjectId
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


async def update_task_status(style_id: str, status: str, progress: int = 0, message: str = ""):
    """Update task status in database

    Args:
        style_id: Visual style ID
        status: Current status (analyzing, generating_character, generating_location, completed, failed)
        progress: Progress percentage (0-100)
        message: Status message
    """
    try:
        print(f"\n📤 UPDATING TASK STATUS")
        print(f"   Style ID: {style_id}")
        print(f"   Status: {status}")
        print(f"   Progress: {progress}%")
        print(f"   Message: {message}")


        result = await db['visual_style'].update_one(
            {'_id': ObjectId(style_id)},
            {'$set': {
                'task_status': status,
                'task_progress': progress,
                'task_message': message,
                'task_updated_at': datetime.utcnow()
            }}
        )

        if result.matched_count == 0:
            print(f"❌ Document not found with ID: {style_id}")
            logger.warning(f"Update task status: Document not found with ID {style_id}")
        elif result.modified_count == 0:
            print(f"⚠️ Document found but no changes made")
            logger.warning(f"Update task status: No changes made for ID {style_id}")
        else:
            print(f"✅ Task status updated successfully!")

    except Exception as e:
        print(f"❌ Error updating task status: {str(e)}")
        logger.error(f"Error updating task status: {e}", exc_info=True)


def register_visual_style_tasks(celery):
    """Register visual style tasks with celery instance (called from celery_worker.py)"""
    service = VisualStyleService()

    @celery.task(name='analyze_visual_style_task', bind=True)
    def analyze_visual_style_task(self, style_id: str, user_id: str):
        """Analyze visual style from reference images (Celery wrapper)

        Args:
            self: Celery task instance (provided by bind=True)
            style_id: String ID of the visual style document
            user_id: String ID of the user
        """
        print(f"\n{'='*70}")
        print(f"🎯 CELERY TASK - ANALYZE VISUAL STYLE")
        print(f"{'='*70}")
        print(f"📋 Task ID: {self.request.id}")
        print(f"📝 Style ID: {style_id}")
        print(f"👤 User ID: {user_id}")

        try:
            print(f"\n⏳ Initializing asyncio event loop...")
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                print(f"✅ Using existing event loop")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print(f"✅ Created new event loop")

            # Run async function and get result
            async def _execute():
                print(f"\n🔄 Executing async task...")
                try:
                    # UPDATE STATUS: Analyzing
                    print(f"📤 Updating status: ANALYZING...")
                    await update_task_status(style_id, 'analyzing', 10, 'Analyzing visual style...')

                    print(f"📤 Calling service.analyze_visual_style()...")
                    logger.info(f"Starting visual style analysis for {style_id}")
                    result = await service.analyze_visual_style(style_id, user_id)
                    print(f"✅ Service call completed")
                    logger.info(f"Completed visual style analysis for {style_id}")

                    # UPDATE STATUS: Analysis completed
                    await update_task_status(style_id, 'analyzing', 30, 'Analysis completed')

                    # Get style prompts for image generation
                    style_prompts = result.get('style_prompts', {})
                    is_animated = result.get('is_animated', False)
                    print(f"\n📊 Got style prompts:")
                    print(f"   Character: {style_prompts.get('character_style', '')[:50]}...")
                    print(f"   Location: {style_prompts.get('location_style', '')[:50]}...")
                    print(f"   Animated: {is_animated}")

                    # Generate example character image
                    print(f"\n🎨 GENERATING CHARACTER IMAGE...")
                    await update_task_status(style_id, 'generating_character', 40, 'Generating character image...')

                    character_data = {
                        'prompt': 'Luis tiene cabello corto y oscuro, piel clara, ojos marrones. Viste una camisa clara y pantalones oscuros.',
                        'genre': 'masculino',
                        'name': 'Luis'
                    }
                    char_image_result = await service.generate_character_image_with_style(
                        character_prompt=character_data['prompt'],
                        character_genre=character_data['genre'],
                        style_prompts=style_prompts,
                        user_id=user_id,
                        is_animated=is_animated
                    )
                    print(f"Character image result: {char_image_result['success']}")

                    print(f"Character image URL: {char_image_result['image_url']}")

                    if char_image_result['success']:
                        await update_task_status(style_id, 'generating_character', 60, 'Character image generated')

                    # Generate example location image
                    print(f"\n🏢 GENERATING LOCATION IMAGE...")
                    await update_task_status(style_id, 'generating_location', 70, 'Generating location image...')

                    location_data = {
                        'prompt': 'Un área de descanso luminosa dentro de una oficina moderna. Hay varias mesas pequeñas distribuidas junto a una máquina de café, y la luz natural entra a través de una amplia ventana con vista a la calle.'
                    }
                    character_data['image'] = char_image_result['image_url'] if char_image_result['success'] else None

                    loc_image_result = await service.generate_location_image_with_style(
                        location_prompt=location_data['prompt'],
                        style_prompts=style_prompts,
                        user_id=user_id,
                        personajes=[character_data],
                        is_animated=is_animated
                    )
                    print(f"Location image result: {loc_image_result['success']}")
                    print(f"Location image URL: {loc_image_result['image_url']}")

                    if loc_image_result['success']:
                        await update_task_status(style_id, 'generating_location', 100, 'Location image generated')

                    # Save images to database
                    print(f"\n📊 Saving both images to database...")
                    await update_task_status(style_id, 'saving', 85, 'Saving images to database...')

                    if char_image_result['success'] and loc_image_result['success']:
                        saved_doc = await service.save_generated_images(
                            visual_style_id=style_id,
                            character_image_url=char_image_result['image_url'],
                            location_image_url=loc_image_result['image_url'],
                            user_id=user_id
                        )
                        print(f"✅ Both images saved to database!")
                        print(f"📊 Generated images:")
                        print(f"   - Character: {saved_doc.get('generated_images', {}).get('character_image_url', '')[:60]}...")
                        print(f"   - Location: {saved_doc.get('generated_images', {}).get('location_image_url', '')[:60]}...")

                    # UPDATE STATUS: Completed
                    await update_task_status(style_id, 'completed', 100, 'Task completed successfully')

                    return {
                        "success": True,
                        "style_id": style_id,
                        "analysis": str(result),
                        "character_image": char_image_result,
                        "location_image": loc_image_result
                    }
                except Exception as e:
                    print(f"❌ Error in async execution: {str(e)}")
                    logger.error(f"Error in visual style analysis: {e}", exc_info=True)

                    # UPDATE STATUS: Failed
                    await update_task_status(style_id, 'failed', 0, f'Error: {str(e)}')

                    return {"success": False, "error": str(e), "style_id": style_id}

            # Execute and return
            print(f"\n🚀 Running async function with event loop...")
            result = loop.run_until_complete(_execute())

            print(f"\n📊 Task Result:")
            print(f"   Success: {result.get('success')}")
            print(f"   Style ID: {result.get('style_id')}")
            if result.get('error'):
                print(f"   Error: {result.get('error')}")

            print(f"\n✨ TASK COMPLETED SUCCESSFULLY!")
            print(f"{'='*70}\n")

            return result

        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR IN CELERY TASK")
            print(f"Error: {str(e)}")
            logger.error(f"Unexpected error in Celery task: {e}", exc_info=True)

            # UPDATE STATUS: Failed
            loop = asyncio.get_event_loop()
            loop.run_until_complete(update_task_status(style_id, 'failed', 0, f'Critical error: {str(e)}'))

            error_result = {"success": False, "error": str(e), "style_id": style_id}
            print(f"{'='*70}\n")
            return error_result

    return analyze_visual_style_task

