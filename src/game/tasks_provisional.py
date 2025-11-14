import json
import random
import string
from io import BytesIO

from task.services import create_task_service, update_task_service
from tasks_shared import generate_character_task, generate_image_event_task, generate_location_task, \
    generate_voice_character_task
import requests
import base64
from datetime import datetime
from uuid import uuid4
import traceback

import pytz
from bson import ObjectId
from fastapi import UploadFile

from openai import NotGiven

from pydantic import BaseModel
from pydantic import Field

from character.models import CharacterGLIC, Character
from character.schemas import SchemaCreateCharacter, ConversationsCharacter, ConversationsOptionsCharacter
from core.database import db
from event.models import Event
from event.schemas import SchemaCreateEvent
from game.models import Game
from game.narrative_templates import TemplateType

from gpt_ai.utils import openai_generator
from location.models import Location, LocationGLIC
from location.schemas import SchemaCreateLocation
from location.tasks import  generate_location_image
from state_game.services import create_state_game, get_state_game_by_game_id, get_state_game_by_id
from state_glic.services import create_state_glic, get_list_state_glic_by_element_id

from utils import upload_image

from config import settings
import asyncio

# Configuración del sistema de logs
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger("game_provisional_tasks")

NOT_GIVEN = NotGiven()


async def deactivate_character_service(character_id: str, state_game: str, active: bool):
    try:
        if character_db := await db["character"].find_one({"_id": ObjectId(character_id)}):
            state_element_db = await db["state_glic"].find_one(
                {"element_id": character_id, "type_element": "character", "state": state_game}
            )

            state_game_max = await db["state_game"].find_one({"game_id": character_db["game_id"]}, sort=[("order", -1)])

            if not state_element_db:
                state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})
                order = state_game_db["order"] + 1
                state_element_db = None

                while state_element_db is None:
                    state_element_db = await db["state_glic"].find_one(
                        {"element_id": character_id, "type_element": "character", "order": order}
                    )
                    if state_element_db:
                        break
                    if order > state_game_max['order']:
                        break
                    order += 1

                if state_element_db is None:
                    state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})
                    order = state_game_db["order"] - 1
                    state_element_db = None

                    while state_element_db is None:
                        state_element_db = await db["state_glic"].find_one(
                            {"element_id": character_id, "type_element": "character", "order": order}
                        )
                        if state_element_db:
                            break
                        if order < 1:
                            break
                        order -= 1
                    if not state_element_db:
                        return "failed deactivate / activate character"

                    state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})

                    state_element_db['data']['is_active'] = active
                    state_element_db['data']['interaction'] = []

                    state_element_db = await create_state_glic(
                        element_id=str(character_id),
                        type_element="character",
                        state=state_game,
                        order=state_game_db['order'],
                        created_by=state_game_db['created_by'],
                        data=state_element_db['data'],
                    )

                    return "Character created and deactivated / activate successfully"

            state_element_db['data']['is_active'] = active
            await db["state_glic"].update_one(
                {"_id": state_element_db["_id"]}, {"$set": {"data": state_element_db["data"]}}
            )

            return "Character deactivated / activate successfully"
    except Exception as e:
        print(traceback.print_exc())
        print(f"Error in deactivate character service: {e}")
        return "failed deactivate / activate character"


async def update_game_provisional_status(id_game_provisional: str, status: str, progress: int = None,
                                         progress_text: str = None, task: str = None):
    """
    Actualiza el estado del juego provisional y registra el historial.

    Args:
        id_game_provisional: ID del juego provisional
        status: Estado actual del proceso
        progress: Progreso en porcentaje (opcional)
        progress_text: Texto descriptivo del progreso actual (opcional)
        task: Nombre de la tarea (opcional)
        message: Mensaje descriptivo (opcional)
    """
    update_data = {
        "state": status,
        "updated_at": datetime.now(pytz.utc)
    }

    if progress is not None:
        update_data["progress"] = progress

    if progress_text is not None:
        update_data["progress_text"] = progress_text

    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$set": update_data}
    )

    # Registrar historial de estado
    entry = {
        "timestamp": datetime.utcnow(),
        "task": task or status,
        "status": status,
        "percent": progress,
        "message": progress_text
    }
    await db["game_provisional"].update_one(
        {"_id": ObjectId(id_game_provisional)},
        {"$push": {"history": entry}}
    )


class TaskCreateGameProvisional(BaseModel):
    script: str = Field(..., example="script", description="Script extens for the game  in text format")
    title: str = Field(..., example="title", description="Title for the game provisional")
    num_scenes: int = Field(..., example=1, description="Number of scenes in the game provisional")
    category: str = Field(..., example="Learning", description="Category of the game based on its content and purpose")


async def create_game_provisional(_id_game_provisional: str):
    """
    Create a provisional game entry in the database.
    """

    # if settings.MODE_TEST:
    #     print("init")
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 0,
    #                                          "test mode active: skipping file download.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 10,
    #                                          "test mode active: skipping file download.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 25,
    #                                          "test mode active: skipping content generation.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 50,
    #                                          "test mode active: skipping image generation and upload.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 80,
    #                                          "test mode active: skipping image generation and upload.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 90,
    #                                          "test mode active: skipping saving data.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(_id_game_provisional, "script_create", 100,
    #                                          "test mode active: game provisional created successfully.")
    #     return "test mode active: game provisional created successfully"

    try:
        # Actualizar estado: Iniciando proceso
        await update_game_provisional_status(_id_game_provisional, "processing", 0,
                                             "Game provisional creation started, initializing process.")

        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(_id_game_provisional)})

        if not game_provisional_db:
            await update_game_provisional_status(_id_game_provisional, "error", 0,
                                                 "Game provisional not found in database.")
            # logger.warning(f"Juego provisional con ID {_id_game_provisional} no encontrado")
            return "Game provisional not found"

        # Actualizar estado: Descargando archivo
        await update_game_provisional_status(_id_game_provisional, "downloading_file", 10,
                                             "Downloading source file for processing.")

        # logger.debug(f"Juego provisional encontrado: {game_provisional_db.get('_id')}")
        file_url = game_provisional_db["file"]
        # logger.info(f"Descargando archivo desde URL: {file_url}")
        response = requests.get(file_url)

        if response.status_code == 200:
            # logger.debug("Archivo descargado correctamente")
            data = response.content  # Contenido binario del archivo
            # Codificar el archivo en base64
            base64_string = base64.b64encode(data).decode("utf-8")
            # logger.debug(f"Archivo codificado en base64 (primeros 100 caracteres): {base64_string[:100]}...")
        else:
            await update_game_provisional_status(_id_game_provisional, "error", 10,
                                                 f"Failed to download file. HTTP status: {response.status_code}")
            # logger.error(f"Error al descargar archivo. Código de estado: {response.status_code}")
            return "Error generating file"

        # Actualizar estado: Generando contenido del juego
        await update_game_provisional_status(_id_game_provisional, "generating_content", 25,
                                             "Generating game script and title using AI.")

        type_template = game_provisional_db.get("type_template", None)
        template_definition = get_template_definition(type_template)
        # logger.info("Generando contenido del juego con GPT-4.1")
        # Refuerzo para template TRIVIA
        if type_template and str(type_template).lower() == "trivia":
            trivia_warning = """
IMPORTANTE: El template es TRIVIA. TODAS las escenas deben tener interacción de tipo 'option_multiple', siguiendo exactamente el formato del ejemplo. No incluyas interacciones de tipo 'two_way' ni 'one_way'. Si no sigues el formato, el resultado será rechazado.

Ejemplo de interacción option_multiple:
1: ¿Cuál es la capital de Francia?
Opciones:
- París
- Madrid
- Berlín
Respuestas:
- París: ¡Correcto! París es la capital de Francia.
- Madrid: Incorrecto. Madrid es la capital de España.
- Berlín: Incorrecto. Berlín es la capital de Alemania.

Estructura exacta:
- Evento inicial
- Escena 1
  - Locación 1
  - Personaje principal
  - Personaje secundario
  - Interacción (option_multiple): [formato del ejemplo]
  - Evento después de la interacción
- Escena 2
  - Locación 2
  - Personaje principal
  - Personaje secundario
  - Interacción (option_multiple): [formato del ejemplo]
- Escena 3
  - Locación 3
  - Personaje principal
  - Personaje secundario
  - Interacción (option_multiple): [formato del ejemplo]
  - Evento final

No incluyas ningún otro tipo de interacción. Sigue el formato del ejemplo al pie de la letra.
"""
        else:
            trivia_warning = ""
        template_interaction_instruction = ""
        if type_template:
            tipo = str(type_template).lower()
            if tipo == "trivia":
                template_interaction_instruction = "IMPORTANTE: Todas las interacciones deben ser de tipo 'option_multiple' (trivia). Cada escena debe tener una pregunta, opciones y retroalimentación, siguiendo el ejemplo proporcionado."
            elif tipo == "learn":
                template_interaction_instruction = "IMPORTANTE: Todas las interacciones deben ser de tipo 'two_way' (diálogo bidireccional entre personajes, sin opciones de respuesta)."
            elif tipo == "evaluation":
                template_interaction_instruction = "IMPORTANTE: Todas las interacciones deben ser de tipo 'open_question' (el jugador responde libremente a una pregunta del personaje)."
            elif tipo == "solve":
                template_interaction_instruction = "IMPORTANTE: Las primeras dos escenas deben ser 'two_way' y la última 'open_question'."
            elif tipo == "expert":
                template_interaction_instruction = "IMPORTANTE: Todas las interacciones deben ser de tipo 'open_talk' (conversación abierta con el experto)."
        # Generación de contenido (sin reintentos)
        content_prompt = get_template_prompt(type_template, template_definition,
                                             game_provisional_db.get('prompt_user', 'No prompt provided'),
                                             base64_string)
        source_game_response = await openai_generator.generate_gpt(
            content_prompt=content_prompt,
            model="gpt-4.1",
            response_format=TaskCreateGameProvisional,
            type_generation="game_provisional",
            user_id=None,
            max_tokens=16384,
        )
        if not source_game_response:
            await update_game_provisional_status(_id_game_provisional, "error", 25,
                                                 "Failed to generate game content from AI.")
            return "Failed to generate game provisional"

        if not source_game_response:
            await update_game_provisional_status(_id_game_provisional, "error", 25,
                                                 "Failed to generate game content from AI.")
            # logger.error("No se recibió respuesta de la API de OpenAI")
            return "Failed to generate game provisional"

        # Verificar si estamos en modo test para omitir generación de imágenes
        if settings.MODE_TEST:
            # En modo test, omitir generación y subida de imágenes
            await update_game_provisional_status(_id_game_provisional, "skipping_image_test", 80,
                                                 "Test mode active: skipping image generation and upload.")

            # Usar una imagen por defecto en modo test
            url_image = "https://storage.googleapis.com/qwestar/voxel_.jpg"
        else:
            # Actualizar estado: Generando imagen de portada
            await update_game_provisional_status(_id_game_provisional, "generating_image", 60,
                                                 "Generating cover image for the game.")

            # logger.info(f"Contenido generado correctamente. Título: '{source_game_response.title}'")
            # logger.debug(f"Longitud del guión generado: {len(source_game_response.script)} caracteres")

            # logger.info("Generando imagen de portada para el juego")
            image_game_provisional = await openai_generator.generate_image(
                prompt=f"Genera una imagen de portada en estilo 3D low poly de proporciones realistas para el juego ."
                       f"basado en el  script: {source_game_response.script} "
                       f"que ejemplifique una escena del juego con un personaje principal que represente el estilo del juego, no debe tener texto o título.",
                model="gpt-image-1",
                size="1024x1536",
                style=None
            )

            # Actualizar estado: Subiendo imagen
            await update_game_provisional_status(_id_game_provisional, "uploading_image", 80,
                                                 "Uploading generated cover image to storage.")

            # logger.debug("Imagen generada, decodificando base64")
            image_bytes = base64.b64decode(image_game_provisional)

            # logger.info("Subiendo imagen a almacenamiento")
            url_image = upload_image(
                img_byte_arr=image_bytes,
                file_name=f"game-provisional/{uuid4()}.jpg",
                size=(512, 896)
            )

            if not url_image:
                await update_game_provisional_status(_id_game_provisional, "error", 80,
                                                     "Failed to upload generated image to storage.")
                # logger.error("Error al subir la imagen generada")
                return "Failed to upload image"

        # Actualizar estado: Guardando en base de datos
        await update_game_provisional_status(_id_game_provisional, "saving_data", 90,
                                             "Saving provisional game data to database.")

        # logger.debug(f"Imagen subida correctamente: {url_image}")

        # logger.info("Actualizando registro en base de datos")
        game_provisional_db["image"] = url_image
        game_provisional_db["title"] = source_game_response.title
        game_provisional_db["script"] = source_game_response.script
        game_provisional_db["category"] = source_game_response.category
        game_provisional_db["updated_at"] = datetime.now(pytz.utc)
        game_provisional_db["num_scenes"] = source_game_response.num_scenes

        await db["game_provisional"].update_one(
            {"_id": ObjectId(_id_game_provisional)},
            {"$set": game_provisional_db}
        )

        # Actualizar estado: Completado
        await update_game_provisional_status(_id_game_provisional, "completed", 100,
                                             "Game provisional created successfully, waiting for processing.")

        # logger.info(f"Juego provisional creado exitosamente: {_id_game_provisional}")
        return "game provisional created successfully"
    except Exception as e:
        # Actualizar estado: Error
        await update_game_provisional_status(_id_game_provisional, "error", 0, f"Unexpected error occurred: {str(e)}")
        # logger.error(f"Error en create_game_provisional: {str(e)}")
        # logger.debug(traceback.format_exc())
        return "Failed to create game provisional"


async def async_create_game_provisional_task(id_game_provisional: str):
    """
    Asynchronous task to create a provisional game.
    """
    # logger.info(f"Iniciando tarea asíncrona para crear juego provisional con ID: {id_game_provisional}")
    try:
        result = await create_game_provisional(_id_game_provisional=id_game_provisional)
        # logger.info(f"Tarea completada para juego {id_game_provisional} con resultado: {result}")
        return result
    except Exception as e:
        #     logger.error(f"Error en tarea async_create_game_provisional_task: {str(e)}")
        #     logger.debug(traceback.format_exc())
        return f"Error: {str(e)}"


class SceneCountResponse(BaseModel):
    scene_count: str = Field(..., description="Número de escenas identificadas en el guión")


async def extract_scene_count_from_script(script: str) -> int:
    """
    Analiza el guión para determinar el número de escenas presentes.

    Args:
        script: El guión completo del juego

    Returns:
        int: El número de escenas identificadas
    """
    # logger.info("Iniciando extracción del número de escenas del guión")
    # logger.debug(f"Longitud del guión a analizar: {len(script)} caracteres")
    try:
        # Definimos un modelo Pydantic para la respuesta

        # logger.debug("Enviando solicitud a GPT para análisis de escenas")
        # Utilizamos GPT para identificar el número de escenas en el guión
        scene_count_response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un asistente especializado en análisis de guiones. Tu tarea es identificar y"
                               " contar el número total de escenas en un guión."
                },
                {
                    "role": "user",
                    "content": f"Analiza el siguiente guión y determina cuántas escenas diferentes contiene. Responde "
                               f"con un número entero: {script}"
                }
            ],
            model="gpt-4o-mini",
            response_format=SceneCountResponse,
            user_id="anonymous",
            max_tokens=1000,
            type_generation="generate story init game",
        )

        if isinstance(scene_count_response, str):
            scene_count_response = json.loads(scene_count_response)

        # Asegúrate de que sea un diccionario y conviértelo a SceneCountResponse
        if isinstance(scene_count_response, dict):
            scene_count_response = SceneCountResponse(**scene_count_response)

        # Ahora accede al atributo scene_count
        num_scenes = max(1, int(scene_count_response.scene_count) if isinstance(scene_count_response.scene_count,
                                                                                str) else scene_count_response.scene_count)
        return num_scenes

    except Exception as e:
        # logger.error(f"Error al extraer el número de escenas: {str(e)}")
        # logger.debug(traceback.format_exc())
        print(traceback.format_exc())
        return f"Error: {str(e)}"


class SceneInteractionResponse(BaseModel):
    content: str = Field(..., description="Contenido de la interacción generada para la escena")


async def generate_interaction_for_scene(script: str, scene_num: int, template_type: str = None):
    """
    Genera la interacción para una escena específica del guión.

    Args:
        script: El guión completo del juego
        scene_num: El número de la escena para la que generar la interacción
        template_type: Tipo de template del juego (opcional)

    Returns:
        dict: Un diccionario con la información de interacción para la escena
    """
    # logger.info(f"Generando interacción para escena {scene_num}")
    try:
        # logger.debug(f"Preparando prompt para GPT con escena {scene_num}")

        # Obtener la definición del template si se proporciona
        template_definition = ""
        if template_type:
            try:
                # Convertir string a TemplateType enum si es necesario
                if isinstance(template_type, str):
                    template_type_enum = TemplateType(template_type)
                else:
                    template_type_enum = template_type
                template_definition = get_template_definition(template_type_enum)
            except (ValueError, AttributeError):
                # Si no se puede convertir o no existe, usar definición vacía
                template_definition = ""

        # Construir el prompt con la definición del template
        template_context = f"\n\nDEFINICIÓN DEL TEMPLATE:\n{template_definition}\n\nAsegúrate de que la interacción generada siga las reglas específicas del template mencionado arriba." if template_definition else ""

        # Utilizamos el prompt proporcionado para generar la interacción
        interaction_response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": "Eres un asisyente que extrae las interacciones de los personajes en formato de diálogo"
                },
                {
                    "role": "user",
                    "content": f"""
                            De la escena de escena {scene_num + 1} del guión, extre con que personajes interactúa el jugador y extrae la interacción en formato de diálogo.
                            {template_context}
                            Aquí está el guión completo:
                            {script}
                            """
                }
            ],
            model="gpt-4.1",
            user_id=None,
            max_tokens=10000,
            type_generation="generate scene interaction",
            response_format=SceneInteractionResponse
        )

        # logger.debug(f"Respuesta recibida para escena {scene_num}. Longitud: {len(interaction_response) if interaction_response else 0} caracteres")

        # Analizamos la respuesta para estructurala adecuadamente
        result = {
            "content": interaction_response.content,
            "created_at": datetime.now(pytz.utc),
            "error": False
        }
        # logger.info(f"Interacción generada exitosamente para escena {scene_num}")
        return result

    except Exception as e:
        # logger.error(f"Error al generar interacción para escena {scene_num}: {str(e)}")
        # logger.debug(traceback.format_exc())
        return {
            "content": f"Error generating interaction: {str(e)}",
            "created_at": datetime.now(pytz.utc),
            "error": True
        }


async def async_generate_scene_interactions_task(id_game_provisional: str):
    """
    Tarea asíncrona para generar las interacciones para cada escena del juego provisional.
    """
    # logger.info(f"Iniciando tarea asíncrona para generar interacciones de escenas para juego ID: {id_game_provisional}")
    # if settings.MODE_TEST:
    #     # logger.warning("Modo de prueba activo: omitiendo creación de juego provisional")
    #     print("init")
    #     await update_game_provisional_status(id_game_provisional, "game_create", 0,
    #                                          "test mode active: skipping file download.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(id_game_provisional, "game_create", 10,
    #                                          "test mode active: skipping file download.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(id_game_provisional, "game_create", 25,
    #                                             "test mode active: skipping content generation.")
    #     await asyncio.sleep(100)
    #
    #     await update_game_provisional_status(id_game_provisional, "game_create", 50,
    #                                             "test mode active: skipping image generation and upload.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(id_game_provisional, "game_create", 80,
    #                                             "test mode active: skipping image generation and upload.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(id_game_provisional, "game_create", 90,
    #                                             "test mode active: skipping saving data.")
    #     await asyncio.sleep(100)
    #     await update_game_provisional_status(id_game_provisional, "game_create", 100,
    #                                             "test mode active: game provisional created successfully.")
    #     return "test mode active: game provisional created successfully"
    try:
        result = await generate_scene_interactions(id_game_provisional)
        # logger.info(f"Tarea de generación de interacciones completada para juego {id_game_provisional} con resultado: {result}")
        return result
    except Exception as e:
        # logger.error(f"Error en tarea async_generate_scene_interactions_task: {str(e)}")
        # logger.debug(traceback.format_exc())
        return f"Error: {str(e)}"


class PersonajeLocacion(BaseModel):
    nombre: str = Field(..., description="Nombre del personaje")
    prompt_descriptivo: str = Field(..., description="Descripción detallada del personaje")


class InteraccionPersonajes(BaseModel):
    tipo: str = Field(..., description="Tipo de conversación: 'one_way' o 'two_way'")
    dialogo: str = Field(..., description="Diálogo de la interacción")


class Options(BaseModel):
    prompt_user_answer: str = Field(..., description="Retroalimentación a la opción de respuesta")
    prompt_user_option: str = Field(..., description="Opción de respuesta que verá el usuario")
    prompt_user_guideline: str = Field(..., description="Opción de respuesta")


class OptionsDialogo(BaseModel):
    prompt_user_question: str = Field(...,
                                      description="Pregunta que hace el personaje secundario al principal puede ser el dialogo 1 y 2 como el two_way en esta parte")
    options: list[Options] = Field(..., description="Opciones de respuesta")
    index_opcion_correcta: int = Field(..., description="Índice de la opción correcta (0 basado en cero)")


class LocationWithCharacters(BaseModel):
    titulo: str = Field(..., description="Nombre de la locación")
    personaje_principal: PersonajeLocacion = Field(..., description="Personaje principal de la locación")
    personaje_secundario: PersonajeLocacion = Field(..., description="Personaje secundario de la locación")
    interaccion: InteraccionPersonajes = Field(..., description="Interacción entre personajes")
    options_dialogo: OptionsDialogo = Field(None, description="Opciones de diálogo si aplica")


class LocationCharactersResponse(BaseModel):
    locations_with_characters: list[LocationWithCharacters] = Field(...,
                                                                    description="Lista de locaciones con personajes e interacciones")


class LocationInfo(BaseModel):
    titulo: str = Field(..., description="Nombre de la locación")
    prompt_user: str = Field(..., description="Descripción detallada de la locación")
    escena: int = Field(..., description="Número de la escena inicial donde aparece la locación")
    escenas_donde_se_repite: list[int] = Field(...,
                                               description="Lista de todas las escenas donde la locación se repite")


class LocationExtractionResponse(BaseModel):
    locations: list[LocationInfo] = Field(..., description="Lista de locaciones extraídas del guión")


async def extract_locations_from_scenes(id_game_provisional: str):
    """
    Extrae información de locaciones a partir de todas las escenas del juego provisional.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        list: Lista de locaciones o string con mensaje de error
    """
    try:
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})
        if not game_provisional_db:
            return "Game provisional not found"

        script = game_provisional_db.get("script")
        num_scenes = game_provisional_db.get("num_scenes")
        if not script or not num_scenes:
            return "Script or num_scenes not found"

        scenes_generated = game_provisional_db.get("scene_interactions", [])

        info_scenes = ""
        for i, scene in enumerate(scenes_generated):
            info_scenes += f"Escena {i + 1}:\n{scene.get('interaction', '')}\n\n"

        type_template = game_provisional_db.get("type_template")
        if type_template:
            type_template_definition = get_template_definition(type_template)
            if type_template_definition:
                info_scenes += f"\n\nDEFINICIÓN DEL TEMPLATE:\n{type_template_definition}\n\nAsegúrate de que las locaciones generadas sigan las reglas específicas del template mencionado arriba."

        prompt = (
            "Analiza todas las escenas del siguiente guion y extrae la información de las locaciones en el siguiente formato para cada locación encontrada:\n"
            "- titulo: nombre de la locación\n"
            "- prompt_user: descripción de la situación que ocurre en la locación. El resultado debe ser una descripción situacional similar al ejemplo dado, mencionando personajes, qué hacen y su ubicación, pero generada dinámicamente según la escena.\n"
            "- escena: escena inicial donde aparece\n"
            "- escenas_donde_se_repite: todas las escenas donde se repite\n"
            "Devuelve una lista de objetos JSON, uno por cada locación.\n"
            f"Escenas:\n{info_scenes}"
        )

        locations_response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system",
                 "content": "Eres un experto en análisis de guiones para videojuegos. solo deben ser 3 locaciones"},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4.1",
            response_format=LocationExtractionResponse,
            user_id=None,
            type_generation="extract locations from scenes"
        )

        # Verificar si hubo error en la respuesta
        if locations_response is None or isinstance(locations_response, str):
            return f"Error in OpenAI response: {locations_response}"

        # Verificar que el objeto tenga el atributo locations
        if not hasattr(locations_response, 'locations'):
            return "No locations attribute found in response"

        # Verificar que locations no esté vacío
        if not locations_response.locations:
            return "No locations found in response"

        # Convertir objetos LocationInfo a diccionarios para el almacenamiento
        locations_dict = []
        for location in locations_response.locations:
            if hasattr(location, 'dict'):
                locations_dict.append(location.dict())
            elif hasattr(location, 'model_dump'):
                # Para versiones más nuevas de Pydantic
                locations_dict.append(location.model_dump())
            else:
                # Si ya es un diccionario
                locations_dict.append(location)

        return locations_dict
    except Exception as e:
        print(traceback.format_exc())
        return f"Error extracting locations: {str(e)}"


async def extract_characters_and_interactions_for_locations(id_game_provisional: str):
    """
    Extrae personajes e interacciones para cada locación del juego provisional.
    Esta función se ejecuta después de extract_locations_from_scenes.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        str: Mensaje indicando el resultado de la operación
    """
    try:
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})
        if not game_provisional_db:
            return "Game provisional not found"

        script = game_provisional_db.get("script")
        locations = game_provisional_db.get("locations")
        template_type = game_provisional_db.get("type_template", "").lower()

        scenes_generated = game_provisional_db.get("scene_interactions", [])

        if not scenes_generated:
            return "No scenes interactions found in game provisional"

        info_scenes = ""
        for i, scene in enumerate(scenes_generated):
            info_scenes += f"Escena {i + 1}:\n{scene.get('interaction', '')}\n\n"

        if not script:
            return "Script not found in game provisional"

        if not locations:
            return "Locations not found. Please run extract_locations_from_scenes first"

        # Verificar si locations es un string de error
        if isinstance(locations, str):
            return f"Locations extraction failed: {locations}"

        # Verificar que locations sea una lista
        if not isinstance(locations, list):
            return f"Invalid locations format: expected list, got {type(locations)}"

        # Crear el prompt para extraer personajes e interacciones
        locations_list = "\n".join(
            [f"- {loc.get('titulo', 'Sin título')}: {loc.get('prompt_user', 'Sin descripción')}" for loc in locations if
             isinstance(loc, dict)])

        type_template = game_provisional_db.get("type_template", None)
        template_select = get_template_definition(type_template)
        if template_select:
            locations_list += f"\n\nDEFINICIÓN DEL TEMPLATE:\n{template_select}\n\nAsegúrate de que los personajes e interacciones generados sigan las reglas específicas del template mencionado arriba."

        if type_template == "learn":
            prompt = (
                f"Analiza el siguiente guion y las locaciones extraídas. Para cada locación, identifica y crea personajes e interacciones. el tipo de interacción debe concordar con lo deseado \n\n"
                f"INFO DE LAS ESCENAS:\n{info_scenes}\n\n"
                f"LOCACIONES EXISTENTES:\n{locations_list}\n\n"
                f"Para cada locación, devuelve un objeto JSON con:\n"
                f"- titulo: nombre de la locación (debe coincidir exactamente con las locaciones existentes)\n"
                f"- personaje_principal: objeto con 'nombre' y 'prompt_descriptivo' (debe ser el mismo personaje en TODAS las locaciones)\n"
                f"- personaje_secundario: objeto con 'nombre' y 'prompt_descriptivo' (diferente para cada locación)\n"
                f"- interaccion: objeto con:\n"
                f"  * tipo: "
                f"    - 'one_way' (solo habla el secundario al principal). solo para el tipo de template (learn)\n"
                f"    - 'two_way' (diálogo entre principal y secundario). solo para el tipo de template (learn)\n"
                f"  * dialogo: \n"
                f"    - Para 'one_way': un diálogo corto que dice el secundario al principal solo para el tipo de template (learn)\n"
                f"    - Para 'two_way': formato '1 texto 2 texto 1 texto' donde 1=principal y 2=secundario de 4 a 6 interacciones solo para el tipo de template (learn)\n\n"
                f"REGLAS IMPORTANTES:\n"
                f"- El personaje principal debe ser el MISMO en todas las locaciones\n"
                f"- Cada locación tiene exactamente 1 personaje secundario (diferente por locación)\n"
                f"- Exactamente 1 interacción por locación\n"
                f"- Los tipos son: 'one_way' , 'two_way'\n\n"
                f"EJEMPL0 DE RESPUESTA:\n"
                f"[\n"
                f"  {{\n"
                f"    'titulo': 'Locación 1',\n"
                f"    'personaje_principal': {{'nombre': 'Nombre Principal', 'prompt_descriptivo': 'Descripción del personaje principal'}},\n"
                f"    'personaje_secundario': {{'nombre': 'Nombre Secundario', 'prompt_descriptivo': 'Descripción del personaje secundario'}},\n"
                f"    'interaccion': {{'tipo': 'one_way', 'dialogo': 'Diálogo del secundario al principal'}}\n"
                f"  }},\n"
                f"  {{\n"
                f"    'titulo': 'Locación 2',\n"
                f"    'personaje_principal': {{'nombre': 'Nombre Principal', 'prompt_descriptivo': 'Descripción del personaje principal'}},\n"
                f"    'personaje_secundario': {{'nombre': 'Nombre Secundario', 'prompt_descriptivo': 'Descripción del personaje secundario'}},\n"
                f"    'interaccion': {{'tipo': 'two_way', 'dialogo': '1 Hola 2 Hola, ¿cómo estás? 1 Bien, ¿y tú? 2 Muy bien, gracias.'}}\n"
                f"  }}\n"
                f"]\n\n"
            )
        elif type_template == "trivia":
            prompt = (
                f"IMPORTANTE: El template es TRIVIA. TODAS las escenas deben tener interacción de tipo 'option_multiple', siguiendo exactamente el formato del ejemplo. No incluyas interacciones de tipo 'two_way' ni 'one_way'. Si no sigues el formato, el resultado será rechazado.\n\n"
                f"Ejemplo de interacción option_multiple:\nPrincipal: Mago\nSecundario: Aprendiz\ninteracción:\n1: Hola, ¿listo para la pregunta?\\n2: Sí, adelante.\\n1: ¿Cuál es la capital de Francia?\nOpciones:\n  - París\n  - Madrid\n  - Berlín\nRespuestas:\n  - París: ¡Correcto! París es la capital de Francia.\n  - Madrid: Incorrecto. Madrid es la capital de España.\n  - Berlín: Incorrecto. Berlín es la capital de Alemania.\n\n"
                f"Estructura exacta:\n- Evento inicial\n- Escena 1\n  - Locación 1\n  - Personaje principal\n  - Personaje secundario\n  - Interacción (open_question): [formato del ejemplo]\n  - Evento después de la interacción\n- Escena 2\n  - Locación 2\n  - Personaje principal\n  - Personaje secundario\n  - Interacción (open_question): [formato del ejemplo]\n- Escena 3\n  - Locación 3\n  - Personaje principal\n  - Personaje secundario\n  - Interacción (open_question): [formato del ejemplo]\n  - Evento final\n\n"
                f"No incluyas ningún otro tipo de interacción. Sigue el formato del ejemplo al pie de la letra.\n\n"
                f"INFO DE LAS ESCENAS:\n{info_scenes}\n\nLOCACIONES EXISTENTES:\n{locations_list}\n\n{template_select}"
            )
        elif type_template == "evaluation":
            prompt = (
                f"IMPORTANTE: El template es EVALUATION.\n"
                f"- Las tres escenas deben ser de tipo 'open_question' (el jugador responde libremente a una pregunta del personaje).\n"
                f"- No incluyas interacciones de tipo 'option_multiple', 'one_way' ni 'two_way'.\n"
                f"- Si no sigues el formato, el resultado será rechazado.\n\n"
                f"EJEMPLOS:\n"
                f"Interacción open_question:\n"
                f"- open_question: Diálogo donde el jugador puede responder libremente a una pregunta o comentario del personaje.\n"
                f"  Ejemplo:\n"
                f"    interacción:\n"
                f"Opciones de dialgo (ptions_dialog):\n"
                f"   pregunta (prompt_user_question): \n"
                f"  1: Hola, ¿listo para la pregunta?\n"
                f"  2: Sí, adelante.\n"
                f"  1: ¿Cuál es la capital de Francia?\n"
                f"  2: [Respuesta libre del jugador]\n\n"
                f"  Opciones de guia (prompt_user_guideline) :\n"
                f"    - París\n"
                f"    - Madrid\n"
                f"    - Berlín\n"
                f"  Respuestas de las opciones (prompt_user_answer) :\n"
                f"    - París: ¡Correcto! París es la capital de Francia.\n"
                f"    - Madrid: Incorrecto. Madrid es la capital de España.\n"
                f"    - Berlín: Incorrecto. Berlín es la capital de Alemania.\n\n"
                f"Estructura de las opciones de guía y respuestas:\n"
                f"- prompt_user_question es el diálogo previo con la pregunta que se quiere preguntar.\n"
                f"- options es una lista de objetos, cada uno con:\n"
                f"  - prompt_user_guideline: la respuesta esperada o patrón a evaluar (puede ser texto libre, no solo opción cerrada).\n"
                f"  - prompt_user_answer: la retroalimentación que se da si la respuesta del usuario coincide (o es similar) con el guideline.\n\n"
                f"La lógica debe ser: si la respuesta del usuario es similar a alguno de los prompt_user_guideline, se responde con el prompt_user_answer correspondiente. Si no hay coincidencia, se puede dar la retroalimentación genérica o la del guideline más cercano.\n\n"
                f"ESTRUCTURA EXACTA:\n"
                f"- Evento inicial\n"
                f"- Escena 1\n"
                f"  - Locación 1\n"
                f"  - Personaje principal\n"
                f"  - Personaje secundario\n"
                f"  - Interacción (open_question): [formato del ejemplo]\n"
                f"  - Evento después de la interacción\n"
                f"- Escena 2\n"
                f"  - Locación 2\n"
                f"  - Personaje principal\n"
                f"  - Personaje secundario\n"
                f"  - Interacción (open_question): [formato del ejemplo]\n"
                f"- Escena 3\n"
                f"  - Locación 3\n"
                f"  - Personaje principal\n"
                f"  - Personaje secundario\n"
                f"  - Interacción (open_question): [formato del ejemplo]\n"
                f"  - Evento final\n\n"
                f"No incluyas ningún otro tipo de interacción. Sigue el formato del ejemplo al pie de la letra.\n\n"
                f"INFO DE LAS ESCENAS:\n{info_scenes}\n\n"
                f"LOCACIONES EXISTENTES:\n{locations_list}\n\n"
                f"{template_select}"
            )
        elif type_template == "solve":
            prompt = (
                f"IMPORTANTE: El template es SOLVE. Las dos primeras escenas deben tener interacción de tipo 'two_way' (diálogo bidireccional entre personajes, orientado a analizar y desarrollar la solución). La tercera escena debe ser de tipo 'open_question' (el jugador propone una solución libremente). No incluyas interacciones de tipo 'option_multiple' ni 'one_way'. Si no sigues el formato, el resultado será rechazado.\n\n"
                f"Ejemplo de interacción two_way:\nPrincipal: Mentor\nSecundario: Aprendiz\ninteracción:\n1: ¿Qué harías en esta situación?\\n2: Buscaría ayuda.\\n1: ¿Por qué?\\n2: Porque es importante aprender de otros.\n\n"
                f"Ejemplo de interacción open_question:\nPrincipal: Mentor\nSecundario: Aprendiz\ninteracción:\n1: ¿Cuál crees que es la mejor solución?\\n2: Yo propondría...\n\n"
                f"Estructura exacta:\n- Evento inicial\n- Escena 1\n  - Locación 1\n  - Personaje principal\n  - Personaje secundario\n  - Interacción (two_way): [formato del ejemplo]\n  - Evento después de la interacción\n- Escena 2\n  - Locación 2\n  - Personaje principal\n  - Personaje secundario\n  - Interacción (two_way): [formato del ejemplo]\n- Escena 3\n  - Locación 3\n  - Personaje principal\n  - Personaje secundario\n  - Interacción (open_question): [formato del ejemplo]\n  - Evento final\n\n"
                f"No incluyas ningún otro tipo de interacción. Sigue el formato del ejemplo al pie de la letra.\n\n"
                f"INFO DE LAS ESCENAS:\n{info_scenes}\n\nLOCACIONES EXISTENTES:\n{locations_list}\n\n{template_select}"
            )

        elif type_template == "storytelling":
            prompt = (
                f"Analiza el siguiente guion y las locaciones extraídas. Para cada locación, identifica y crea personajes e interacciones. el tipo de interacción debe concordar con lo deseado \n\n"
                f"INFO DE LAS ESCENAS:\n{info_scenes}\n\n"
                f"LOCACIONES EXISTENTES:\n{locations_list}\n\n"
                f"Para cada locación, devuelve un objeto JSON con:\n"
                f"- titulo: nombre de la locación (debe coincidir exactamente con las locaciones existentes)\n"
                f"- personaje_principal: objeto con 'nombre' y 'prompt_descriptivo' (debe ser el mismo personaje en TODAS las locaciones)\n"
                f"- personaje_secundario: objeto con 'nombre' y 'prompt_descriptivo' (diferente para cada locación)\n"
                f"- interaccion: objeto con:\n"
                f"  * tipo: "
                f"    - 'one_way' (solo habla el secundario al principal). solo para el tipo de template (learn)\n"
                f"    - 'two_way' (diálogo entre principal y secundario). solo para el tipo de template (learn)\n"
                f"  * dialogo: \n"
                f"    - Para 'one_way': un diálogo corto que dice el secundario al principal solo para el tipo de template (learn)\n"
                f"    - Para 'two_way': formato '1 texto 2 texto 1 texto' donde 1=principal y 2=secundario de 4 a 6 interacciones solo para el tipo de template (learn)\n\n"
                f"REGLAS IMPORTANTES:\n"
                f"- El personaje principal debe ser el MISMO en todas las locaciones\n"
                f"- Cada locación tiene exactamente 1 personaje secundario (diferente por locación)\n"
                f"- Exactamente 1 interacción por locación\n"
                f"- Los tipos son: 'one_way' , 'two_way'\n\n"
                f"EJEMPL0 DE RESPUESTA:\n"
                f"[\n"
                f"  {{\n"
                f"    'titulo': 'Locación 1',\n"
                f"    'personaje_principal': {{'nombre': 'Nombre Principal', 'prompt_descriptivo': 'Descripción del personaje principal'}},\n"
                f"    'personaje_secundario': {{'nombre': 'Nombre Secundario', 'prompt_descriptivo': 'Descripción del personaje secundario'}},\n"
                f"    'interaccion': {{'tipo': 'one_way', 'dialogo': 'Diálogo del secundario al principal'}}\n"
                f"  }},\n"
                f"  {{\n"
                f"    'titulo': 'Locación 2',\n"
                f"    'personaje_principal': {{'nombre': 'Nombre Principal', 'prompt_descriptivo': 'Descripción del personaje principal'}},\n"
                f"    'personaje_secundario': {{'nombre': 'Nombre Secundario', 'prompt_descriptivo': 'Descripción del personaje secundario'}},\n"
                f"    'interaccion': {{'tipo': 'two_way', 'dialogo': '1 Hola 2 Hola, ¿cómo estás? 1 Bien, ¿y tú? 2 Muy bien, gracias.'}}\n"
                f"  }}\n"
                f"]\n\n"
            )
        else:
            prompt = (
                f"Analiza el siguiente guion y las locaciones extraídas. Para cada locación, identifica y crea personajes e interacciones. el tipo de interacción debe concordar con lo deseado \n\n"
                f"INFO DE LAS ESCENAS:\n{info_scenes}\n\n"
                f"LOCACIONES EXISTENTES:\n{locations_list}\n\n"
                f"Para cada locación, devuelve un objeto JSON con:\n"
                f"- titulo: nombre de la locación (debe coincidir exactamente con las locaciones existentes)\n"
                f"- personaje_principal: objeto con 'nombre' y 'prompt_descriptivo' (debe ser el mismo personaje en TODAS las locaciones)\n"
                f"- personaje_secundario: objeto con 'nombre' y 'prompt_descriptivo' (diferente para cada locación)\n"
                f"- interaccion: objeto con:\n"
                f"  * tipo: "
                f"    - 'one_way' (solo habla el secundario al principal). \n"
                f"    - 'two_way' (diálogo entre principal y secundario). \n"
                f"    - 'option_multiple' (el principal elige entre varias opciones para responder al secundario, no numeradas). \n\n"
                f"  * dialogo o Opciones de dialogo según el tipo:\n"
                f"    - Para 'one_way': un diálogo corto que dice el secundario al principal \n"
                f"    - Para 'two_way': formato '1 texto 2 texto 1 texto' donde 1=principal y 2=secundario de 4 a 6 interracciones \n"
                f"    - Para 'option_multiple':\n"
                f"      ** prompt_user_question: interacción llevando hacia la pregunta antes de las opciones que hace el secundario al principal puede ser formato '1 texto 2 texto 1 texto' donde 1=principal y 2=secundario de 4 a 6 interracciones \n"
                f"      ** opciones: opciones de respuesta\n"
                f"        ** prompt_user_guideline: opcion de respuesta\n"
                f"        ** prompt_user_answer: retroalimentación a la opcion de respuesta\n"
                f"      ** Index de la opcion correcta (0 basado en cero)\n\n"

                f"REGLAS IMPORTANTES:\n"
                f"- El personaje principal debe ser el MISMO en todas las locaciones\n"
                f"- Cada locación tiene exactamente 1 personaje secundario (diferente por locación)\n"
                f"- Exactamente 1 interacción por locación\n"
                f"- Los tipos son: 'one_way' , 'two_way' , 'option_multiple'\n\n"
            )

        characters_response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system",
                 "content": "Eres un experto en análisis de guiones y creación de personajes para videojuegos. Analiza cuidadosamente el guión y crea personajes consistentes con interacciones naturales. y que acople al template"},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4.1",
            response_format=LocationCharactersResponse,
            user_id=None,
            max_tokens=15000,
            type_generation="extract characters and interactions for locations"
        )

        # Verificar si hubo error en la respuesta
        if not characters_response or isinstance(characters_response, str):
            return f"Error in characters OpenAI response: {characters_response}"

        # Convertir la respuesta si es necesario
        if hasattr(characters_response, 'locations_with_characters'):
            locations_with_chars = characters_response.locations_with_characters
        else:
            return "No characters data found in response"

        if not template_type:
            template_type = "learn"  # O el valor por defecto que corresponda

        for loc in locations_with_chars:
            if hasattr(loc, 'interaccion') and hasattr(loc.interaccion, 'tipo'):
                is_valid, expected_types = await validate_interaction_type(
                    template_type,
                    loc.interaccion.tipo
                )
                if not is_valid:
                    print(
                        f"Invalid interaction type '{loc.interaccion.tipo}' for template '{template_type}'. Expected types: {expected_types}")
                    return f"error interaction type '{loc.interaccion.tipo}' for template '{template_type}'. Expected types: {expected_types}"
        # Actualizar las locaciones existentes con la información de personajes
        updated_locations = []

        for location in locations:
            if not isinstance(location, dict):
                continue

            # Buscar la información de personajes para esta locación
            char_info = None
            for loc_chars in locations_with_chars:
                # Manejar tanto objetos Pydantic como diccionarios
                loc_title = loc_chars.titulo if hasattr(loc_chars, 'titulo') else loc_chars.get('titulo', '')
                if loc_title.lower().strip() == location.get('titulo', '').lower().strip():
                    char_info = loc_chars
                    break

            # Crear la locación actualizada
            updated_location = location.copy()
            if char_info:
                # Convertir objetos Pydantic a diccionarios si es necesario
                if hasattr(char_info, 'dict'):
                    char_dict = char_info.dict()
                    updated_location['personaje_principal'] = char_dict.get('personaje_principal')
                    updated_location['personaje_secundario'] = char_dict.get('personaje_secundario')
                    updated_location['interaccion'] = char_dict.get('interaccion')
                    if char_dict.get('interaccion', {}).get('tipo') == 'option_multiple' and char_dict.get(
                            'options_dialogo'):
                        options_dialogo = char_dict['options_dialogo']
                        for option in options_dialogo['options']:
                            if 'prompt_user_guideline' in option:
                                del option['prompt_user_guideline']
                        updated_location['options_dialogo'] = options_dialogo
                else:
                    updated_location['personaje_principal'] = char_info.get('personaje_principal')
                    updated_location['personaje_secundario'] = char_info.get('personaje_secundario')
                    updated_location['interaccion'] = char_info.get('interaccion')
                    updated_location['options_dialogo'] = char_info.get('options_dialogo')

            updated_locations.append(updated_location)

            # Validar que la clave 'personaje_principal' exista en updated_location
            if 'personaje_principal' not in updated_location:
                import logging
                logging.error(f"Falta la clave 'personaje_principal' en updated_location: {updated_location}")
                raise ValueError(f"Falta la clave 'personaje_principal' en updated_location: {updated_location}")

        # Actualizar la base de datos
        await db["game_provisional"].update_one(
            {"_id": ObjectId(id_game_provisional)},
            {"$set": {
                "locations": updated_locations,
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        return f"Successfully added characters and interactions to {len(updated_locations)} locations"

    except Exception as e:
        print(traceback.format_exc())
    return f"Failed to extract characters and interactions: {str(e)}"


async def create_character_service(character: SchemaCreateCharacter, user_id: str, game_id: str,
                                   file: UploadFile | None = None):
    try:

        character_db = Character(**character.dict())
        character_db.created_by = user_id
        character_db.updated_by = user_id

        character_created = await db["character"].insert_one(character_db.dict())

        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            if game_db.get('characters_id'):
                game_db["characters_id"].append(str(character_created.inserted_id))
            else:
                game_db["characters_id"] = [str(character_created.inserted_id)]
            await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})

        character_db_state = CharacterGLIC(**character.dict())

        if character.state_game:
            state_game = await get_state_game_by_id(character.state_game)
        else:
            state_game = await get_state_game_by_game_id(game_id)

        if file:
            file_content = file.file.read()
            if not file_content:
                return "File is empty"
            file.file.seek(0)  # Reset file pointer to the beginning
            if file.content_type not in ["image/jpeg", "image/png"]:
                return "File type not allowed"
            if file.content_type == "image/jpeg":
                file_name = f"characters-reference/{uuid4()}.jpg"
            elif file.content_type == "image/png":
                file_name = f"characters-reference/{uuid4()}.png"
            else:
                return "File type not allowed"
            img_byte_arr = BytesIO(file_content)
            img_byte_arr.seek(0)

            url_image_reference = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=file_name,
                size=(512, 512),
            )
            character_db_state.image_reference = url_image_reference

        if state_game:
            await create_state_glic(
                element_id=str(character_created.inserted_id),
                type_element="character",
                state=state_game['_id'],
                order=state_game['order'],
                created_by=user_id,
                data=character_db_state.dict(),
            )

        task_celery =  generate_character_task.delay(
            _character_id=str(character_created.inserted_id),
            _user_id=user_id,
            _task_id="",
            _location_id=character.location_id,
            _state_game_id=state_game['_id'],
            _game_id=game_id,
        )

        if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
            return character_db
    except Exception as e:
        print(f"Error in create character service: {str(e)}")
        return "Error: " + str(e)


async def change_character_principal_game_service(
        game_id: str, character_principal: str, user_id: str
):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if game_db:
            game_db["character_principal"] = character_principal
            await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': game_db})

            return game_db
    except Exception as e:
        print(f"Error changing character principal game service: {str(e)}")
        return f"Error: {str(e)}"


async def create_location_service(location: SchemaCreateLocation, user_id: str, file: UploadFile = None):
    """
    Create a location.
    """

    try:
        location_schema = Location(**location.dict())
        location_schema.created_by = user_id
        location_schema.updated_by = user_id
        location_created = await db['location'].insert_one(location_schema.dict())

        game_db = await db['game'].find_one({'_id': ObjectId(location.game_id)})
        if game_db:
            if game_db.get('locations_id'):
                game_db["locations_id"].append(str(location_created.inserted_id))
            else:
                game_db["locations_id"] = [str(location_created.inserted_id)]
            await db['game'].update_one({'_id': ObjectId(location.game_id)}, {'$set': game_db})

        location_db_state = LocationGLIC(**location.dict())

        if location.state_game:
            state_game = await get_state_game_by_id(location.state_game)
        else:
            state_game = await get_state_game_by_game_id(location.game_id)

        # Procesar la imagen de referencia si se proporciona
        if file:
            file_content = file.file.read()
            if not file_content:
                return "File is empty"
            file.file.seek(0)  # Reset file pointer to the beginning
            if file.content_type not in ["image/jpeg", "image/png"]:
                return "File type not allowed, only jpeg and png"
            if file.content_type == "image/jpeg":
                file_name = f"locations-reference/{uuid4()}.jpg"
            elif file.content_type == "image/png":
                file_name = f"locations-reference/{uuid4()}.png"
            else:
                return "File type not allowed, only jpeg and png"
            img_byte_arr = BytesIO(file_content)
            img_byte_arr.seek(0)

            from utils import upload_image
            url_image_reference = upload_image(
                img_byte_arr=img_byte_arr,
                file_name=file_name,
                size=(512, 512),
            )
            location_db_state.image_reference = url_image_reference

        if state_game:
            await create_state_glic(
                element_id=str(location_created.inserted_id),
                type_element="location",
                state=state_game["_id"],
                order=state_game["order"],
                created_by=user_id,
                data=location_db_state.dict(),
            )

        # Obtener el provisional_id del game
        game_data = await db['game'].find_one({'_id': ObjectId(location.game_id)})
        provisional_id = game_data.get('provisional_id', '') if game_data else ''

        # Crear la tarea
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=provisional_id,
            _element_type="game_provisional",
            _process="create_location",
        )

        task_celery = generate_location_task.delay(
            _location_id=str(location_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db['_id']),
            _state_game_id=state_game["_id"]
        )

        # Actualizar la tarea con el ID de celery
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        if location_db := await db['location'].find_one({"_id": location_created.inserted_id}):
            return location_db
    except Exception as e:
        print(f"Error in create location service: {e}")
        print(traceback.print_exc())
        return "Location not created"


async def create_game_service(user_id: str):
    try:
        game_db = Game(
            updated_by=user_id,
            created_by=user_id,
            version=2,
            code_access=await generate_code_access_game_service(),
        )
        if game_created := await db['game'].insert_one(game_db.dict()):
            # Crear el estado inicial del juego
            # TODO: Comentar cuando se tenga el servicio de tareas
            await create_state_game(
                game_id=str(game_created.inserted_id), order=1, created_by=user_id
            )
            return await db['game'].find_one({'_id': game_created.inserted_id})
    except Exception as e:
        print(f"Error creating game service: {str(e)}")
        return f"Error: {str(e)}"


async def create_event_service(event: SchemaCreateEvent, user_id: str):
    event_schema = Event(
        name=event.name,
        prompt_user_image=event.prompt_user_image,
        prompt_user_text=event.prompt_user_text,
        type_conversation=event.type_conversation,
        option_number=event.option_number,
        character_id=event.character_id,
        character_principal="",
        state_game_init=event.state_game_init,
        state_game_end=event.state_game_end,
        location_state_game_init=event.location_state_game_init,
        location_state_game_end=event.location_state_game_end,
        text_image=event.prompt_user_text,
        image=event.image,
        game_id=event.game_id,
        created_by=user_id,
        updated_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_final=event.is_final,
        is_equal_option_number=event.is_equal_option_number,
    )

    event_created = await db["event"].insert_one(event_schema.dict())

    if event.prompt_user_image and not event.image:
        task_celery = generate_image_event_task.delay(
            _game_id=event.game_id,
            _event_id=str(event_created.inserted_id),
            _state_game=event.state_game_init,
            _user_id=user_id,
            _prompt_user_image=event.prompt_user_image,
            _task_id="",
        )

        event_db = await db["event"].find_one({"_id": event_created.inserted_id})
        event_db["_id"] = str(event_db["_id"])
        return event_db

    event_db = await db["event"].find_one({"_id": event_created.inserted_id})
    event_db["_id"] = str(event_db["_id"])
    return event_db


async def generate_code_access_game_service():
    while True:
        code = ''.join(
            random.choices(string.ascii_lowercase, k=2) + random.choices(string.digits, k=2)
        )
        code = ''.join(random.sample(code, len(code)))  # Shuffle the characters

        existing_code = await db['game'].find_one({'code_access': code})

        if not existing_code:
            return code


async def create_game_by_provisional(id_game_provisional: str):
    """
    Crea un juego a partir de un juego provisional.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        str: Mensaje indicando el resultado de la operación
    """
    try:
        # Aquí iría la lógica para crear el juego a partir del provisional
        # Por ejemplo, copiar los datos necesarios y crear un nuevo registro en la colección de juegos
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})

        game_db = await create_game_service(user_id=str(game_provisional_db.get("created_by", "anonymous")), )

        game_update_db = await db["game"].update_one({"_id": game_db.get("_id")}, {"$set": {
            "title": game_provisional_db.get("title"),
            "history": game_provisional_db.get("script"),
            "image": game_provisional_db.get("image"),
            "image_minimalist": game_provisional_db.get("image"),
            "created_by": game_provisional_db.get("created_by", "anonymous"),
            "updated_by": game_provisional_db.get("created_by", "anonymous"),
            "provisional_id": str(game_provisional_db.get("_id")),
            "category_id": game_provisional_db.get("category"),
            "is_active": True
        }})

        state_game_db = await db["state_game"].find_one({"game_id": str(game_db.get("_id")), "order": 1})

        if not state_game_db:
            return "StateGame not found for the created game"

        # crear locaciones de las locaciones del juego provisional
        locations = game_provisional_db.get("locations", [])

        locations_db = []
        characters_db = []
        states_game_db = [str(state_game_db.get("_id", None))]

        # logger.info(f"Creating game with {len(locations)} locations from provisional")
        for i, location in enumerate(locations):

            if i >= 1:
                state_game_new = await create_state_game(
                    game_id=str(game_db.get("_id")),
                    order=i + 1,
                    created_by=str(game_provisional_db.get("created_by", "anonymous"))
                )

                states_game_db.append(str(state_game_new.get("_id", None)))

                await deactivate_character_service(characters_db[0], str(state_game_new.get("_id", None)), True)

            location_db = await create_location_service(
                location=SchemaCreateLocation(
                    title=location["titulo"],
                    prompt_user=location["prompt_user"],
                    game_id=str(game_db.get("_id")),
                    state_game=states_game_db[i],
                ),
                user_id=str(game_provisional_db.get("created_by", "anonymous")),
                file=None
            )

            locations_db.append(str(location_db.get("_id", None)))

            if i == 0:
                if "personaje_principal" not in location:
                    import logging
                    logging.error(f"Falta la clave 'personaje_principal' en location: {location}")
                    raise ValueError(f"Falta la clave 'personaje_principal' en location: {location}")
                character_principal_db = await create_character_service(
                    character=SchemaCreateCharacter(
                        name=location["personaje_principal"]["nombre"],
                        prompt_user=location["personaje_principal"]["prompt_descriptivo"],
                        prompt_user_dialog=None,
                        conversation_type="none",
                        options_dialog=None,
                        game_id=str(game_db.get("_id")),
                        location_id=str(location_db.get("_id")),
                        state_game=str(state_game_db.get("_id"))
                    ),
                    user_id=game_provisional_db.get("created_by", "anonymous"),
                    game_id=str(game_db.get("_id")),
                    file=None
                )

                characters_db.append(str(character_principal_db.get("_id", None)))

                location_change_character_db = await change_character_principal_game_service(
                    str(game_db.get("_id")), str(character_principal_db.get("_id")),
                    game_provisional_db.get("created_by", "anonymous")
                )

            character_db = await create_character_service(
                character=SchemaCreateCharacter(
                    name=location["personaje_secundario"]["nombre"],
                    prompt_user=location["personaje_secundario"]["prompt_descriptivo"],
                    prompt_user_dialog=location["interaccion"]["dialogo"],
                    conversation_type=location["interaccion"]["tipo"],
                    options_dialog=location.get("options_dialogo", None),
                    game_id=str(game_db.get("_id")),
                    location_id=str(location_db.get("_id")),
                    state_game=states_game_db[i]
                ),
                user_id=game_provisional_db.get("created_by", "anonymous"),
                game_id=str(game_db.get("_id")),
                file=None
            )

            characters_db.append(str(character_db.get("_id", None)))

            await generate_location_image(
                _location_id=str(location_db.get("_id")),
                _user_id=str(game_provisional_db.get("created_by", "anonymous")),
                _state_game_id=states_game_db[i],
                _type_game="2d",
            )

            # # Crear configuración de la locación con posicionamiento de personajes
            # def generate_random_position():
            #     """Genera una posición aleatoria en la cuadrícula de 60x60"""
            #     return {
            #         "index": 0,  # Índice de la cuadrícula
            #         "X": random.randint(28, 35),
            #         "Y": random.randint(28, 35)
            #     }
            #
            # # Configuración de la locación con personajes posicionados
            # location_configuration = {
            #     "characterScale": 1.6,
            #     "GridX": 0,
            #     "GridY": 0,
            #     "GridPlaneSize": 0,  # Cuadrícula de 60x60
            #     "Characters": [
            #         {
            #             "characterId": str(character_principal_db.get("_id")),
            #             **generate_random_position()
            #         },
            #         {
            #             "characterId": str(character_db.get("_id")),
            #             **generate_random_position()
            #         }
            #     ],
            #     "items": []  # Por ahora sin items, se pueden agregar después
            # }
            #
            # location_state_db = await db["state_glic"].find_one(
            #     {"element_id": str(location_db.get("_id")), "type_element": "location"}
            # )
            #
            # location_state_db["data"]["configuration"] = location_configuration
            # await db["state_glic"].update_one(
            #     {"_id": location_state_db["_id"]},
            #     {"$set": {
            #         "data": location_state_db["data"],
            #         "updated_at": datetime.now(pytz.utc)
            #     }}
            # )

            event_current = game_provisional_db.get("events_generated", False)

            if event_current:

                event_current = event_current[i]

                state_game_final = None
                location_state_game_end = None

                if i == 0:
                    character_id = ""
                    state_game_init = states_game_db[i]
                    location_stata_game_init = locations_db[i]
                    location_state_game_end = locations_db[i]
                elif i == len(locations) - 1:
                    character_id = characters_db[i]
                    state_game_init = states_game_db[i - 1]
                    state_game_final = states_game_db[i]
                    location_stata_game_init = locations_db[i - 1]
                    location_state_game_end = locations_db[i]
                else:
                    state_game_init = states_game_db[i - 1]
                    state_game_final = states_game_db[i]
                    location_stata_game_init = locations_db[i - 1]
                    location_state_game_end = locations_db[i]
                    character_id = characters_db[i]

                # Crear el evento usando la función existente create_event_service

                # Crear el evento usando el servicio existente
                created_event = await create_event_service(
                    event=SchemaCreateEvent(
                        name=event_current.get("event_name", f"Event for {location['titulo']}"),
                        prompt_user_image=event_current.get("prompt_image", "A detailed image of the scene"),
                        prompt_user_text=event_current.get("prompt_text", "Description of the event"),
                        character_id=character_id,
                        type_conversation=location["interaccion"]["tipo"],
                        option_number=location.get("options_dialogo", {}).get("index_opcion_correcta", 0),
                        state_game_init=state_game_init,
                        state_game_end=state_game_final,
                        location_state_game_init=location_stata_game_init,
                        location_state_game_end=location_state_game_end,
                        game_id=str(game_db.get("_id")),
                        is_final=False,
                        audio_mp3=None,
                        audio=None
                    ),
                    user_id=game_provisional_db.get("created_by", "anonymous")
                )

                # Actualizar el juego con el evento inicial
                if i == 0:
                    await db["game"].update_one(
                        {"_id": ObjectId(str(game_db.get("_id")))},
                        {"$set": {"event_init": created_event.get("_id")}}
                    )

                if i == len(locations) - 1:
                    event_current = game_provisional_db.get("events_generated", False)
                    event_current = event_current[i + 1]
                    # Crear el evento usando la función existente create_event_service
                    event_data = SchemaCreateEvent(
                        name=event_current.get("event_name", f"Event for {location['titulo']}"),
                        prompt_user_image=event_current.get("prompt_image", "A detailed image of the scene"),
                        prompt_user_text=event_current.get("prompt_text", "Description of the event"),
                        character_id=characters_db[i + 1],
                        type_conversation=location["interaccion"]["tipo"],
                        option_number=0,
                        state_game_init=states_game_db[i],
                        state_game_end="",
                        location_state_game_init=locations_db[i],
                        location_state_game_end="",
                        game_id=str(game_db.get("_id")),
                        is_final=True
                    )

                    # Crear el evento usando el servicio existente
                    created_event = await create_event_service(
                        event=event_data,
                        user_id=game_provisional_db.get("created_by", "anonymous")
                    )

                    await db["game"].update_one(
                        {"_id": ObjectId(str(game_db.get("_id")))},
                        {"$set": {"event_final": str(created_event.get("_id"))}}
                    )

        # update game provisional with the created game id
        await db["game_provisional"].update_one(
            {"_id": ObjectId(id_game_provisional)},
            {"$set": {
                "game_id": str(game_db.get("_id")),
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        return "Game created successfully from provisional data"

    except Exception as e:
        print(traceback.format_exc())
        return f"Failed to create game from provisional: {str(e)}"


async def new_interaction_character_service(
        location_id: str,
        game_id: str,
        character_id: str,
        conversation_type: str,
        conversation: list[ConversationsCharacter],
        option: list[ConversationsOptionsCharacter],
        user_id: str,
        options_dialog: dict = None,
        state_game: str = None,
):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise Exception("error character not found")

    if not state_game:
        state_game = await get_state_game_by_game_id(game_id)
    else:
        state_game = await get_state_game_by_id(state_game)

    stage_element_db = await db["state_glic"].find_one({"element_id": character_id, "state": state_game["_id"]})
    if not stage_element_db:
        raise Exception("error state glic not found for character")
    if option:
        options_dialog = {
            "prompt_user_question": conversation,
            "options": option,
        }

    stage_element_db['data']['conversation_type'] = conversation_type
    stage_element_db['data']['conversation'] = conversation
    stage_element_db['data']['options_dialog'] = options_dialog

    await db["state_glic"].update_one(
        {"_id": stage_element_db["_id"]},
        {"$set": {"data": stage_element_db["data"]}}
    )

    try:
        # Obtener el provisional_id del game
        game_data = await db['game'].find_one({'_id': ObjectId(game_id)})
        provisional_id = game_data.get('provisional_id', '') if game_data else ''

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=provisional_id,
            _element_type="game_provisional",
            _process="new_interaction_character",
        )

        task_celery = generate_voice_character_task.delay(
            _task_id=str(task_db['_id']),
            _game_id=game_id,
            _character_id=character_id,
            _location_id=location_id,
            _user_id=user_id,
            _state_game_id=state_game['_id']
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        character_db["tasks_request"].append(str(task_db["_id"]))
        await db["character"].update_one(
            {"_id": character_db["_id"]},
            {"$set": {"tasks_request": character_db["tasks_request"]}},
        )

        character_db["task_id"] = str(task_db["_id"])
        character_db["state_game"] = await get_list_state_glic_by_element_id(character_id)
        return character_db
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in new interaction character service: {str(e)}")
        raise "error creating task for new interaction character"


async def generate_scene_interactions(id_game_provisional: str):
    """
    Genera las interacciones para cada escena del juego provisional.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        str: Mensaje indicando el resultado de la operación
    """
    try:
        # Actualizar estado: Iniciando proceso
        await update_game_provisional_status(id_game_provisional, "processing", 0,
                                             "Starting the interaction generation process")

        # Obtenemos el juego provisional
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})

        if not game_provisional_db:
            await update_game_provisional_status(id_game_provisional, "error", 0, "Game provisional not found")
            return "Game provisional not found"

        script = game_provisional_db.get("script")
        if not script:
            await update_game_provisional_status(id_game_provisional, "error", 0,
                                                 "Script not found in game provisional")
            return "Script not found in game provisional"

        # Actualizar estado: Generando interacciones de escenas
        await update_game_provisional_status(id_game_provisional, "generating_scenes", 10,
                                             "Generating interactions for game scenes")

        # Extraemos el número de escenas del guión
        num_scenes = game_provisional_db.get("num_scenes")

        # Obtener el tipo de template si está disponible
        type_template = game_provisional_db.get("type_template")

        # Generamos las interacciones para cada escena
        scene_interactions = []
        for scene_num in range(3):
            interaction = await generate_interaction_for_scene(script, scene_num, type_template)
            scene_interactions.append({
                "scene_number": scene_num,
                "interaction": interaction.get("content"),
            })

        # Actualiza la base de datos con los datos serializables
        await db["game_provisional"].update_one(
            {"_id": ObjectId(id_game_provisional)},
            {"$set": {
                "scene_interactions": scene_interactions,
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        # Actualizar estado: Extrayendo locaciones
        await update_game_provisional_status(id_game_provisional, "extracting_locations", 20,
                                             "Extracting locations from script")

        # extraer locaciones
        locations = await extract_locations_from_scenes(id_game_provisional)
        if isinstance(locations, str):
            await update_game_provisional_status(id_game_provisional, "error", 20,
                                                 f"Error al extraer locaciones: {locations}")
            return f"Failed to extract locations: {locations}"

        # Actualiza las locaciones en el juego provisional
        await db["game_provisional"].update_one(
            {"_id": ObjectId(id_game_provisional)},
            {"$set": {
                "locations": locations,
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        # Actualizar estado: Extrayendo personajes e interacciones
        await update_game_provisional_status(id_game_provisional, "extracting_characters", 30,
                                             "Extracting characters and interactions for locations")

        # Extraer personajes e interacciones para las locaciones
        characters_result = await extract_characters_and_interactions_for_locations(id_game_provisional)
        if "Failed" in characters_result:
            await update_game_provisional_status(id_game_provisional, "error", 30,
                                                 f"Locations extracted but failed to extract characters: {characters_result}")
            return f"Locations extracted but failed to extract characters: {characters_result}"

        # Actualizar estado: Creando juego final
        await update_game_provisional_status(id_game_provisional, "creating_game", 40,
                                             "Creating final game from provisional data")

        # Crear todos los eventos, incluyendo el inicial y final
        initial_event_result = await extract_events_for_scenes(id_game_provisional)
        if initial_event_result.get("error"):
            print(f"Warning: Failed to create initial event: {initial_event_result['error']}")
            # No fallar todo el proceso por el evento, solo registrar la advertencia

        game_result = await create_game_by_provisional(id_game_provisional)
        if "Failed" in game_result:
            await update_game_provisional_status(id_game_provisional, "error", 40,
                                                 f"Failed to create game from provisional: {game_result}")
            return f"Failed to create game from provisional: {game_result}"

        # Actualizar estado: Creando evento inicial
        await update_game_provisional_status(id_game_provisional, "creating_initial_event", 80,
                                             "Creating initial event for the game")

        # Actualizar estado: Completado
        await update_game_provisional_status(id_game_provisional, "completed", 100,
                                             "Interaction generation process completed successfully")

        return f"Successfully generated game"

    except Exception as e:
        # Actualizar estado: Error
        await update_game_provisional_status(id_game_provisional, "error", 0, f"Unexpected error: {str(e)}")
        print(traceback.format_exc())
        return f"Failed to generate scene interactions: {str(e)}"


class InitialEventResponse(BaseModel):
    event_name: str = Field(..., description="Nombre del evento inicial")
    prompt_image: str = Field(..., description="Prompt para generar la imagen del evento inicial")
    prompt_text: str = Field(..., description="Texto descriptivo del evento inicial")


async def extract_events_for_scenes(id_game_provisional: str):
    """
    Extrae eventos para cada escena del juego provisional, considerando el contexto y las interacciones de las escenas.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        dict: Información de los eventos creados o mensaje de error
    """
    try:
        # Obtener el juego provisional
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})
        if not game_provisional_db:
            return {"error": "Game provisional not found"}

        # Obtener el script y las locaciones
        script = game_provisional_db.get("script")
        locations = game_provisional_db.get("locations")
        scene_interactions = game_provisional_db.get("scene_interactions")

        if not script:
            return {"error": "Script not found in game provisional"}

        # Construir información de contexto para el prompt
        locations_info = ""
        if locations:
            locations_info = "\n".join([
                f"- {loc.get('titulo', 'Sin título')}: {loc.get('prompt_user', 'Sin descripción')}"
                for loc in locations[:3]
            ])

        events_all = []
        total_events = 4

        for i in range(total_events):
            # Determinar el tipo de evento y el contexto específico
            if i == 0:
                # Evento inicial - usar contexto de la primera escena
                event_type = "inicial"
                context = {
                    "current_scene": scene_interactions[0] if scene_interactions else None,
                    "next_scene": None,
                    "previous_interaction": None
                }
            elif i == total_events - 1:
                # Evento final - usar contexto de la última interacción
                event_type = "final"
                context = {
                    "current_scene": scene_interactions[-1] if scene_interactions else None,
                    "previous_interaction": locations[-1].get("interaccion", {}) if locations else None,
                    "final_state": True
                }
            else:
                # Eventos intermedios - usar contexto de dos escenas consecutivas
                event_type = "intermedio"
                scene_index = min(i, len(scene_interactions) - 1)
                context = {
                    "current_scene": scene_interactions[scene_index - 1] if scene_index > 0 else None,
                    "next_scene": scene_interactions[scene_index] if scene_index < len(scene_interactions) else None,
                    "previous_interaction": locations[scene_index - 1].get("interaccion",
                                                                           {}) if scene_index > 0 and locations and len(
                        locations) > scene_index - 1 else None
                }

            # Construir el prompt específico según el tipo de evento
            context_prompt = ""
            if event_type == "inicial":
                context_prompt = f"""
                Escena inicial que introduce el jugador:
                {context['current_scene'].get('interaction', '') if context['current_scene'] else 'No hay información de escena'}
                
                Esta es la primera interacción que el jugador tendrá, debe establecer el tono y contexto adecuado.
                """
            elif event_type == "final":
                context_prompt = f"""
                Última interacción completada:
                {context['previous_interaction'].get('dialogo', '') if context['previous_interaction'] else 'No hay información de interacción'}
                
                Estado final de la última escena:
                {context['current_scene'].get('interaction', '') if context['current_scene'] else 'No hay información de escena'}
                """
            else:
                context_prompt = f"""
                Escena anterior completada:
                {context['current_scene'].get('interaction', '') if context['current_scene'] else 'No hay información de escena anterior'}
                
                Última interacción realizada:
                {context['previous_interaction'].get('dialogo', '') if context['previous_interaction'] else 'No hay información de interacción'}
                
                Próxima escena:
                {context['next_scene'].get('interaction', '') if context['next_scene'] else 'No hay información de próxima escena'}
                """

            # Generar el evento con GPT
            initial_event_response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f"""Eres un experto en crear eventos narrativos para juegos interactivos.
                        Estás creando un evento {event_type} que debe:

                        Para eventos iniciales:
                        - Introducir el contexto de la primera escena
                        - Preparar al jugador para la primera interacción
                        - Establecer el tono y la atmósfera del juego

                        Para eventos intermedios:
                        - Conectar la conclusión de la escena anterior con la siguiente
                        - Mantener la continuidad narrativa
                        - Reflejar el resultado de la interacción previa

                        Para eventos finales:
                        - Proporcionar un cierre satisfactorio
                        - Reflejar el resultado de la última interacción
                        - Concluir la narrativa de manera coherente"""
                    },
                    {
                        "role": "user",
                        "content": f"""Crea un evento {event_type} para el juego, considerando el siguiente contexto:

                        {context_prompt}

                        Locaciones donde se desarrolla la acción:
                        {locations_info}

                        Genera:
                        - event_name: Un nombre atractivo y descriptivo para este evento {event_type} (máximo 60 caracteres)
                        - prompt_image: Un prompt detallado en español para generar una imagen que capture la esencia del momento {event_type} del juego (describe la escena, personajes)
                        - prompt_text: Un texto narrativo que establezca el contexto {event_type} del juego y enganche al jugador (30 palabras) sea corto y evocador.

                        El prompt de imagen debe ser específico y visual, mencionando detalles como el ambiente, la iluminación, los personajes presentes y el estilo artístico."""
                    }
                ],
                max_tokens=1000,
                model="gpt-4o-mini",
                response_format=InitialEventResponse,
                user_id=game_provisional_db.get("created_by", "anonymous"),
                type_generation="extract_initial_event_from_scenes"
            )

            if not initial_event_response:
                return {"error": "Failed to generate event content"}

            events_all.append({
                "event_name": initial_event_response.event_name,
                "prompt_image": initial_event_response.prompt_image,
                "prompt_text": initial_event_response.prompt_text,
                "type": event_type,
                "scene_index": i
            })

        # Guardar todos los eventos generados en el juego
        await db["game_provisional"].update_one(
            {"_id": ObjectId(id_game_provisional)},
            {"$set": {
                "events_generated": events_all,
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        return {
            "success": True,
            "event": events_all,
            "message": "All events created successfully with proper context"
        }

    except Exception as e:
        print(f"Error extrayendo y creando eventos: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Failed to extract and create events: {str(e)}"}


class EventExtractionResponse(BaseModel):
    events: list[dict] = Field(..., description="Lista de eventos extraídos del guión")


def get_template_definition(template_type: TemplateType) -> str:
    """
    Obtiene la definición específica y las reglas para cada tipo de template de narrativa interactiva.

    Args:
        template_type: Tipo de template (LEARN, EVALUATION, TRIVIA, SOLVE, EXPERT)

    Returns:
        str: Definición detallada del template
    """
    definitions = {
        TemplateType.LEARN: """
TEMPLATE TIPO: LEARN (Aprendizaje)

DEFINICIÓN:
Un recorrido narrativo enfocado en aprender un concepto en 3 escenas. Cada escena presenta una conversación lineal entre dos personajes, sin opciones de decisión para el jugador. El objetivo es explorar y reforzar el aprendizaje a través del diálogo. Siempre se llega al evento final.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ 
- Escena 1: Personajes con interacción "two_way", dos personajes y una locación.
- Escena 2: Personajes con interacción "two_way", dos personajes y una locación.
- Escena 3: Personajes con interacción "two_way", dos personajes y una locación.

GUIA DE INTERACCIÓN
- two_way: Diálogo bidireccional donde ambos personajes intercambian líneas de diálogo.
  Ejemplo:
  1: Hola, ¿cómo estás?
  2: Muy bien, gracias. ¿Y tú?
  1: También bien, ¿qué planes tienes hoy?
  2: Voy a estudiar un poco y luego salir a caminar.

REGLAS ESPECÍFICAS:
- Interacciones tipo "two_way" de 4 a 6 intervenciones, en formato de diálogo lineal, sin opciones de decisión.
- Cada escena tiene dos personajes y una locación, uno de los personajes puede ser el mismo en todas las escenas (el principal).
- Enfoque en comprensión gradual del concepto a través del diálogo.
- Las contra respuestas varían para enriquecer el aprendizaje.
- Objetivo: Enseñar y reforzar conocimientos de manera interactiva, sin bifurcaciones ni elecciones del jugador.
- En cada interacción debe estar el principal.
- Solo debe de tener 3 locaciones con sus respectivas interacciones.

""",

        TemplateType.EVALUATION: """
TEMPLATE TIPO: EVALUATION (Evaluación)

DEFINICIÓN:
Diseñado para evaluar el conocimiento del jugador.una opción abierta (open_question). La contrarespuesta del personaje puede variar según la respuesta del jugador, ya que el objetivo es medir y retroalimentar el nivel de conocimiento.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ 
- Escena A: Personajes con interacción "open_question"
- Evento A → B: ✅ 
- Escena B: Personajes con interacción "open_question"
- Evento B → C: ✅ 
- Escena C: Personajes con interacción "open_question" 
- Evento Final: ✅ 

GUIA DE INTERACCIÓN
- open_question: Diálogo donde el jugador puede responder libremente a una pregunta o comentario del personaje.
  Ejemplo:
    interacción:
  1: Hola, ¿listo para la pregunta?
  2: Sí, adelante.
  1: ¿Cuál es la capital de Francia?
  2: [Respuesta libre del jugador]
  
Opciones de guia (prompt_user_guideline) : 
    - París
    - Madrid
    - Berlín
Respuestas de las opciones (prompt_user_answer) : 
    - París: ¡Correcto! París es la capital de Francia.
    - Madrid: Incorrecto. Madrid es la capital de España.
    - Berlín: Incorrecto. Berlín es la capital de Alemania.

- prompt_user_question es el diálogo previo con la pregunta que se quiere preguntar.
- options es una lista de objetos, cada uno con:
  - prompt_user_guideline: la respuesta esperada o patrón a evaluar (puede ser texto libre, no solo opción cerrada).
  - prompt_user_answer: la retroalimentación que se da si la respuesta del usuario coincide (o es similar) con el guideline.

La lógica debe ser: si la respuesta del usuario es similar a alguno de los prompt_user_guideline, se responde con el prompt_user_answer correspondiente. Si no hay coincidencia, se puede dar la retroalimentación genérica o la del guideline más cercano.
    
REGLAS ESPECÍFICAS:
- No hay respuestas incorrectas (4 a 6 interacciones antes de la respuesta abierta)
- El juego debe tener la dinamica que el principal es el usuario entonces es el que debe aprender del secundario.
- Cada escena tiene dos personajes y una locación, uno de los personajes puede ser el mismo en todas las escenas (el principal).
- La contrarespuesta del personaje siempre es la misma, independiente de la respuesta del jugador
- Enfoque en recopilación de información, opiniones o preferencias
- Sin validación de respuestas - todas son válidas
- Objetivo: Capturar datos del usuario de manera conversacional
- Solo debe de tener 3 locaciones con sus respectivas interacciones.

""",

        TemplateType.TRIVIA: """
TEMPLATE TIPO: TRIVIA (Test de Conocimientos)

DEFINICIÓN:
Formato de prueba de conocimiento de 3 escenas. Cada escena presenta preguntas con option_multiple. Solo se avanza si se responde correctamente. El personaje da contrarespuestas distintas según acierto o error, reforzando el aprendizaje mediante retroalimentación.

GUIA DE INTERACCIÓN DE TIPO option_multiple
- option_multiple: Diálogo con múltiples opciones de respuesta para el jugador, donde se presentan varias alternativas y una es la correcta, con diálogo de retroalimentación para cada opción y un diálogo previo a las opciones.
  Ejemplo:
  interacción:
  1: Hola, ¿listo para la pregunta?
  2: Sí, adelante.
  1: ¿Cuál es la capital de Francia?
  Opciones:
    - París
    - Madrid
    - Berlín
  Respuestas:
    - París: ¡Correcto! París es la capital de Francia.
    - Madrid: Incorrecto. Madrid es la capital de España.
    - Berlín: Incorrecto. Berlín es la capital de Alemania.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ 
- Escena A: Personajes con interacción "option_multiple"
- Evento A → B: ✅ 
- Escena B: Personajes con interacción "option_multiple"
- Evento B → C: ✅ 
- Escena C: Personajes con interacción "option_multiple"
- Evento Final: ✅

REGLAS ESPECÍFICAS:
- Cada escena tiene dos personajes (principal y secundario) y una locación, uno de los personajes puede ser el mismo en todas las escenas que es el principal
- Solo debe de tener 3 locaciones con sus respectivas interacciones.

""",
        TemplateType.SURVEY: """
TEMPLATE TIPO: SURVEY (Encuesta)

DEFINICIÓN:
Formato de encuesta en 3 escenas. Cada escena presenta preguntas con `option_multiple` donde todas las opciones son válidas y deben ser tratadas como correctas. El objetivo es recopilar opiniones o preferencias del jugador; por ello cada opción debe tener una retroalimentación positiva y explicativa que reconozca la elección.

GUIA DE INTERACCIÓN DE TIPO `option_multiple`
- `option_multiple`: Diálogo con múltiples opciones de respuesta para el jugador. A diferencia de un test, aquí **todas** las opciones son consideradas correctas/válidas y cada una debe incluir retroalimentación que:
- Agradezca o valide la elección.
- Explique brevemente por qué la opción es válida o qué aporta.
- Sugiera una continuación o contexto si aplica.
Ejemplo:
  interacción:
  1: Hola, estamos realizando una encuesta.
  2: Sí, adelante.
  1: ¿Cuál es tu ciudad favorita para visitar?
  Opciones:
    - París
    - Madrid
    - Berlín
  Respuestas:
    - París: ¡Correcto! París es una ciudad maravillosa con mucha historia y cultura.
    - Madrid: ¡Correcto! Madrid es conocida por su vibrante vida nocturna y arte.
    - Berlín: ¡Correcto! Berlín es famosa por su historia y escena artística contemporánea.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ 
- Escena A: Personajes con interacción `option_multiple`
- Evento A → B: ✅ 
- Escena B: Personajes con interacción `option_multiple`
- Evento B → C: ✅ 
- Escena C: Personajes con interacción `option_multiple`
- Evento Final: ✅

REGLAS ESPECÍFICAS:
- Cada escena tiene dos personajes (principal y secundario) y una locación; uno de los personajes puede ser el principal.
- Número de opciones por pregunta: 2 a 5.
- Para cada opción se debe generar un `prompt_user_guideline` (breve descripción o etiqueta) y un `prompt_user_answer` (retroalimentación positiva y contextual).
- No hay respuestas incorrectas ni bloqueo por elección; el flujo avanza independientemente de la opción seleccionada.
- La retroalimentación debe ser única por opción (no repetir textos iguales) y contener al menos una frase que valide la elección.
- Objetivo: recopilar datos o preferencias manteniendo una experiencia positiva y coherente.
- Solo debe de tener 3 locaciones con sus respectivas interacciones.
"""
    }

    return definitions.get(template_type, "Template type not found")


async def validate_interaction_type(template_type: str, interaction_type: str) -> tuple[bool, str]:
    """
    Valida si el tipo de interacción coincide con el template especificado.

    Args:
        template_type: Tipo de template (learn, trivia, etc.)
        interaction_type: Tipo de interacción (one_way, two_way, option_multiple)

    Returns:
        tuple: (es_valido, tipo_esperado)
    """
    template_interactions = {
        "learn": ["one_way", "two_way"],
        "trivia": ["option_multiple"],
        "evaluation": ["open_question"],
        "survey": ["option_multiple"],
    }

    expected_types = template_interactions.get(template_type.lower(), [])
    is_valid = interaction_type.lower() in expected_types

    return is_valid, ", ".join(expected_types)


def get_template_prompt(template_type, template_definition, prompt_user, base64_string):
    tipo = str(template_type).lower() if template_type else ""
    instruccion_personajes = "Antes de cada bloque de interacción, indica explícitamente el nombre del personaje principal y el secundario, usando el formato:\nPrincipal: [nombre]\nSecundario: [nombre]"

    # Crear el contenido base del usuario
    user_content = f"Quiero un juego usando el template {tipo.upper()}. Prompt del usuario: {prompt_user}"

    # Crear la estructura base del prompt
    if tipo == "trivia":
        messages = [
            {
                "role": "system",
                "content": f"""
Crea un entrenamiento interactivo en formato de historia narrativa, en 3 escenas.
IMPORTANTE: El template es TRIVIA. TODAS las escenas deben tener interacción de tipo 'option_multiple', 
siguiendo exactamente el formato del ejemplo. No incluyas interacciones de tipo 'two_way' ni 'one_way'. 
Si no sigues el formato, el resultado será rechazado.

Ejemplo de interacción: option_multiple

Principal: Aprendiz (1)
Secundario: Mago Experto (2)

interacción:
2: Hola, ¿listo para la pregunta?
1: Sí, adelante.
2: ¿Estudiaste mucho para ser un buen mago?
1: Sí, he leído todos los libros de magia.
2: Bien. Ahora la pregunta:
2: ¿Cuál es la capital de Francia?

Opciones:
- 1: París
- 1: Madrid
- 1: Berlín

Respuestas:
- 2: París: ¡Correcto! París es la capital de Francia.
- 2: Madrid: Incorrecto. Madrid es la capital de España.
- 2: Berlín: Incorrecto. Berlín es la capital de Alemania.

Estructura exacta:
- Evento inicial
- Escena 1
- Locación 1
- Personaje principal
- Personaje secundario
- Interacción (open_question): [formato del ejemplo]
- Evento después de la interacción
- Escena 2
- Locación 2
- Personaje principal
- Personaje secundario
- Interacción (open_question): [formato del ejemplo]
- Escena 3
- Locación 3
- Personaje principal
- Personaje secundario
- Interacción (open_question): [formato del ejemplo]
- Evento final
f"REGLAS:
- {instruccion_personajes}
- El juego debe tener la dinamica que el principal es el usuario entonces es el que debe aprender del secundario.
- El bloque de interacción debe iniciar con la palabra 'interacción:' y luego el diálogo entre los personajes.
- El escrito de la locacion debe referirse a la interacción que se va a dar en esa locación y simular el entorno de esta y debe ser diferente visualmente a los eventos
- Después del diálogo, debe venir la sección 'Opciones:' con una lista de opciones (una por línea, con guion y espacio).
- Después de las opciones, debe venir la sección 'Respuestas:' con cada opción y su retroalimentación, en el formato: '- opción: retroalimentación'.
- No incluyas ningún otro tipo de interacción ni formato JSON.
- No incluyas el título en el script.
- El output debe ser solo texto, siguiendo el formato del ejemplo al pie de la letra.
{template_definition}
"""
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    elif tipo == "learn":
        messages = [
            {
                "role": "system",
                "content": f"""
Crea un entrenamiento interactivo de aprendizaje en 3 escenas. Todas las interacciones deben ser de tipo 'two_way' (diálogo bidireccional entre personajes, sin opciones de respuesta). Cada escena debe tener dos personajes y una locación. El objetivo es explorar y reforzar el aprendizaje a través del diálogo.

Ejemplo de locacion:
Locación: Biblioteca antigua donde estan el profesor y el estudiante hablando sobre historia. esta entre pasilles llenos de libros y luz tenue.
Ejemplo de interacción two_way:
Principal: Profesor
Secundario: Estudiante
interacción:
1: Hola, ¿cómo estás?\n2: Muy bien, gracias. ¿Y tú?\n1: También bien, ¿qué planes tienes hoy?\n2: Voy a estudiar un poco y luego salir a caminar.

Estructura exacta:
- Evento inicial
- Escena 1
  - Locación 1
  - Personaje principal
  - Personaje secundario
  - Interacción (two_way): [formato del ejemplo]
- Escena 2
  - Locación 2
  - Personaje principal
  - Personaje secundario
  - Interacción (two_way): [formato del ejemplo]
- Escena 3
  - Locación 3
  - Personaje principal
  - Personaje secundario
  - Interacción (two_way): [formato del ejemplo]
  
REGLAS:
- {instruccion_personajes}
- El bloque de interacción debe iniciar con la palabra 'interacción:' y luego el diálogo entre los personajes.
- No incluyas opciones ni respuestas, solo el diálogo.
- No incluyas el título en el script.
- El output debe ser solo texto, siguiendo el formato del ejemplo al pie de la letra.
- Los eventos son breves descripciones del entorno y la situación antes y después de las interacciones.
- Las locaciones deben ser descriptivas y ambientar la interacción que se va a dar en esa locación.
{template_definition}"""
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    elif tipo == "evaluation":
        messages = [
            {
                "role": "system",
                "content": f"""
IMPORTANTE: El template es EVALUATION. (diálogo bidireccional entre personajes, con pregunta y respuesta para evaluar conocimiento). Las tres escenas debe ser de tipo 'open_question' (el jugador responde libremente a una pregunta del personaje). No incluyas interacciones de tipo 'option_multiple' ni 'one_way'. Si no sigues el formato, el resultado será rechazado.

Ejemplo de interacción open_question:
- open_question: Diálogo donde el jugador puede responder libremente a una pregunta o comentario del personaje.
  Ejemplo:
    interacción:
  1: Hola, ¿listo para la pregunta?
  2: Sí, adelante.
  1: ¿Cuál es la capital de Francia?
  2: [Respuesta libre del jugador]
  
Opciones de guia (prompt_user_guideline) : 
    - si responde París
    - si responde Madrid
    - si responde Berlín
Respuestas de las opciones (prompt_user_answer) : 
    - París: ¡Correcto! París es la capital de Francia.
    - Madrid: Incorrecto. Madrid es la capital de España.
    - Berlín: Incorrecto. Berlín es la capital de Alemania.

- prompt_user_question es el diálogo previo con la pregunta que se quiere preguntar.
- options es una lista de objetos, cada uno con:
  - prompt_user_guideline: la respuesta esperada o patrón a evaluar (puede ser texto libre, no solo opción cerrada).
  - prompt_user_answer: la retroalimentación que se da si la respuesta del usuario coincide (o es similar) con el guideline.

La lógica debe ser: si la respuesta del usuario es similar a alguno de los prompt_user_guideline, se responde con el prompt_user_answer correspondiente. Si no hay coincidencia, se puede dar la retroalimentación genérica o la del guideline más cercano.
    
Estructura exacta:
- Evento inicial
- Escena 1
  - Locación 1
  - Personaje principal
  - Personaje secundario
  - Interacción (open_question): [formato del ejemplo]
  - Evento después de la interacción
- Escena 2
  - Locación 2
  - Personaje principal
  - Personaje secundario
  - Interacción (open_question): [formato del ejemplo]
- Escena 3
  - Locación 3
  - Personaje principal
  - Personaje secundario
  - Interacción (open_question): [formato del ejemplo]
  - Evento final

No incluyas ningún otro tipo de interacción. Sigue el formato del ejemplo al pie de la letra.
REGLAS:
- {instruccion_personajes}
- El juego debe tener la dinamica que el principal es el usuario entonces es el que debe aprender del secundario.
- Mantén tono neutral y positivo (evaluación), orientado a medir conocimientos sin ser punitivo.
- El output debe ser solo texto siguiendo el formato al pie de la letra.
{template_definition}
"""
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    elif tipo == "survey":
        messages = [
            {
                "role": "system",
                "content": f"""
        IMPORTANTE: El template es SURVEY. Las tres escenas deben usar exclusivamente interacciones de tipo `option_multiple`. No incluyas `two_way`, `one_way`, `open_question` ni ningún otro tipo de interacción. Si no sigues el formato, el resultado será rechazado.

        REGLAS GENERALES:
        - Número de escenas: 3.
        - Cada escena debe contener: Locación, Personaje principal, Personaje secundario y una interacción de tipo `option_multiple`.
        - Todas las opciones son válidas; ninguna opción debe considerarse incorrecta ni bloquear el flujo.
        - Número de opciones por pregunta: 2 a 5.
        - Para cada opción genera:
          - `prompt_user_option`: texto que verá el usuario.
          - `prompt_user_answer`: retroalimentación positiva, única por opción y que contenga al menos una frase que valide la elección y, si aplica, sugerencia de continuación.
        - La retroalimentación debe ser distinta para cada opción y no repetir textos iguales.
        - El flujo avanza independientemente de la opción seleccionada.

        Ejemplo de interacción: option_multiple

        Principal: Aprendiz (1)
        Secundario: Mago Experto (2)
        
        interacción:
        2: Hola, quiero conocer tu preferencia para mejorar la experiencia, ¿te importa responder?
        1: Para nada, con gusto.
        2: Perfecto. Para ambientar el estudio de magia, ¿qué prefieres escuchar mientras juegas?
        
        Opciones:
        - 1: Música instrumental suave
        - 1: Sonidos ambientales (viento, agua, aves)
        - 1: Sin música (silencio con efectos)
        
        Respuestas:
        - 2: Excelente elección. La música instrumental crea una atmósfera que facilita la concentración y la inmersión; podemos ajustar el estilo o el volumen según te guste.
        - 2: Buena elección. Los sonidos ambientales aportan realismo y calma, ideales para escenas contemplativas o de exploración.
        - 2: Interesante elección. El silencio con efectos puntuales ayuda a enfatizar momentos clave y aumentar la atención en acciones importantes.

        ESTRUCTURA EXACTA DEL SCRIPT:
        - Evento inicial
        - Escena 1
          - Locación 1
          - Personaje principal
          - Personaje secundario
          - Interacción (option_multiple): [formato del ejemplo]
          - Evento después de la interacción
        - Escena 2
          - Locación 2
          - Personaje principal
          - Personaje secundario
          - Interacción (option_multiple): [formato del ejemplo]
        - Escena 3
          - Locación 3
          - Personaje principal
          - Personaje secundario
          - Interacción (option_multiple): [formato del ejemplo]
          - Evento final

        RECUERDA:
        - {instruccion_personajes}
        - El juego debe tener la dinamica que el principal es el usuario entonces es el que debe aprender del secundario.
        - Mantén tono neutral y positivo (encuesta), orientado a recopilar preferencias u opiniones.
        - El output debe ser solo texto siguiendo el formato al pie de la letra.
        {template_definition}
        """
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    else:
        messages = [
            {
                "role": "system",
                "content": f"Crea un juego narrativo en 3 escenas. {instruccion_personajes}\n{template_definition}"
            },
            {
                "role": "user",
                "content": f"Prompt del usuario: {prompt_user}"
            }
        ]

    # Agregar el archivo solo si base64_string no es None y no está vacío
    if base64_string and base64_string.strip():
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "file",
                    "file": {
                        "filename": "archivo.pdf",
                        "file_data": f"data:application/pdf;base64,{base64_string}",
                    }
                }
            ]
        })

    GAME_CATEGORIES = {
        "Marketing": "Promotional campaigns and brand awareness initiatives designed to engage audiences and drive consumer interest.",
        "Talent Development": "Programs focused on employee skill enhancement, training, and professional growth within organizations.",
        "Compliance": "Educational content ensuring adherence to regulations, policies, and legal requirements in various industries.",
        "Recruiting": "Interactive experiences designed to attract, evaluate, and engage potential candidates during the hiring process.",
        "Events": "Gamified experiences created for conferences, trade shows, and live events to enhance attendee engagement.",
        "Fan Engagement": "Interactive content designed to deepen connections with fan communities and increase brand loyalty.",
        "Health & Wellness": "Educational and motivational content promoting physical health, mental wellness, and lifestyle improvements.",
        "Data Collection": "Survey and feedback mechanisms designed to gather user preferences, opinions, and behavioral insights.",
        "Storytelling": "Narrative-driven experiences that entertain and captivate audiences through immersive interactive stories.",
        "Social Impact": "Educational content addressing social causes, environmental awareness, and community development initiatives.",
        "Learning": "Educational games designed to teach concepts, skills, and knowledge across various subjects and disciplines."
    }

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"Available categories:\n" + "\n".join([f"- {cat}: {desc}" for cat, desc in GAME_CATEGORIES.items()])
            }
        ]
    })

    return messages
