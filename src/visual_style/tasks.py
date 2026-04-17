"""Celery tasks for Visual Style module"""
from core.database import db
from visual_style.services import VisualStyleService
import logging
import asyncio

logger = logging.getLogger(__name__)


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
                    print(f"📤 Calling service.analyze_visual_style()...")
                    logger.info(f"Starting visual style analysis for {style_id}")
                    result = await service.analyze_visual_style(style_id, user_id)
                    print(f"✅ Service call completed")
                    logger.info(f"Completed visual style analysis for {style_id}")

                    # Get style prompts for image generation
                    style_prompts = result.get('style_prompts', {})
                    print(f"\n📊 Got style prompts:")
                    print(f"   Character: {style_prompts.get('character_style', '')[:50]}...")
                    print(f"   Location: {style_prompts.get('location_style', '')[:50]}...")

                    # Generate example character image
                    print(f"\n🎨 GENERATING CHARACTER IMAGE...")
                    character_data = {
                        'prompt': 'Luis tiene cabello corto y oscuro, piel clara, ojos marrones. Viste una camisa clara y pantalones oscuros.',
                        'genre': 'masculino',
                        'name': 'Luis'
                    }
                    char_image_result = await service.generate_character_image_with_style(
                        character_prompt=character_data['prompt'],
                        character_genre=character_data['genre'],
                        style_prompts=style_prompts,
                        user_id=user_id
                    )
                    print(f"Character image result: {char_image_result['success']}")

                    # Generate example location image
                    print(f"\n🏢 GENERATING LOCATION IMAGE...")
                    location_data = {
                        'prompt': 'Un área de descanso luminosa dentro de una oficina moderna. Hay varias mesas pequeñas distribuidas junto a una máquina de café, y la luz natural entra a través de una amplia ventana con vista a la calle.'
                    }
                    character_data['image'] = char_image_result['image_url'] if char_image_result['success'] else None

                    loc_image_result = await service.generate_location_image_with_style(
                        location_prompt=location_data['prompt'],
                        style_prompts=style_prompts,
                        user_id=user_id,
                        personajes=[character_data]
                    )
                    print(f"Location image result: {loc_image_result['success']}")

                    # Save images to database
                    print(f"\n📊 Saving both images to database...")
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
            error_result = {"success": False, "error": str(e), "style_id": style_id}
            print(f"{'='*70}\n")
            return error_result

    return analyze_visual_style_task

