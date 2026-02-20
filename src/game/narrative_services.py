import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from bson import ObjectId

from core.database import db
from game.narrative_templates import (
    NarrativeTemplate, LearnTemplate, EvaluationTemplate,
    TriviaTemplate, SolveTemplate, ExpertTemplate,
    TemplateType, InteractionType, NarrativeScene,
    NarrativeEvent, SceneInteraction
)
from game.narrative_schemas import (
    SchemaGenerateFromScript, SchemaTemplateExtractionResult,
    SchemaTemplateGenerationProgress
)
from gpt_ai.utils import openai_generator


async def update_template_generation_status(template_id: str, status: str, progress: int = None,
                                          progress_text: str = None, current_step: str = None):
    """Actualiza el estado de generación del template"""
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }

    if progress is not None:
        update_data["progress"] = progress
    if progress_text is not None:
        update_data["progress_text"] = progress_text
    if current_step is not None:
        update_data["current_step"] = current_step

    await db["narrative_templates"].update_one(
        {"template_id": template_id},
        {"$set": update_data}
    )


def create_template_by_type(template_type: TemplateType, base_data: Dict[str, Any]) -> NarrativeTemplate:
    """Factory para crear templates según su tipo"""

    template_classes = {
        TemplateType.LEARN: LearnTemplate,
        TemplateType.EVALUATION: EvaluationTemplate,
        TemplateType.TRIVIA: TriviaTemplate,
        TemplateType.SOLVE: SolveTemplate,
        TemplateType.EXPERT: ExpertTemplate
    }

    template_class = template_classes.get(template_type, NarrativeTemplate)
    return template_class(**base_data)


async def generate_narrative_structure_from_script(script_data: SchemaGenerateFromScript) -> Dict[str, Any]:
    """Genera la estructura narrativa usando GPT basada en el script y tipo de template"""

    # Prompt específico según el tipo de template
    template_prompts = {
        TemplateType.LEARN: """
        Crea una estructura de narrativa interactiva tipo LEARN con:
        - Evento Intro de presentación
        - 3 Escenas (1, 2, 3) con interacciones tipo "two_way" de 4-6 opciones cada una
        - Eventos de transición entre escenas
        - Evento Final de cierre
        - Enfoque en aprendizaje progresivo
        """,

        TemplateType.EVALUATION: """
        Crea una estructura de narrativa interactiva tipo EVALUATION con:
        - Evento Intro de explicación
        - 3 Escenas (1, 2, 3) con interacciones "two_way" + "open_answer" de 2-4 opciones
        - Sin manejo de errores (todas las respuestas son válidas)
        - La contrarespuesta del personaje es siempre consistente
        - Eventos de transición automáticos
        - Evento Final de recopilación
        """,

        TemplateType.TRIVIA: """
        Crea una estructura de narrativa interactiva tipo TRIVIA con:
        - Evento Intro de instrucciones
        - 3 Escenas (1, 2, 3) con interacciones "two_way" + "option_multiple" de 2-4 opciones
        - Solo se avanza con respuesta correcta
        - Contrarespuesta del personaje cambia según acierto/error
        - Eventos condicionados a respuestas correctas
        - Evento Final solo para quienes completan
        """,

        TemplateType.SOLVE: """
        Crea una estructura de narrativa interactiva tipo SOLVE con:
        - Evento Intro de planteamiento del problema
        - Escena A: Two Ways (2-4 opciones)
        - Escena B: Two Ways (2-4 opciones)  
        - Escena C: Two Ways + Open Answer (2-4 opciones)
        - Contrarespuesta varía según acierto/error
        - Evento Final solo accesible resolviendo correctamente
        """,

        TemplateType.EXPERT: """
        Crea una estructura de narrativa interactiva tipo EXPERT con:
        - Evento Intro de bienvenida
        - 3 Escenas (A, B, C) con interacciones "Open Talk" (conversación libre)
        - Eventos de transición fluidos
        - Contrarespuesta final siempre igual independiente de la conversación
        - Evento Final de despedida
        """
    }

    prompt = f"""
    {template_prompts[script_data.template_type]}
    
    Script base: {script_data.script}
    Título: {script_data.title}
    Categoría: {script_data.category}
    Número de escenas: {script_data.num_scenes}
    
    Responde en formato JSON con esta estructura:
    {{
        "intro_event": {{
            "event_id": "intro_event_id",
            "event_name": "Nombre del evento intro",
            "description": "Descripción del evento",
            "is_intro": true
        }},
        "scenes": [
            {{
                "scene_id": "scene_a",
                "scene_name": "Nombre escena A",
                "interaction": {{
                    "interaction_type": "tipo_interaccion",
                    "min_options": 2,
                    "max_options": 4,
                    "allows_error": true,
                    "error_handling": "continue/retry/block",
                    "response_varies": true
                }},
                "content": "Contenido de la escena"
            }}
        ],
        "transition_events": [
            {{
                "event_id": "event_a_to_b",
                "event_name": "Transición A a B",
                "from_scene": "scene_a",
                "to_scene": "scene_b",
                "condition_type": "always/correct_answer"
            }}
        ],
        "final_event": {{
            "event_id": "final_event_id",
            "event_name": "Nombre del evento final",
            "description": "Descripción del evento final",
            "is_final": true
        }}
    }}
    """

    try:
        response = await openai_generator(
            message_content=prompt,
            model="gpt-4o-mini",
            temperature=0.7
        )

        # Parsear la respuesta JSON
        structure = json.loads(response)
        return structure

    except Exception as e:
        raise Exception(f"Error generando estructura narrativa: {str(e)}")


async def create_narrative_template_from_script(script_data: SchemaGenerateFromScript) -> str:
    """Crea un template de narrativa completo desde un script"""

    template_id = str(uuid.uuid4())

    try:
        # Inicializar status
        await update_template_generation_status(
            template_id, "processing", 10,
            "Iniciando generación de template", "script_analysis"
        )

        # Generar estructura con GPT
        await update_template_generation_status(
            template_id, "processing", 30,
            "Generando estructura narrativa", "structure_generation"
        )

        structure = await generate_narrative_structure_from_script(script_data)

        # Crear escenas
        await update_template_generation_status(
            template_id, "processing", 50,
            "Procesando escenas", "scenes_processing"
        )

        scenes = []
        for scene_data in structure.get("scenes", []):
            interaction = SceneInteraction(**scene_data["interaction"])
            scene = NarrativeScene(
                scene_id=scene_data["scene_id"],
                scene_name=scene_data["scene_name"],
                interaction=interaction
            )
            scenes.append(scene)

        # Crear eventos
        await update_template_generation_status(
            template_id, "processing", 70,
            "Procesando eventos", "events_processing"
        )

        intro_event = NarrativeEvent(**structure["intro_event"])
        final_event = NarrativeEvent(**structure["final_event"])

        transition_events = []
        for event_data in structure.get("transition_events", []):
            event = NarrativeEvent(**event_data)
            transition_events.append(event)

        # Crear template
        await update_template_generation_status(
            template_id, "processing", 85,
            "Creando template final", "template_creation"
        )

        template_data = {
            "template_id": template_id,
            "name": script_data.title,
            "template_type": script_data.template_type,
            "description": f"Template generado desde script para {script_data.category}",
            "intro_event": intro_event,
            "scenes": scenes,
            "transition_events": transition_events,
            "final_event": final_event,
            "rules": {}
        }

        template = create_template_by_type(script_data.template_type, template_data)

        # Guardar en base de datos
        template_dict = template.dict()
        template_dict["_id"] = ObjectId()

        await db["narrative_templates"].insert_one(template_dict)

        await update_template_generation_status(
            template_id, "completed", 100,
            "Template creado exitosamente", "completed"
        )

        return template_id

    except Exception as e:
        await update_template_generation_status(
            template_id, "error", 0,
            f"Error en generación: {str(e)}", "error"
        )
        raise


async def extract_template_elements(template_id: str) -> SchemaTemplateExtractionResult:
    """Extrae elementos individuales (personajes, locaciones, eventos) de un template"""

    template_doc = await db["narrative_templates"].find_one({"template_id": template_id})
    if not template_doc:
        raise ValueError(f"Template {template_id} no encontrado")

    extraction_result = SchemaTemplateExtractionResult(template_id=template_id)

    # Extraer personajes principales mencionados
    characters = []
    scenes_content = [scene.get("content", "") for scene in template_doc.get("scenes", [])]
    all_content = " ".join(scenes_content)

    # Aquí podrías usar NLP o GPT para extraer personajes automáticamente
    # Por ahora, buscaremos patrones básicos

    # Extraer locaciones
    locations = []
    for scene in template_doc.get("scenes", []):
        if scene.get("location_id"):
            locations.append({
                "location_id": scene["location_id"],
                "scene_reference": scene["scene_id"]
            })

    # Extraer eventos
    events = []
    events.append(template_doc.get("intro_event", {}))
    events.extend(template_doc.get("transition_events", []))
    events.append(template_doc.get("final_event", {}))

    # Extraer escenas
    scenes = template_doc.get("scenes", [])

    extraction_result.characters = characters
    extraction_result.locations = locations
    extraction_result.events = events
    extraction_result.scenes = scenes
    extraction_result.extraction_summary = {
        "total_characters": len(characters),
        "total_locations": len(locations),
        "total_events": len(events),
        "total_scenes": len(scenes),
        "template_type": template_doc.get("template_type"),
        "extraction_timestamp": datetime.utcnow().isoformat()
    }

    return extraction_result


async def get_template_generation_status(template_id: str) -> Optional[SchemaTemplateGenerationProgress]:
    """Obtiene el estado actual de generación de un template"""

    template_doc = await db["narrative_templates"].find_one({"template_id": template_id})
    if not template_doc:
        return None

    return SchemaTemplateGenerationProgress(
        template_id=template_id,
        status=template_doc.get("status", "unknown"),
        progress=template_doc.get("progress", 0),
        progress_text=template_doc.get("progress_text", ""),
        current_step=template_doc.get("current_step", ""),
        estimated_time_remaining=template_doc.get("estimated_time_remaining")
    )


async def list_narrative_templates(template_type: Optional[TemplateType] = None) -> List[Dict[str, Any]]:
    """Lista todos los templates de narrativa, opcionalmente filtrados por tipo"""

    query = {}
    if template_type:
        query["template_type"] = template_type.value

    templates = await db["narrative_templates"].find(query).to_list(length=100)

    return [
        {
            "template_id": template["template_id"],
            "name": template["name"],
            "template_type": template["template_type"],
            "created_at": template["created_at"].isoformat() if template.get("created_at") else None,
            "status": template.get("status", "unknown")
        }
        for template in templates
    ]
