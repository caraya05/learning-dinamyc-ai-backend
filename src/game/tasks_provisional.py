import json

import requests
import base64
from datetime import datetime
from uuid import uuid4
import traceback

import pytz
from bson import ObjectId

from openai import NotGiven

from pydantic import BaseModel
from pydantic import Field

from core.database import db

from gpt_ai.utils import openai_generator

from utils import upload_image

# Configuración del sistema de logs
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger("game_provisional_tasks")

NOT_GIVEN = NotGiven()


class TaskCreateGameProvisional(BaseModel):
    script: str = Field(..., example="script", description="Script for the game provisional")
    title: str = Field(..., example="title", description="Title for the game provisional")
    num_scenes: int = Field(..., example=1, description="Number of scenes in the game provisional")


async def create_game_provisional(_id_game_provisional: str):
    """
    Create a provisional game entry in the database.
    """
    # logger.info(f"Iniciando creación de juego provisional con ID: {_id_game_provisional}")
    try:
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(_id_game_provisional)})

        if not game_provisional_db:
            # logger.warning(f"Juego provisional con ID {_id_game_provisional} no encontrado")
            return "Game provisional not found"

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
            # logger.error(f"Error al descargar archivo. Código de estado: {response.status_code}")
            return "Error generating file"

        # logger.info("Generando contenido del juego con GPT-4.1")
        source_game_response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "system",
                    "content": """Crea un entrenamiento interactivo en formato "elige tu propia aventura" para un nuevo representante de ventas en una empresa de tecnología (TechCorp).
                                El objetivo es enseñar buenas prácticas de ventas a través de decisiones narrativas.
                                Estructura:
                                Introducción breve con contexto.
                                Múltiples escenas (3 a 5), cada una con una situación clave (primera reunión, manejo de objeciones, cierre de venta, etc.)
                                En cada escena, presenta una decisión con 3 opciones (A, B, C).
                                No des la respuesta correcta de inmediato. Permite que el usuario elija y luego ofrece una retroalimentación adaptativa basada en su elección.
                                Usa un tono profesional, pero dinámico y conversacional.
                                Incluye una conclusión que resuma el estilo de ventas del jugador según sus elecciones y ofrezca consejos prácticos."""
                },
                {
                    "role": "user",
                    "content": f"nesecito que me ayudes a crear un juego basado en el archivo PDF proporcionado."
                               f"nesecito que el juego tenga un guion y un titulo ambos en ingles, el guion debe ser una historia que se pueda jugar en formato de texto"
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
            # logger.error("No se recibió respuesta de la API de OpenAI")
            return "Failed to generate game provisional"

        # logger.info(f"Contenido generado correctamente. Título: '{source_game_response.title}'")
        # logger.debug(f"Longitud del guión generado: {len(source_game_response.script)} caracteres")

        # logger.info("Generando imagen de portada para el juego")
        image_game_provisional = await openai_generator.generate_image(
            prompt=f"Genera una imagen de portada en estilo 3D low poly de proporciones realistas para el juego ."
                   f"basado en el  script: {source_game_response.script} "
                   f"que ejemplifique una escena del juego con un personaje principal que represente el estilo del juego, no debe tener texto.",
            model="gpt-image-1",
            size="1024x1536",
            style=None
        )

        # logger.debug("Imagen generada, decodificando base64")
        image_bytes = base64.b64decode(image_game_provisional)

        # logger.info("Subiendo imagen a almacenamiento")
        url_image = upload_image(
            img_byte_arr=image_bytes,
            file_name=f"game-provisional/{uuid4()}.jpg",
            size=(512, 896)
        )

        if not url_image:
            # logger.error("Error al subir la imagen generada")
            return "Failed to upload image"

        # logger.debug(f"Imagen subida correctamente: {url_image}")

        # logger.info("Actualizando registro en base de datos")
        game_provisional_db["image"] = url_image
        game_provisional_db["title"] = source_game_response.title
        game_provisional_db["script"] = source_game_response.script
        game_provisional_db["updated_at"] = datetime.now(pytz.utc)
        game_provisional_db["num_scenes"] = source_game_response.num_scenes

        await db["game_provisional"].update_one(
            {"_id": ObjectId(_id_game_provisional)},
            {"$set": game_provisional_db}
        )

        # logger.info(f"Juego provisional creado exitosamente: {_id_game_provisional}")
        return "game provisional created successfully"
    except Exception as e:
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
        # Obtenemos el juego provisional
        # logger.debug(f"Buscando juego provisional en base de datos: {id_game_provisional}")
        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(id_game_provisional)})

        if not game_provisional_db:
            # logger.warning(f"Juego provisional con ID {id_game_provisional} no encontrado")
            return "Game provisional not found"

        script = game_provisional_db.get("script")
        if not script:
            # logger.warning(f"El juego provisional {id_game_provisional} no tiene guión")
            return "Script not found in game provisional"

        # logger.debug("Guión encontrado, procediendo a extraer número de escenas")
        # Extraemos el número de escenas del guión
        num_scenes = game_provisional_db.get("num_scenes")

        # Generamos las interacciones para cada escena
        # logger.info(f"Generando interacciones para {num_scenes} escenas")
        scene_interactions = []
        for scene_num in range(1, num_scenes + 1):
            # logger.debug(f"Procesando escena {scene_num}/{num_scenes}")
            interaction = await generate_interaction_for_scene(script, scene_num)
            scene_interactions.append({
                "scene_number": scene_num,
                "interaction": interaction.get("content") ,
            })
            # logger.debug(f"Escena {scene_num} procesada: {len(interaction.get('content', ''))} caracteres")

        # Actualiza la base de datos con los datos serializables
        await db["game_provisional"].update_one(
            {"_id": ObjectId(id_game_provisional)},
            {"$set": {
                "scene_interactions": scene_interactions,
                "updated_at": datetime.now(pytz.utc)
            }}
        )

        # logger.info(f"Generación de interacciones completada exitosamente para juego {id_game_provisional}")
        return f"Successfully generated interactions for {num_scenes} scenes"

    except Exception as e:
        # logger.error(f"Error en generate_scene_interactions: {str(e)}")
        # logger.debug(traceback.format_exc())
        print(traceback.format_exc())
        return f"Failed to generate scene interactions: {str(e)}"

class SceneInteractionResponse(BaseModel):
    content: str = Field(..., description="Contenido de la interacción generada para la escena")

async def generate_interaction_for_scene(script: str, scene_num: int):
    """
    Genera la interacción para una escena específica del guión.

    Args:
        script: El guión completo del juego
        scene_num: El número de la escena para la que generar la interacción

    Returns:
        dict: Un diccionario con la información de interacción para la escena
    """
    # logger.info(f"Generando interacción para escena {scene_num}")
    try:
        # logger.debug(f"Preparando prompt para GPT con escena {scene_num}")
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
