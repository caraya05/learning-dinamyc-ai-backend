import json
import random
import string
from io import BytesIO

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
from character.schemas import SchemaCreateCharacter
from character.tasks import async_generate_character_task
from core.database import db
from event.models import Event
from event.schemas import SchemaCreateEvent
from game.models import Game
from game.narrative_templates import TemplateType
from game.narrative_schemas import SchemaGenerateFromScript, SchemaTemplateExtractionResult
from game.narrative_services import (
    create_narrative_template_from_script,
    extract_template_elements,
    get_template_generation_status
)

from gpt_ai.utils import openai_generator
from location.models import Location, LocationGLIC
from location.schemas import SchemaCreateLocation
from location.tasks import async_generate_location_task
from event.tasks import async_generate_image_event
from state_game.services import create_state_game, get_state_game_by_game_id, get_state_game_by_id
from state_glic.services import create_state_glic

from utils import upload_image

from config import settings

# Configuración del sistema de logs
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger("game_provisional_tasks")

NOT_GIVEN = NotGiven()


async def update_game_provisional_status(id_game_provisional: str, status: str, progress: int = None,
                                         progress_text: str = None):
    """
    Actualiza el estado del juego provisional.

    Args:
        id_game_provisional: ID del juego provisional
        status: Estado actual del proceso
        progress: Progreso en porcentaje (opcional)
        progress_text: Texto descriptivo del progreso actual (opcional)
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


class TaskCreateGameProvisional(BaseModel):
    script: str = Field(..., example="script", description="Script for the game provisional")
    title: str = Field(..., example="title", description="Title for the game provisional")
    num_scenes: int = Field(..., example=1, description="Number of scenes in the game provisional")
    category: str = Field(..., example="Learning", description="Category of the game based on its content and purpose")


async def create_game_provisional(_id_game_provisional: str):
    """
    Create a provisional game entry in the database.
    """
    # logger.info(f"Iniciando creación de juego provisional con ID: {_id_game_provisional}")
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

        template_definition = get_template_definition(game_provisional_db.get("template_type", None))


        # logger.info("Generando contenido del juego con GPT-4.1")
        source_game_response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": f"""Crea un entrenamiento interactivo en formato de historia narrativa tipo "elige tu propia aventura" para un nuevo representante de ventas en una empresa.
                                El objetivo es transformar el documento a través de situaciones narradas de forma fluida, como si fuera un capítulo de un libro.
                                 🔹 Instrucciones:
                                Comienza con una introducción inmersiva que sitúe al protagonista en su primer día como representante de ventas en una empresa, destacando su entusiasmo y nerviosismo al enfrentarse a este nuevo desafío. 
                                Desarrolla entre 3 y 5 escenas clave que narren momentos cruciales de su experiencia, como su primera reunión con un cliente, el manejo de objeciones inesperadas, la negociación de condiciones bajo presión y el emocionante cierre de su primera venta. 
                                Cada escena debe fluir como un capítulo de una novela, integrando momentos de decisión en los que el protagonista debe elegir entre diferentes acciones. Por ejemplo, podría decidir si responder de inmediato con argumentos técnicos o tomarse una pausa para indagar más sobre las necesidades del cliente, todo narrado de manera fluida y literaria.
                                No reveles de inmediato cuál es la mejor opción. En su lugar, tras cada decisión, describe las consecuencias de manera narrativa: cómo afecta la confianza del cliente, la reputación del protagonista y sus habilidades de venta, integrando estas reflexiones en la historia.
                                Usa un tono profesional, dinámico y conversacional, pero con un estilo literario que mantenga al lector inmerso en la experiencia. Finaliza con una conclusión personalizada que resuma el estilo de ventas del protagonista según sus elecciones, como si fuera una evaluación narrativa de su desempeño, y ofrece consejos prácticos para mejorar en el futuro.
                                        
                                🔹 Detalles técnicos:
                                {template_definition}
                                
                                🔹 Categorización del juego:
                                Después de crear el contenido, categoriza el juego en UNA de las siguientes categorías basándote en el propósito principal y contenido del juego:
                                
                                - Marketing: Juegos enfocados en promoción de productos, branding, campañas publicitarias, estrategias de mercadeo
                                - Talent Development: Juegos para desarrollo de habilidades profesionales, liderazgo, capacitación laboral, crecimiento personal
                                - Compliance: Juegos sobre cumplimiento normativo, políticas empresariales, regulaciones, procedimientos legales
                                - Recruiting: Juegos para procesos de selección, evaluación de candidatos, onboarding, atracción de talento
                                - Events: Juegos para eventos corporativos, conferencias, actividades de equipo, celebraciones
                                - Fan Engagement: Juegos para fidelización de clientes, comunidades de fans, engagement de audiencias
                                - Health & Wellness: Juegos sobre bienestar, salud mental, ejercicio, hábitos saludables, prevención
                                - Data Collection: Juegos para recopilar información, encuestas interactivas, investigación de mercado
                                - Storytelling: Juegos narrativos, historias interactivas, experiencias inmersivas, entretenimiento educativo
                                - Social Impact: Juegos sobre responsabilidad social, sostenibilidad, causas benéficas, impacto comunitario
                                - Learning: Juegos educativos, entrenamiento académico, desarrollo de conocimientos específicos, enseñanza"""
                },
                {
                    "role": "user",
                    "content": f"nesecito que me ayudes a crear un juego basado en el archivo PDF proporcionado."
                               f"nesecito que el juego tenga un guion y un titulo ambos en ingles, el guion debe ser una historia que se pueda jugar en formato de texto"
                               f"prompt del usuario: {game_provisional_db.get('prompt_user', 'No prompt provided')}"
                },
                {
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
                }
            ],
            model="gpt-4.1",
            response_format=TaskCreateGameProvisional,
            type_generation="game_provisional",
            user_id=None,
            max_tokens=16384,
        )

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
            url_image = "https://via.placeholder.com/512x896.jpg?text=Test+Mode+Image"
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
                    "content": "Eres un diseñador de juegos narrativos especializados en crear interacciones para juegos basados en texto."
                },
                {
                    "role": "user",
                    "content": f"""
                            De la escena de escena {scene_num} del guión, define con que personajes y con que objetos (que no sean su ropa ni objetos que el protagonista tenga en su haber) el protagonista debe interactuar.
                            De estos personajes y objetos con los que debe interactuar escoge uno solo, el cual será el personaje u objeto clave para avanzar en la historia, salir de esta escena y pasar a la siguiente.
                            Definido lo anterior, para los personajes que no sea personaje clave, redacta lo que seria un dialogo finito entre el protagonista y este. Mientras que para el personaje clave, si lo hay, define un dialogo que termine en una pregunta la cual el protagonista debe responder correctamente para avanzar en la historia al siguiente escenario, define la respuesta que daría el personaje tanto si responde correctamente como si responde incorrectamente.
                            De manera similar, para los objetos que no sean objeto clave, redacta lo que seria el texto de lo que pensaría el protagonista al ver este objeto. Mientras que para el objeto clave, si lo hay, define una auto-pregunta que se haga el protagonista y llame a la acción, acción que el protagonista debe realizar para avanzar en la historia al siguiente escenario, define lo que sucedería y lo que pensaría el protagonista, tanto si realiza la acción correcta, como si no la realiza.
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

        # Analizamos la respuesta para estructurarla adecuadamente
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
    tipo: str = Field(..., description="Tipo de conversación: 'one_one' o 'two_way'")
    dialogo: str = Field(..., description="Diálogo de la interacción")


class LocationWithCharacters(BaseModel):
    titulo: str = Field(..., description="Nombre de la locación")
    personaje_principal: PersonajeLocacion = Field(..., description="Personaje principal de la locación")
    personaje_secundario: PersonajeLocacion = Field(..., description="Personaje secundario de la locación")
    interaccion: InteraccionPersonajes = Field(..., description="Interacción entre personajes")


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

        prompt = (
            "Analiza todas las escenas del siguiente guion y extrae la información de las locaciones en el siguiente formato para cada locación encontrada:\n"
            "- titulo: nombre de la locacion\n"
            "- prompt_user: descripcion de la locacion\n"
            "- escena: escena inicial donde aparece\n"
            "- escenas_donde_se_repite: todas las escenas donde se repite\n"
            "Devuelve una lista de objetos JSON, uno por cada locación.\n"
            f"Guion:\n{script}"
        )

        locations_response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system", "content": "Eres un experto en análisis de guiones para videojuegos."},
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

        prompt = (
            f"Analiza el siguiente guion y las locaciones extraídas. Para cada locación, identifica y crea personajes e interacciones.\n\n"
            f"LOCACIONES EXISTENTES:\n{locations_list}\n\n"
            f"Para cada locación, devuelve un objeto JSON con:\n"
            f"- titulo: nombre de la locación (debe coincidir exactamente con las locaciones existentes)\n"
            f"- personaje_principal: objeto con 'nombre' y 'prompt_descriptivo' (debe ser el mismo personaje en TODAS las locaciones)\n"
            f"- personaje_secundario: objeto con 'nombre' y 'prompt_descriptivo' (diferente para cada locación)\n"
            f"- interaccion: objeto con:\n"
            f"  * tipo: 'one_one' (solo habla el secundario al principal) o 'two_way' (diálogo entre principal y secundario)\n"
            f"  * dialogo: \n"
            f"    - Para 'one_one': un diálogo corto que dice el secundario al principal\n"
            f"    - Para 'two_way': formato '1 texto 2 texto 1 texto' donde 1=principal y 2=secundario\n\n"
            f"REGLAS IMPORTANTES:\n"
            f"- El personaje principal debe ser el MISMO en todas las locaciones\n"
            f"- Cada locación tiene exactamente 1 personaje secundario (diferente por locación)\n"
            f"- Exactamente 1 interacción por locación\n"
            f"- Los tipos son: 'one_one' o 'two_way'\n\n"
            f"GUION COMPLETO:\n{script}"
        )

        characters_response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system",
                 "content": "Eres un experto en análisis de guiones y creación de personajes para videojuegos. Analiza cuidadosamente el guión y crea personajes consistentes con interacciones naturales."},
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
                else:
                    updated_location['personaje_principal'] = char_info.get('personaje_principal')
                    updated_location['personaje_secundario'] = char_info.get('personaje_secundario')
                    updated_location['interaccion'] = char_info.get('interaccion')

            updated_locations.append(updated_location)

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
        if character.prompt_user:
            response_moderation_prompt_user = await openai_generator.moderation_text(
                text=character.prompt_user, user_id=user_id
            )
            if response_moderation_prompt_user:
                return "Prompt user not allowed"
        if character.prompt_user_dialog:
            response_moderation_dialog = await openai_generator.moderation_text(
                text=character.prompt_user_dialog, user_id=user_id
            )
            if response_moderation_dialog:
                return "Prompt user dialog not allowed"

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



        task_celery = await async_generate_character_task(
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

    moderation_prompt_user = await openai_generator.moderation_text(
        text=location.prompt_user,
        user_id=user_id,
    )
    if moderation_prompt_user:
        return "Prompt user not allowed"

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



        task_celery = await async_generate_location_task(
            _location_id=str(location_created.inserted_id),
            _user_id=user_id,
            _task_id="",
            _state_game_id=state_game["_id"],
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
        image=None,
        game_id=event.game_id,
        created_by=user_id,
        updated_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_final=event.is_final,
    )

    event_created = await db["event"].insert_one(event_schema.dict())

    if event.prompt_user_image:

        task_celery = await async_generate_image_event(
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

        # logger.info(f"Creating game with {len(locations)} locations from provisional")
        for location in locations[0:1]:
            location_db = await create_location_service(
                location=SchemaCreateLocation(
                    title=location["titulo"],
                    prompt_user=location["prompt_user"],
                    game_id=str(game_db.get("_id")),
                    state_game=str(state_game_db.get("_id")),
                ),
                user_id=str(game_provisional_db.get("created_by", "anonymous")),
                file=None
            )

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
                    options_dialog=None,
                    game_id=str(game_db.get("_id")),
                    location_id=str(location_db.get("_id")),
                    state_game=str(state_game_db.get("_id"))
                ),
                user_id=game_provisional_db.get("created_by", "anonymous"),
                game_id=str(game_db.get("_id")),
                file=None
            )

            # Crear configuración de la locación con posicionamiento de personajes
            def generate_random_position():
                """Genera una posición aleatoria en la cuadrícula de 60x60"""
                return {
                    "index": 0,  # Índice de la cuadrícula
                    "X": random.randint(28, 35),
                    "Y": random.randint(28, 35)
                }

            # Configuración de la locación con personajes posicionados
            location_configuration = {
                "characterScale": 1.7,
                "GridX": 0,
                "GridY": 0,
                "GridPlaneSize": 0,  # Cuadrícula de 60x60
                "Characters": [
                    {
                        "characterId": str(character_principal_db.get("_id")),
                        **generate_random_position()
                    },
                    {
                        "characterId": str(character_db.get("_id")),
                        **generate_random_position()
                    }
                ],
                "items": []  # Por ahora sin items, se pueden agregar después
            }

            location_state_db = await db["state_glic"].find_one(
                {"element_id": str(location_db.get("_id")), "type_element": "location"}
            )

            location_state_db["data"]["configuration"] = location_configuration
            await db["state_glic"].update_one(
                {"_id": location_state_db["_id"]},
                {"$set": {
                    "data": location_state_db["data"],
                    "updated_at": datetime.now(pytz.utc)
                }}
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


async def generate_scene_interactions(id_game_provisional: str):
    """
    Genera las interacciones para cada escena del juego provisional.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        str: Mensaje indicando el resultado de la operación
    """
    # logger.info(f"Iniciando generación de interacciones para juego provisional ID: {id_game_provisional}")
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
        await update_game_provisional_status(id_game_provisional, "generating_scenes", 15,
                                             "Generating interactions for game scenes")

        # Extraemos el número de escenas del guión
        num_scenes = game_provisional_db.get("num_scenes")

        # Obtener el tipo de template si está disponible
        template_type = game_provisional_db.get("template_type")

        # Generamos las interacciones para cada escena
        scene_interactions = []
        for scene_num in range(3):
            interaction = await generate_interaction_for_scene(script, scene_num, template_type)
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
        await update_game_provisional_status(id_game_provisional, "extracting_locations", 35,
                                             "Extracting locations from script")

        # extraer locaciones
        locations = await extract_locations_from_scenes(id_game_provisional)
        if isinstance(locations, str):
            await update_game_provisional_status(id_game_provisional, "error", 35,
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
        await update_game_provisional_status(id_game_provisional, "extracting_characters", 45,
                                             "Extracting characters and interactions for locations")

        # Extraer personajes e interacciones para las locaciones
        characters_result = await extract_characters_and_interactions_for_locations(id_game_provisional)
        if "Failed" in characters_result:
            await update_game_provisional_status(id_game_provisional, "error", 45,
                                                 f"Locations extracted but failed to extract characters: {characters_result}")
            return f"Locations extracted but failed to extract characters: {characters_result}"

        # Actualizar estado: Creando juego final
        await update_game_provisional_status(id_game_provisional, "creating_game", 60,
                                             "Creating final game from provisional data")

        game_result = await create_game_by_provisional(id_game_provisional)
        if "Failed" in game_result:
            await update_game_provisional_status(id_game_provisional, "error", 60,
                                                 f"Failed to create game from provisional: {game_result}")
            return f"Failed to create game from provisional: {game_result}"

        # Actualizar estado: Creando evento inicial
        await update_game_provisional_status(id_game_provisional, "creating_initial_event", 80,
                                             "Creating initial event for the game")

        # Crear evento inicial después de que se haya creado el juego
        initial_event_result = await extract_and_create_initial_event_from_scenes(id_game_provisional)
        if initial_event_result.get("error"):
            print(f"Warning: Failed to create initial event: {initial_event_result['error']}")
            # No fallar todo el proceso por el evento, solo registrar la advertencia
        else:
            print(f"Initial event created successfully: {initial_event_result.get('message', 'Unknown result')}")

        # Actualizar estado: Completado
        await update_game_provisional_status(id_game_provisional, "completed", 100,
                                             "Interaction generation process completed successfully")

        return f"Successfully generated interactions for {num_scenes} scenes and extracted characters for locations"

    except Exception as e:
        # Actualizar estado: Error
        await update_game_provisional_status(id_game_provisional, "error", 0, f"Unexpected error: {str(e)}")
        print(traceback.format_exc())
        return f"Failed to generate scene interactions: {str(e)}"


class InitialEventResponse(BaseModel):
    event_name: str = Field(..., description="Nombre del evento inicial")
    prompt_image: str = Field(..., description="Prompt para generar la imagen del evento inicial")
    prompt_text: str = Field(..., description="Texto descriptivo del evento inicial")


async def extract_and_create_initial_event_from_scenes(id_game_provisional: str):
    """
    Extrae un evento inicial previo a las escenas del guego provisional y crea el evento usando create_event_service.

    Args:
        id_game_provisional: ID del juego provisional

    Returns:
        dict: Información del evento creado o mensaje de error
    """
    try:
        # Obtener el juego provisional
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})
        if not game_provisional_db:
            return {"error": "Game provisional not found"}

        # Verificar que existe un juego asociado
        game_id = game_provisional_db.get("game_id")
        if not game_id:
            return {"error": "No game associated with this provisional game"}

        # Obtener información del juego
        game_db = await db["game"].find_one({"_id": ObjectId(game_id)})
        if not game_db:
            return {"error": "Associated game not found"}

        # Obtener el script y las locaciones
        script = game_provisional_db.get("script")
        locations = game_provisional_db.get("locations", [])

        if not script:
            return {"error": "Script not found in game provisional"}

        # Obtener estado inicial del juego
        state_game_db = await db["state_game"].find_one({"game_id": game_id, "order": 1})
        if not state_game_db:
            return {"error": "Initial game state not found"}

        # Obtener la primera locación para el evento
        first_location_id = None
        if locations and len(locations) > 0:
            # Buscar la locación real en la base de datos usando el título
            location_title = locations[0].get("titulo", "")
            if location_title:
                location_db = await db["location"].find_one({
                    "title": location_title,
                    "game_id": game_id
                })
                if location_db:
                    first_location_id = str(location_db["_id"])

        # Si no encontramos la locación por título, usar la primera de la lista del juego
        if not first_location_id and game_db.get("locations_id"):
            first_location_id = game_db["locations_id"][0]

        # Construir información de contexto para el prompt
        locations_info = ""
        if locations:
            locations_info = "\n".join([
                f"- {loc.get('titulo', 'Sin título')}: {loc.get('prompt_user', 'Sin descripción')}"
                for loc in locations[:3]  # Solo primeras 3 locaciones para no sobrecargar
            ])

        # Generar el evento inicial con GPT
        initial_event_response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": """Eres un experto en crear eventos iniciales para juegos narrativos interactivos.
                    Tu tarea es crear un evento que sirva como introducción o prólogo al juego, estableciendo 
                    el contexto y la atmósfera antes de que el jugador comience su aventura en las locaciones.
                    
                    El evento debe:
                    1. Crear expectativa y emoción
                    2. Establecer el tono del juego
                    3. Introducir brevemente el contexto sin revelar demasiado
                    4. Ser visualmente atractivo para la generación de imágenes"""
                },
                {
                    "role": "user",
                    "content": f"""Crea un evento inicial previo a las escenas principales para el juego "{game_db.get('title', 'Sin título')}" basándote en la siguiente información:

                    Historia/Guión del juego:
                    {script[:2000]}...  # Limitamos para no sobrecargar el prompt

                    Primeras locaciones donde se desarrollará la acción:
                    {locations_info}

                    El evento debe ser una introducción o prólogo que prepare al jugador para lo que está por venir.
                    
                    Genera:
                    - event_name: Un nombre atractivo y descriptivo para este evento inicial (máximo 60 caracteres)
                    - prompt_image: Un prompt detallado en español para generar una imagen que capture la esencia del momento inicial del juego (describe la escena, personajes)
                    - prompt_text: Un texto narrativo que establezca el contexto inicial del juego y enganche al jugador (30 palabras) sea corto y evocador.
                    
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
            return {"error": "Failed to generate initial event content"}

        # Crear el evento usando la función existente create_event_service
        event_data = SchemaCreateEvent(
            name=initial_event_response.event_name,
            prompt_user_image=initial_event_response.prompt_image,
            prompt_user_text=initial_event_response.prompt_text,
            character_id=game_db.get("character_principal"),  # Usar el personaje principal si existe
            type_conversation=None,
            option_number=None,
            state_game_init=str(state_game_db["_id"]),
            state_game_end=None,
            location_state_game_init=first_location_id,
            location_state_game_end=None,
            game_id=game_id,
            is_final=False
        )

        # Crear el evento usando el servicio existente
        created_event = await create_event_service(
            event=event_data,
            user_id=game_provisional_db.get("created_by", "anonymous")
        )

        # Actualizar el juego con el evento inicial
        await db["game"].update_one(
            {"_id": ObjectId(game_id)},
            {"$set": {"event_init": created_event.get("_id")}}
        )

        return {
            "success": True,
            "event": created_event,
            "message": f"Initial event '{initial_event_response.event_name}' created successfully"
        }

    except Exception as e:
        print(f"Error extrayendo y creando evento inicial: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Failed to extract and create initial event: {str(e)}"}


async def create_game_provisional_with_narrative_template(_id_game_provisional: str, template_type: TemplateType):
    """
    Crear un juego provisional usando el sistema de templates de narrativa interactiva.

    Args:
        _id_game_provisional: ID del juego provisional
        template_type: Tipo de template a usar (TemplateType.LEARN, EVALUATION, TRIVIA, SOLVE, EXPERT)
    """
    try:
        # Actualizar estado: Iniciando proceso con templates
        await update_game_provisional_status(_id_game_provisional, "processing", 0,
                                             "Iniciando creación con template de narrativa interactiva.")

        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(_id_game_provisional)})

        if not game_provisional_db:
            await update_game_provisional_status(_id_game_provisional, "error", 0,
                                                 "Game provisional not found in database.")
            return "Game provisional not found"

        # Obtener la definición específica del template
        template_definition = get_template_definition(template_type)

        # Obtener el script del usuario o generar uno desde el archivo
        script_content = game_provisional_db.get('script')

        if not script_content:
            # Si no hay script, generarlo desde el archivo PDF como antes
            await update_game_provisional_status(_id_game_provisional, "downloading_file", 10,
                                                 "Descargando archivo para generar script.")

            file_url = game_provisional_db["file"]
            response = requests.get(file_url)

            if response.status_code == 200:
                data = response.content
                base64_string = base64.b64encode(data).decode("utf-8")

                # Generar script usando GPT con la definición específica del template
                await update_game_provisional_status(_id_game_provisional, "generating_script", 25,
                                                     f"Generando script base para template {template_type.value}.")

                script_response = await openai_generator.generate_gpt(
                    content_prompt=[
                        {
                            "role": "system",
                            "content": f"""Eres un experto en diseño de narrativas interactivas. Tu tarea es crear un script que se adapte específicamente al tipo de template solicitado.

{template_definition}

INSTRUCCIONES PARA EL SCRIPT:
1. Extrae el contenido relevante del documento proporcionado
2. Adapta la narrativa para que se ajuste EXACTAMENTE a la estructura y reglas del template especificado
3. Crea personajes, locaciones y diálogos que funcionen con el tipo de interacción requerido
4. Asegúrate de que la progresión narrativa respete las restricciones del template
5. El script debe ser coherente y educativo, siguiendo las mejores prácticas del tipo de template

El script resultante debe ser una historia completa que permita implementar las interacciones específicas del template {template_type.value}."""
                        },
                        {
                            "role": "user",
                            "content": f"""Basándote en el documento proporcionado y las especificaciones del template {template_type.value}, crea un script narrativo interactivo.

Prompt del usuario: {game_provisional_db.get('prompt_user', 'No prompt provided')}

Asegúrate de que el script permita implementar las reglas específicas del template:
- Para LEARN: Enfoque en exploración y aprendizaje gradual
- Para EVALUATION: Diseñado para recopilar datos sin validación
- Para TRIVIA: Preguntas de conocimiento con progresión condicionada
- Para SOLVE: Resolución de problemas con acceso condicionado al final
- Para EXPERT: Conversaciones abiertas con un experto"""
                        },
                        {
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
                        }
                    ],
                    model="gpt-4o-mini",
                    max_tokens=4096,
                )

                script_content = script_response
            else:
                await update_game_provisional_status(_id_game_provisional, "error", 10,
                                                     f"Error descargando archivo. Estado HTTP: {response.status_code}")
                return "Error downloading file"
        else:
            # Si ya existe un script, adaptarlo al template específico
            await update_game_provisional_status(_id_game_provisional, "adapting_script", 25,
                                                 f"Adaptando script existente para template {template_type.value}.")

            adapted_script_response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f"""Eres un experto en adaptación de narrativas para templates interactivos específicos.

{template_definition}

Tu tarea es adaptar el script existente para que se ajuste perfectamente a las reglas y estructura del template {template_type.value}."""
                    },
                    {
                        "role": "user",
                        "content": f"""Adapta el siguiente script para que funcione específicamente con el template {template_type.value}:

SCRIPT ORIGINAL:
{script_content}

INSTRUCCIONES DE ADAPTACIÓN:
1. Mantén la esencia de la historia original
2. Ajusta la estructura narrativa a las reglas del template
3. Modifica los diálogos y situaciones para que permitan el tipo de interacción requerido
4. Asegúrate de que la progresión respete las restricciones específicas del template
5. Optimiza para el objetivo educativo del template

El script adaptado debe ser coherente con las reglas específicas del template {template_type.value}."""
                    }
                ],
                model="gpt-4o-mini",
                max_tokens=4096,
            )

            script_content = adapted_script_response

        # Crear datos para el template con el tipo especificado
        await update_game_provisional_status(_id_game_provisional, "creating_template", 40,
                                             f"Creando template tipo {template_type.value} con script adaptado.")

        script_data = SchemaGenerateFromScript(
            script=script_content,
            template_type=template_type,
            title=game_provisional_db.get('title', 'Historia Interactiva'),
            num_scenes=game_provisional_db.get('num_scenes', 3),
            category=game_provisional_db.get('category', 'Learning')
        )

        # Generar el template de narrativa
        template_id = await create_narrative_template_from_script(script_data)

        # Actualizar estado: Extrayendo elementos del template
        await update_game_provisional_status(_id_game_provisional, "extracting_elements", 70,
                                             "Extrayendo personajes, locaciones y eventos del template.")

        # Extraer elementos del template
        extraction_result = await extract_template_elements(template_id)

        # Actualizar estado: Creando componentes del juego
        await update_game_provisional_status(_id_game_provisional, "creating_game_components", 85,
                                             "Creando personajes, locaciones y eventos en la base de datos.")

        # Crear componentes del juego basados en la extracción
        game_components = await create_game_components_from_template(extraction_result, _id_game_provisional)

        # Actualizar el juego provisional con los IDs de los componentes creados
        await db["game_provisional"].update_one(
            {"_id": ObjectId(_id_game_provisional)},
            {"$set": {
                "template_id": template_id,
                "template_type": template_type.value,
                "template_definition": template_definition,  # Guardar la definición usada
                "script": script_content,  # Actualizar con el script adaptado
                "characters_id": game_components["characters"],
                "locations_id": game_components["locations"],
                "events_id": game_components["events"],
                "narrative_structure": extraction_result.dict(),
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        # Finalizar proceso
        await update_game_provisional_status(_id_game_provisional, "completed", 100,
                                             f"Juego provisional creado exitosamente con template {template_type.value}.")

        return f"Game provisional created successfully with template {template_id}"

    except Exception as e:
        await update_game_provisional_status(_id_game_provisional, "error", 0,
                                             f"Error en creación con template: {str(e)}")
        return f"Error creating game provisional with template: {str(e)}"


async def create_game_components_from_template(extraction_result: SchemaTemplateExtractionResult,
                                               game_provisional_id: str) -> dict:
    """
    Crea los componentes del juego (personajes, locaciones, eventos) basados en la extracción del template.
    """
    created_components = {
        "characters": [],
        "locations": [],
        "events": []
    }

    try:
        # Crear personajes
        for character_data in extraction_result.characters:
            character_id = str(uuid4())
            character_doc = {
                "_id": ObjectId(),
                "character_id": character_id,
                "name": character_data.get("name", "Personaje"),
                "description": character_data.get("description", ""),
                "personality": character_data.get("personality", ""),
                "game_provisional_id": game_provisional_id,
                "template_reference": extraction_result.template_id,
                "created_at": datetime.now(pytz.utc),
                "created_by": "template_system"
            }

            await db["characters"].insert_one(character_doc)
            created_components["characters"].append(character_id)

        # Crear locaciones
        for location_data in extraction_result.locations:
            location_id = str(uuid4())
            location_doc = {
                "_id": ObjectId(),
                "location_id": location_id,
                "name": location_data.get("name", "Locación"),
                "description": location_data.get("description", ""),
                "environment": location_data.get("environment", ""),
                "game_provisional_id": game_provisional_id,
                "template_reference": extraction_result.template_id,
                "created_at": datetime.now(pytz.utc),
                "created_by": "template_system"
            }

            await db["locations"].insert_one(location_doc)
            created_components["locations"].append(location_id)

        # Crear eventos
        for event_data in extraction_result.events:
            event_id = str(uuid4())
            event_doc = {
                "_id": ObjectId(),
                "event_id": event_id,
                "name": event_data.get("event_name", "Evento"),
                "description": event_data.get("description", ""),
                "event_type": event_data.get("event_type", "narrative"),
                "is_intro": event_data.get("is_intro", False),
                "is_final": event_data.get("is_final", False),
                "condition_type": event_data.get("condition_type", "always"),
                "game_provisional_id": game_provisional_id,
                "template_reference": extraction_result.template_id,
                "created_at": datetime.now(pytz.utc),
                "created_by": "template_system"
            }

            await db["events"].insert_one(event_doc)
            created_components["events"].append(event_id)

        return created_components

    except Exception as e:
        raise Exception(f"Error creando componentes del juego: {str(e)}")


async def get_narrative_template_status(_id_game_provisional: str):
    """
    Obtiene el estado de generación del template de narrativa para un juego provisional.
    """
    try:
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(_id_game_provisional)})

        if not game_provisional_db:
            return {"error": "Game provisional not found"}

        template_id = game_provisional_db.get("template_id")

        if not template_id:
            return {"status": "no_template", "message": "No template associated with this game"}

        template_status = await get_template_generation_status(template_id)

        if not template_status:
            return {"error": "Template status not found"}

        return {
            "template_id": template_id,
            "status": template_status.status,
            "progress": template_status.progress,
            "progress_text": template_status.progress_text,
            "current_step": template_status.current_step,
            "estimated_time_remaining": template_status.estimated_time_remaining
        }

    except Exception as e:
        return {"error": f"Error retrieving template status: {str(e)}"}


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
Un recorrido narrativo enfocado en aprender un concepto. Cada escena ofrece dos posibles caminos (Two Ways), generando exploración y reforzando el aprendizaje. Siempre se llega al evento final.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ (Presentación del tema a aprender)
- Escena A: Personajes con interacción "Two Ways" (2 caminos de exploración)
- Evento A → B: ✅ (Transición que refuerza lo aprendido)
- Escena B: Personajes con interacción "Two Ways" (2 caminos de profundización)
- Evento B → C: ✅ (Consolidación del conocimiento)
- Escena C: Personajes con interacción "Two Ways" (2 caminos de aplicación)
- Evento Final: ✅ (Resumen y conclusiones del aprendizaje)

REGLAS ESPECÍFICAS:
- Interacciones tipo "Two Ways" (dos caminos) de 4 a 6 opciones
- Todas las rutas llevan al progreso (sin bloqueos por respuestas incorrectas)
- Enfoque en exploración y comprensión gradual del concepto
- Las contrarespuestas varían para enriquecer el aprendizaje
- Objetivo: Enseñar y reforzar conocimientos de manera interactiva
""",

        TemplateType.EVALUATION: """
TEMPLATE TIPO: EVALUATION (Evaluación o Data Collection)

DEFINICIÓN:
Diseñado para recoger información del jugador. Combina respuestas cerradas (2way) con una opción abierta (OpenA). La contrarespuesta del personaje es siempre la misma, independientemente de lo que se elija, porque lo importante es capturar datos y no validar respuestas.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ (Explicación del propósito de la evaluación)
- Escena A: Personajes con interacción "Two Ways + OpenA" (recolección de datos)
- Evento A → B: ✅ (Transición neutral)
- Escena B: Personajes con interacción "Two Ways + OpenA" (más datos)
- Evento B → C: ✅ (Transición neutral)
- Escena C: Personajes con interacción "Two Ways + OpenA" (finalización de datos)
- Evento Final: ✅ (Agradecimiento por participar)

REGLAS ESPECÍFICAS:
- No hay respuestas incorrectas (2way de 2 a 4 opciones + OpenA)
- La contrarespuesta del personaje siempre es la misma, independiente de la respuesta del jugador
- Enfoque en recopilación de información, opiniones o preferencias
- Sin validación de respuestas - todas son válidas
- Objetivo: Capturar datos del usuario de manera conversacional
""",

        TemplateType.TRIVIA: """
TEMPLATE TIPO: TRIVIA (Test de Conocimientos)

DEFINICIÓN:
Formato de prueba de conocimiento. Cada escena presenta preguntas con múltiples opciones. Solo se avanza si se responde correctamente. El personaje da contrarespuestas distintas según acierto o error, reforzando el aprendizaje mediante retroalimentación.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ (Presentación del desafío de conocimientos)
- Escena A: Personajes con interacción "Two Ways + Multiple" (pregunta de trivia)
- Evento A → B: ✅ (Solo si respuesta es correcta)
- Escena B: Personajes con interacción "Two Ways + Multiple" (segunda pregunta)
- Evento B → C: ✅ (Solo si respuesta es correcta)
- Escena C: Personajes con interacción "Two Ways + Multiple" (pregunta final)
- Evento Final: ✅ (Solo acceden quienes responden todas correctamente)

REGLAS ESPECÍFICAS:
- Si hay error, el jugador solo avanza al responder correctamente (2way de 2 a 4 opciones)
- La contrarespuesta del personaje cambia según si acierta o falla
- Progresión bloqueada hasta respuesta correcta
- Retroalimentación educativa en respuestas incorrectas
- Objetivo: Evaluar y enseñar conocimientos específicos
""",

        TemplateType.SOLVE: """
TEMPLATE TIPO: SOLVE (Resolución de Problemas)

DEFINICIÓN:
Basado en resolver un problema o reto. El jugador avanza a través de decisiones (Two Ways) y finalmente enfrenta una escena abierta (2way + OpenA). Solo quienes resuelven correctamente acceden al evento final, diferenciando entre éxito o fracaso.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ (Presentación del problema a resolver)
- Escena A: Personajes con interacción "Two Ways" (análisis del problema)
- Evento A → B: ✅ (Progresión en la resolución)
- Escena B: Personajes con interacción "Two Ways" (desarrollo de la solución)
- Evento B → C: ✅ (Aproximación a la solución)
- Escena C: Personajes con interacción "Two Ways + OpenA" (propuesta de solución)
- Evento Final: ✅ (Solo acceden quienes resuelven correctamente)

REGLAS ESPECÍFICAS:
- Interacciones 2way de 2 a 4 opciones en escenas A y B
- Escena C combina opciones cerradas con respuesta abierta
- Contrarespuesta del personaje distinta según acierto o error
- Acceso al evento final condicionado a resolver correctamente
- Objetivo: Desarrollar habilidades de resolución de problemas
""",

        TemplateType.EXPERT: """
TEMPLATE TIPO: EXPERT (Consulta con Experto)

DEFINICIÓN:
Orientado a conversaciones abiertas con un experto. Cada escena es tipo OpenTalk, permitiendo diálogo libre. El cierre siempre lleva a la misma contrarespuesta final, sin importar el camino recorrido, porque el objetivo es explorar ideas o reflexiones.

ESTRUCTURA REQUERIDA:
- Evento Intro: ✅ (Presentación del experto y tema de consulta)
- Escena A: Personajes con interacción "OpenTalk" (conversación libre)
- Evento A → B: ✅ (Transición conversacional)
- Escena B: Personajes con interacción "OpenTalk" (profundización del diálogo)
- Evento B → C: ✅ (Continuación de la consulta)
- Escena C: Personajes con interacción "OpenTalk" (cierre conversacional)
- Evento Final: ✅ (Síntesis y despedida del experto)

REGLAS ESPECÍFICAS:
- Todas las interacciones son tipo "OpenTalk" (conversación abierta)
- La contrarespuesta final del personaje siempre es la misma, independiente de la conversación
- Sin restricciones en el flujo conversacional
- Enfoque en exploración de ideas y intercambio de conocimientos
- Objetivo: Facilitar consultas expertas y reflexiones profundas
"""
    }

    return definitions.get(template_type, "Template type not found")
