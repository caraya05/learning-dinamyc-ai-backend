import base64
import traceback
import json
import requests
import asyncio

from bson import ObjectId
from pydantic import BaseModel, Field

from character.schemas import SchemaCreateCharacter
from config import settings
from core import db
from event.schemas import SchemaCreateEvent
from game.tasks_provisional import update_game_provisional_status, get_template_definition, get_template_prompt, \
    create_game_service, deactivate_character_service, create_location_service, create_character_service, \
    create_event_service, new_interaction_character_service
from gpt_ai.utils import openai_generator
from location.schemas import SchemaCreateLocation
from state_game.services import create_state_game
from task.services import create_task_service
from tasks_shared import generate_image_character_shared_task, detection_voice_character_task
from tasks_shared import generate_image_event_shared_task


class TaskCreateGameProvisional(BaseModel):
    script: str = Field(..., example="script", description="Script extens for the game  in text format")
    title: str = Field(..., example="title", description="Title for the game provisional")
    num_scenes: int = Field(..., example=1, description="Number of scenes in the game provisional")
    category: str = Field(..., example="Learning", description="Category of the game based on its content and purpose")


async def create_game_provisional_2(_id_game_provisional: str, _user_id: str = None) -> str:
    """
    Create a provisional game entry in the database.
    """

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

        # Extracción robusta del script y del objeto de respuesta
        script = None
        source_game_obj = None
        if isinstance(source_game_response, dict):
            script = source_game_response.get("script")
            try:
                source_game_obj = TaskCreateGameProvisional(**source_game_response)
            except Exception:
                source_game_obj = None
        elif hasattr(source_game_response, "script"):
            script = getattr(source_game_response, "script")
            source_game_obj = source_game_response
        elif isinstance(source_game_response, str):
            try:
                data = json.loads(source_game_response)
                script = data.get("script")
                source_game_obj = TaskCreateGameProvisional(**data)
            except Exception:
                script = None
                source_game_obj = None

        if not script:
            await update_game_provisional_status(_id_game_provisional, "error", 25,
                                                 "No se pudo extraer el script del resultado de la IA.")
            return "Failed to generate game provisional"

        await db["game_provisional"].update_one({
            "_id": ObjectId(_id_game_provisional)
        }, {
            "$set": {
                "script": script,
                "title": source_game_obj.title if source_game_obj else game_provisional_db.get("title", "Untitled"),
                "num_scenes": source_game_obj.num_scenes if source_game_obj else game_provisional_db.get("num_scenes",
                                                                                                         0),
                "category": source_game_obj.category if source_game_obj else game_provisional_db.get("category",
                                                                                                     "General"),
            }
        })

        # Verificar si estamos en modo test para omitir generación de imágenes
        if settings.MODE_TEST:
            await update_game_provisional_status(_id_game_provisional, "skipping_image_test", 80,
                                                 "Test mode active: skipping image generation and upload.")
            url_image = "https://storage.googleapis.com/qwestar/voxel_.jpg"
        else:
            characters = await extract_characters_from_script(script)
            await db["game_provisional"].update_one(
                {"_id": ObjectId(_id_game_provisional)},
                {"$set": {"characters": [character.dict() for character in characters]}}
            )

            # Generar tareas para cada personaje (si hay)
            last_task_character_id = None
            for character in characters:
                task_character = generate_image_character_shared_task.delay(
                    _id_game_provisional,
                    character.visual_description,
                    character.gender,
                    character.id,
                    _id_game_provisional
                )

                # Guardar último id de tarea para uso opcional en el estado
                last_task_character_id = task_character.id

                task_db = await create_task_service(
                    _task_id=task_character.id,
                    _user_id=_user_id,
                    _task_data={},
                    _element_id=_id_game_provisional,
                    _element_type="game_provisional",
                    _process="create_image_character",
                )

                task_character_2 = detection_voice_character_task.delay(
                    _prompt_user=character.visual_description,
                    _gender=character.gender,
                    _id_character=character.id,
                    _game_provisional=_id_game_provisional,
                    _user_id=_user_id
                )

                task_db = await create_task_service(
                    _task_id=task_character_2.id,
                    _user_id=_user_id,
                    _task_data={},
                    _element_id=_id_game_provisional,
                    _element_type="game_provisional",
                    _process="detection_voice_character",
                )

            # Actualizar estado solo si se creó al menos una tarea
            if last_task_character_id and len(characters) > 0:
                try:
                    character_name = characters[0].name
                except Exception:
                    character_name = ""
                await update_game_provisional_status(_id_game_provisional, "create_image_character", 40,
                                                     f"Creating image generation for character '{character_name}'",
                                                     task=last_task_character_id)

            locations = await extract_locations_from_script(script, characters)
            await db["game_provisional"].update_one(
                {"_id": ObjectId(_id_game_provisional)},
                {"$set": {"locations": [location.dict() for location in locations]}}
            )

            await update_game_provisional_status(_id_game_provisional, "extract_locations", 50,
                                                 "Extracts locations from script")

            events = await extract_events_from_script(script, characters, locations)
            await db["game_provisional"].update_one(
                {"_id": ObjectId(_id_game_provisional)},
                {"$set": {"events": [event.dict() for event in events]}}
            )

            event_intro = next((e for e in events if e.type and str(e.type).lower() == "scene_start"), None)
            if event_intro:
                task_event = generate_image_event_shared_task.delay(
                    _id_game_provisional,
                    event_intro.visual_description,
                    event_intro.id,
                    _id_game_provisional,
                    True
                )

                task_db = await create_task_service(
                    _task_id=task_event.id,
                    _user_id=_user_id,
                    _task_data={},
                    _element_id=_id_game_provisional,
                    _element_type="game_provisional",
                    _process="create_image_event",
                )

                await update_game_provisional_status(_id_game_provisional, "create_image_event", 60,
                                                     "Creating image generation for intro event",
                                                     task=str(task_event.id))

            interactions = await extract_interactions_from_script(script, locations, characters)
            await db["game_provisional"].update_one(
                {"_id": ObjectId(_id_game_provisional)},
                {"$set": {"interactions": [interaction.dict() for interaction in interactions]}}
            )

            # Guardar la lista ya serializada en la base de datos
            events_serialized = [
                event.dict() if hasattr(event, "dict") else event
                for event in events
            ]

            await db["game_provisional"].update_one(
                {"_id": ObjectId(_id_game_provisional)},
                {"$set": {"events": events_serialized}}
            )

            await update_game_provisional_status(_id_game_provisional, "extract_interaction", 70,
                                                 "Extracts interactions from script")

        return "game provisional created successfully"
    except Exception as e:
        # Actualizar estado: Error
        print(traceback.format_exc())
        await update_game_provisional_status(_id_game_provisional, "error", 0, f"Unexpected error occurred: {str(e)}")
        # logger.error(f"Error en create_game_provisional: {str(e)}")
        # logger.debug(traceback.format_exc())
        return "Failed to create game provisional"


class CharactersProvisional(BaseModel):
    id: str = Field(..., example="character_1", description="Unique identifier for the character")
    name: str = Field(..., example="Character Name", description="Name of the character")
    role: str = Field(..., example="principal",
                      description="Role of the character in the game, if principal or secondary, just one principal")
    visual_description: str = Field(..., example="A brave hero...", description="Description of the character")
    gender: str = Field(..., example="male", description="Gender of the character, e.g., male, female, animal, other")


class TasksCreateCharactersProvisional(BaseModel):
    characters: list[CharactersProvisional] = Field(..., example=[],
                                                    description="List of characters for the game provisional")


async def extract_characters_from_script(script: str) -> list[CharactersProvisional]:
    """
    Extract characters from the provided script using OpenAI's GPT model.
    """
    try:
        prompt = f"""
        Extract the main characters from the following game script. Provide a list of characters with their names, 
        roles (principal or secondary), and visual descriptions. Ensure there is only one principal character.
        Script:
        {script}
        """
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system", "content": "You are an expert game designer assistant."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4.1",
            response_format=TasksCreateCharactersProvisional,
            type_generation="extract_characters",
            user_id=None,
            max_tokens=16384,
        )
        # Manejo robusto de la respuesta
        if isinstance(response, str):
            import json
            try:
                data = json.loads(response)
                response_obj = TasksCreateCharactersProvisional(**data)
            except Exception:
                response_obj = None
        elif isinstance(response, dict):
            try:
                response_obj = TasksCreateCharactersProvisional(**response)
            except Exception:
                response_obj = None
        else:
            response_obj = response
        if response_obj and hasattr(response_obj, "characters"):
            return response_obj.characters
        else:
            return []
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        return []


class EventsProvisional(BaseModel):
    id: str = Field(..., example="event_1", description="Unique identifier for the event")
    description: str = Field(..., example="The hero arrives at the village...", description="Description of the event")
    visual_description: str = Field(..., example="A bustling medieval village...",
                                    description="Visual description of the event")
    type: str = Field(..., example="event", description="Type of the event, e.g., event_inter, scene_start, scene_end")
    id_characters: list[str] = Field(..., example=["character_1"],
                                     description="List of character IDs involved in this event")
    order: int = Field(..., example=1, description="Order of the event in the sequence of events")
    id_location_start: str = Field(..., example="location_1", description="ID of the starting location for this event")
    id_location_end: str = Field(..., example="location_2", description="ID of the ending location for this event")


class TasksCreateEventsProvisional(BaseModel):
    events: list[EventsProvisional] = Field(..., example=[], description="List of events for the game provisional")


async def extract_events_from_script(script: str, characters, locations) -> list[EventsProvisional]:
    """
    Extract events from the provided script using OpenAI's GPT model.
    """
    try:
        prompt = f"""
        Extract only the first event of type 'scene_start' (the intro event) from the following game script. 
        Provide its description, visual description, and type. Do not extract any other events.
        Script:
        {script}
        Characters available (with their IDs):
        {characters}
        Locations available (with their IDs):
        {locations}
        """
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system", "content": "You are an expert game designer assistant."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4.1",
            response_format=TasksCreateEventsProvisional,
            type_generation="extract_events",
            user_id=None,
            max_tokens=16384,
        )
        # Manejo robusto de la respuesta
        if isinstance(response, str):
            import json
            try:
                data = json.loads(response)
                response_obj = TasksCreateEventsProvisional(**data)
            except Exception:
                response_obj = None
        elif isinstance(response, dict):
            try:
                response_obj = TasksCreateEventsProvisional(**response)
            except Exception:
                response_obj = None
        else:
            response_obj = response
        if response_obj and hasattr(response_obj, "events"):
            return response_obj.events
        else:
            return []
    except Exception as e:
        print(traceback.format_exc())
        return []


class LocationsProvisional(BaseModel):
    id: str = Field(..., example="location_1", description="Unique identifier for the location")
    name: str = Field(..., example="Enchanted Forest", description="Name of the location")
    visual_description: str = Field(..., example="A mystical forest with glowing plants...",
                                    description="Visual description of the location")
    description_situacional: str = Field(..., example="The forest is filled with magical creatures...",
                                         description="Situational description of the location")
    id_characters: list[str] = Field(..., example=["character_1"],
                                     description="List of character IDs present in this location")
    order: int = Field(..., example=1, description="Order of the location in the sequence of locations")
    id_characters_reused: list[str] = Field(..., example=["character_2"],
                                            description="List of character IDs reused from previous locations")


class TasksCreateLocationsProvisional(BaseModel):
    locations: list[LocationsProvisional] = Field(..., example=[],
                                                  description="List of locations for the game provisional")


async def extract_locations_from_script(script: str, characters) -> list[LocationsProvisional]:
    """
    Extract locations from the provided script using OpenAI's GPT model.
    """
    try:
        prompt = f"""
        Extract the main locations from the following game script. Provide a list of locations with their names,
        visual descriptions, descriptions situacional and characters present in each location.

        IMPORTANT: In the visual description of each location, include descriptions of adjacent or nearby places to create
        a sense of depth and make the spaces appear distant from each other.

        Script:
        {script}
        Characters available (with their IDs):
        {characters}
        """
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system", "content": "You are an expert game designer assistant."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4.1",
            response_format=TasksCreateLocationsProvisional,
            type_generation="extract_locations",
            user_id=None,
            max_tokens=16384,
        )
        # Manejo robusto de la respuesta
        if isinstance(response, str):
            import json
            try:
                data = json.loads(response)
                response_obj = TasksCreateLocationsProvisional(**data)
            except Exception:
                response_obj = None
        elif isinstance(response, dict):
            try:
                response_obj = TasksCreateLocationsProvisional(**response)
            except Exception:
                response_obj = None
        else:
            response_obj = response
        if response_obj and hasattr(response_obj, "locations"):
            return response_obj.locations
        else:
            return []
    except Exception as e:
        print(traceback.format_exc())
        return []


class ConversationProvisional(BaseModel):
    id_character: str = Field(..., example="character_1", description="Unique identifier for the character")
    dialog: str = Field(..., example="Hello, welcome to our village!", description="Dialogue text for the character")
    audio: str | None = Field(None, example=None, description="ever is None")


class InteractionProvisional(BaseModel):
    id: str = Field(..., example="interaction_1", description="Unique identifier for the interaction")
    type: str = Field(..., example="two_way",
                      description="Type of interaction, e.g., two_way, one_way, option_multiple, open_question, open_talk")
    conversations: list[ConversationProvisional] = Field(..., example=[],
                                                         description="List of conversations involved in this interaction")
    id_location: str = Field(..., example="location_1",
                             description="ID of the location where this interaction takes place")
    id_characters: list[str] = Field(..., example=["character_1"],
                                     description="List of character IDs involved in this interaction")


class TasksCreateInteractionsProvisional(BaseModel):
    interactions: list[InteractionProvisional] = Field(..., example=[],
                                                       description="List of interactions for the game provisional")


async def extract_interactions_from_script(script: str, locations, characters) -> list[InteractionProvisional]:
    """
    Extract interactions from the provided script using OpenAI's GPT model.
    """
    try:
        prompt = f"""
        Extract the main interactions from the following game script. Provide a list of interactions with their types 
        (two_way, one_way, option_multiple, open_question, open_talk), conversations, locations, and characters involved.
        Script:
        {script}
        Locations available (with their IDs):
        {locations}
        Characters available (with their IDs):
        {characters}
        """
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {"role": "system", "content": "You are an expert game designer assistant."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4.1",
            response_format=TasksCreateInteractionsProvisional,
            type_generation="extract_interactions",
            user_id=None,
            max_tokens=16384,
        )
        # Manejo robusto de la respuesta
        if isinstance(response, str):
            import json
            try:
                data = json.loads(response)
                response_obj = TasksCreateInteractionsProvisional(**data)
            except Exception:
                response_obj = None
        elif isinstance(response, dict):
            try:
                response_obj = TasksCreateInteractionsProvisional(**response)
            except Exception:
                response_obj = None
        else:
            response_obj = response
        if response_obj and hasattr(response_obj, "interactions"):
            return response_obj.interactions
        else:
            return []
    except Exception as e:
        print(traceback.format_exc())
        return []


async def async_create_game_provisional_task_2(id_game_provisional: str, user_id: str = None) -> str:
    """
    Asynchronous task to create a provisional game.
    """
    # logger.info(f"Iniciando tarea asíncrona para crear juego provisional con ID: {id_game_provisional}")
    try:
        result = await create_game_provisional_2(_id_game_provisional=id_game_provisional, _user_id=user_id)
        # logger.info(f"Tarea completada para juego {id_game_provisional} con resultado: {result}")
        return result
    except Exception as e:
        #     logger.error(f"Error en tarea async_create_game_provisional_task: {str(e)}")
        #     logger.debug(traceback.format_exc())
        return f"Error: {str(e)}"


def build_game_structure(locations, events, interactions, characters):
    """
    Construye la estructura del juego agrupando por locación, eventos, interacciones y personajes.
    Retorna una lista de dicts serializables para MongoDB.
    """
    estructura = []
    personajes_por_locacion = {
        loc.get("id"): [c for c in characters if c.get("id") in loc.get("id_characters", [])]
        for loc in locations
    }
    interacciones_por_locacion = {}
    for inter in interactions:
        loc_id = inter.get("id_location")
        if loc_id:
            interacciones_por_locacion.setdefault(loc_id, []).append(inter)
    eventos_por_locacion = {}
    for event in events:
        loc_ids = event.get("id_locations", []) if "id_locations" in event else event.get("id_characters", [])
        for loc_id in loc_ids:
            eventos_por_locacion.setdefault(loc_id, []).append(event)
    for loc in locations:
        loc_id = loc.get("id")
        item = {
            "location": loc,
            "event_start": None,
            "event_end": None,
            "interaction": [inter for inter in interacciones_por_locacion.get(loc_id, [])],
            "characters": [c for c in personajes_por_locacion.get(loc_id, [])]
        }
        eventos = eventos_por_locacion.get(loc_id, [])
        if eventos:
            event_start = next((e for e in eventos if e.get("is_start")), None)
            event_end = next((e for e in eventos if e.get("is_end")), None)
            item["event_start"] = event_start if event_start else (eventos[0] if eventos else None)
            item["event_end"] = event_end if event_end else (eventos[-1] if len(eventos) > 1 else None)
        estructura.append(item)
    return estructura


def _validate_and_get_character(chars_mapped, block_characters, principal_id):
    """
    Valida que el personaje esté en la locación actual.
    Si no está, elige un personaje secundario de esa locación.
    """
    block_char_ids = {char["id"] for char in block_characters}

    # Si el personaje mapeado está en la locación, usarlo
    if chars_mapped and chars_mapped[0] in block_char_ids:
        return chars_mapped[0]

    # Si no, buscar un personaje secundario que no sea principal
    for char in block_characters:
        if char["id"] != principal_id:
            return char.get("id")

    # Si no hay personajes secundarios, devolver None
    return None


async def async_continue_create_game_provisional_2(_id_game_provisional: str, _user_id: str = None) -> str:
    """
    Continue creating a provisional game entry in the database.
    Proceso dividido en fases: estados, personajes, locaciones, actualización de locación en personajes,
    interacciones, eventos.
    """
    try:
        def _extract_id(obj):
            try:
                if obj is None:
                    return None
                if isinstance(obj, dict):
                    return str(obj.get("_id") or obj.get("id") or obj.get("inserted_id") or "")
                if hasattr(obj, "get"):
                    v = obj.get("_id") if obj.get("_id") else obj.get("id")
                    return str(v) if v else repr(obj)
                if hasattr(obj, "_id"):
                    return str(getattr(obj, "_id"))
                return str(obj)
            except Exception:
                return repr(obj)

        game_provisional_db = await db["game_provisional"].find_one({"_id": ObjectId(_id_game_provisional)})

        game_structure = create_game_structure(
            locations=game_provisional_db.get("locations", []),
            events=game_provisional_db.get("events", []),
            interactions=game_provisional_db.get("interactions", []),
            characters=game_provisional_db.get("characters", [])
        )

        id_map_characters = {}
        id_map_locations = {}
        id_map_events = {}
        id_map_states = {}

        # Diccionarios con información del estado de juego
        id_map_characters_detailed = {}  # {provisional_id: {db_id, state_game_id}}
        id_map_locations_detailed = {}  # {provisional_id: {db_id, state_game_id}}
        id_map_events_detailed = {}  # {provisional_id: {db_id, state_game_id}}

        game_db = await create_game_service(user_id=str(game_provisional_db.get("created_by", "anonymous")))

        event_start = game_provisional_db.get("events", [])[0] if game_provisional_db.get("events", []) else None

        await db["game"].update_one({"_id": game_db.get("_id")}, {"$set": {
            "title": game_provisional_db.get("title"),
            "history": game_provisional_db.get("script"),
            "image": event_start.get("image") if event_start else None,
            "image_minimalist": event_start.get("image") if event_start else None,
            "created_by": game_provisional_db.get("created_by", "anonymous"),
            "updated_by": game_provisional_db.get("created_by", "anonymous"),
            "provisional_id": str(game_provisional_db.get("_id")),
            "category_id": game_provisional_db.get("category"),
            "is_active": True
        }})

        await db["game_provisional"].update_one(
            {"_id": ObjectId(_id_game_provisional)},
            {"$set": {"game_id": str(game_db.get("_id"))}}
        )

        state_game_db = await db["state_game"].find_one({"game_id": str(game_db.get("_id")), "order": 1})
        id_map_states[str(1)] = str(state_game_db.get("_id"))

        total_blocks = len(game_structure)

        for i in range(1, total_blocks):
            order = i + 1
            state_game_new = await create_state_game(
                game_id=str(game_db.get("_id")),
                order=order,
                created_by=str(game_provisional_db.get("created_by", "anonymous"))
            )
            id_map_states[str(order)] = str(state_game_new.get("_id"))

        total_characters = sum(len(block["characters"]) for block in game_structure)
        current_character_index = 0
        last_task_character_id = None

        for index, block in enumerate(game_structure):
            state_for_chars = id_map_states.get(str(index + 1))
            for char in block["characters"]:
                current_character_index += 1
                progress = 40 + int((current_character_index / total_characters) * 10) if total_characters > 0 else 40

                if char["id"] in id_map_characters:
                    await deactivate_character_service(id_map_characters[char["id"]], state_for_chars, True)
                else:
                    character_db = await create_character_service(
                        character=SchemaCreateCharacter(
                            name=char["name"],
                            prompt_user=char["visual_description"],
                            conversation_type=None,
                            options_dialog=None,
                            game_id=str(game_db.get("_id")),
                            location_id=None,
                            state_game=state_for_chars,
                            image=char.get("image", None),
                            gender=char.get("gender", None),
                            voice_id=char.get("voice_id", None),
                            conversation=None
                        ),
                        user_id=game_provisional_db.get("created_by", "anonymous"),
                        game_id=str(game_db.get("_id")),
                        file=None
                    )
                    created_char_id = _extract_id(character_db)
                    id_map_characters[char["id"]] = created_char_id
                    # Guardar mapeo detallado con estado de juego
                    id_map_characters_detailed[char["id"]] = {
                        "db_id": created_char_id,
                        "state_game_id": state_for_chars,
                        "state_game_order": index + 1
                    }
                    last_task_character_id = created_char_id

                    await update_game_provisional_status(
                        _id_game_provisional,
                        "create_image_character",
                        progress,
                        f"Creating image generation for character '{char['name']}'",
                        task=last_task_character_id
                    )
                    await asyncio.sleep(10)

        total_locations = len(
            [loc for block in game_structure for loc in [block["location"]] if loc["id"] not in id_map_locations])
        current_location_index = 0

        for index, block in enumerate(game_structure):
            loc = block["location"]
            if loc["id"] in id_map_locations:
                continue
            current_location_index += 1
            progress = 50 + int((current_location_index / total_locations) * 10) if total_locations > 0 else 50

            location_db = await create_location_service(
                location=SchemaCreateLocation(
                    title=loc["name"],
                    prompt_user=loc["visual_description"],
                    prompt_user_description=loc["description_situacional"],
                    game_id=str(game_db.get("_id")),
                    state_game=id_map_states[str(index + 1)]
                ),
                user_id=str(game_provisional_db.get("created_by", "anonymous")),
                file=None
            )
            created_loc_id = _extract_id(location_db)
            id_map_locations[loc["id"]] = created_loc_id
            # Guardar mapeo detallado con estado de juego
            id_map_locations_detailed[loc["id"]] = {
                "db_id": created_loc_id,
                "state_game_id": id_map_states[str(index + 1)],
                "state_game_order": index + 1
            }

            await update_game_provisional_status(
                _id_game_provisional,
                "create_location",
                progress,
                f"Creating location '{loc['name']}'",
                task=created_loc_id
            )
            await asyncio.sleep(10)

        principal_char = next(
            (char for char in game_provisional_db.get("characters", []) if
             str(char.get("role")).lower() == "principal"),
            None
        )

        if principal_char and principal_char.get("id") in id_map_characters:
            await db["game"].update_one(
                {"_id": ObjectId(str(game_db.get("_id")))},
                {"$set": {"character_principal": id_map_characters[principal_char["id"]]}}
            )

        for index, block in enumerate(game_structure):
            created_loc_id = id_map_locations.get(block["location"]["id"])
            for char in block["characters"]:
                state_glic_db = await db["state_glic"].find_one(
                    {"element_id": id_map_characters[char["id"]], "state": id_map_states[str(index + 1)]}
                )
                if state_glic_db:
                    await db["state_glic"].update_one(
                        {"_id": state_glic_db["_id"]},
                        {"$set": {"data.locations_id": [str(created_loc_id)]}}
                    )

        principal_orig_id = principal_char.get("id") if principal_char else None

        total_interactions = sum(len(block["interaction"]) for block in game_structure)
        current_interaction_index = 0

        for index, block in enumerate(game_structure):
            for inter in block["interaction"]:
                current_interaction_index += 1
                progress = 60 + int(
                    (current_interaction_index / total_interactions) * 10) if total_interactions > 0 else 60

                inter_location_mapped = id_map_locations.get(inter["id_location"], inter["id_location"])
                inter_characters_mapped = [
                    id_map_characters[cid]
                    for cid in inter.get("id_characters", [])
                    if cid in id_map_characters and cid != principal_orig_id
                ]

                for conv in inter["conversations"]:
                    if conv.get("id_character") in id_map_characters:
                        conv["id_character"] = id_map_characters[conv["id_character"]]

                inter_db = await new_interaction_character_service(
                    location_id=inter_location_mapped,
                    game_id=str(game_db.get("_id")),
                    character_id=inter_characters_mapped[0] if inter_characters_mapped else None,
                    conversation_type=inter["type"],
                    conversation=inter["conversations"],
                    user_id=game_provisional_db.get("created_by", "anonymous"),
                    options_dialog=None,
                    state_game=id_map_states[str(index + 1)]
                )

                await update_game_provisional_status(
                    _id_game_provisional,
                    "create_interaction",
                    progress,
                    "Creating interaction at location",
                    task=_extract_id(inter_db) if inter_db else None
                )
                await asyncio.sleep(10)

        for index, block in enumerate(game_structure):
            for event_type in ["event_start", "event_end"]:
                event = block.get(event_type)
                if not event:
                    continue

                if hasattr(event, "dict"):
                    try:
                        event = event.dict()
                    except Exception:
                        event = {k: getattr(event, k, None) for k in
                                 ("id_location_start", "id_location_end", "id_characters", "interaction_type")}

                loc_start = id_map_locations.get(event.get("id_location_start") or event.get("id_location"),
                                                 event.get("id_location_start"))
                loc_end = id_map_locations.get(event.get("id_location_end") or event.get("id_location"), loc_start)

                principal_char = next(
                    (char for char in game_provisional_db.get("characters", []) if
                     str(char.get("role")).lower() == "principal"),
                    None
                )

                chars_mapped = [id_map_characters[cid] for cid in id_map_characters.keys()
                                if cid != principal_char["id"]][0:1] if principal_char else []

                created_event = await create_event_service(
                    event=SchemaCreateEvent(
                        name="event start" if event_type == "event_start" else "event end",
                        prompt_user_image=event.get("visual_description", "") if event_type == "event_start" else None,
                        prompt_user_text=event.get("description", "") if event_type == "event_start" else None,
                        character_id=chars_mapped[0] if chars_mapped and event_type != "event_start" else None,
                        type_conversation=event.get("interaction_type"),
                        option_number=0,
                        state_game_init=id_map_states[str(index + 1)],
                        state_game_end=id_map_states[str(index + 1)],
                        location_state_game_init=loc_start,
                        location_state_game_end=loc_start,
                        game_id=str(game_db.get("_id")),
                        is_final=False if event_type == "event_start" else True,
                        audio_mp3=None,
                        audio=None,
                        image=event.get("image", None) if event_type == "event_start" else None
                    ),
                    user_id=game_provisional_db.get("created_by", "anonymous")
                )

                # Guardar mapeo de evento
                event_provisional_id = event.get("id")
                if event_provisional_id:
                    id_map_events[event_provisional_id] = str(created_event.get("_id"))
                    # Guardar mapeo detallado con estado de juego
                    id_map_events_detailed[event_provisional_id] = {
                        "db_id": str(created_event.get("_id")),
                        "state_game_id": id_map_states[index + 1],
                        "state_game_order": index + 1,
                        "event_type": event_type
                    }

                event_field = "event_end" if event_type == "event_end" else "event_init"
                await db["game"].update_one(
                    {"_id": ObjectId(str(game_db.get("_id")))},
                    {"$set": {event_field: str(created_event.get("_id"))}}
                )

            if block.get("events_middle", None):
                for event in block.get("events_middle", []):
                    if hasattr(event, "dict"):
                        try:
                            event = event.dict()
                        except Exception:
                            event = {k: getattr(event, k, None) for k in
                                     ("id_location_start", "id_location_end", "id_characters", "interaction_type")}

                    loc_start = id_map_locations.get(event.get("id_location_start"), event.get("id_location_start"))
                    loc_end = id_map_locations.get(event.get("id_location_end"), event.get("id_location_end"))
                    principal_char = next(
                        (char for char in game_provisional_db.get("characters", []) if
                         str(char.get("role")).lower() == "principal"),
                        None
                    )

                    chars_mapped = [id_map_characters[cid] for cid in id_map_characters.keys()
                                    if cid != principal_char["id"]][0:1] if principal_char else []

                    created_middle_event = await create_event_service(
                        event=SchemaCreateEvent(
                            name="event middle",
                            prompt_user_image=None,
                            prompt_user_text=None,
                            character_id=_validate_and_get_character(
                                chars_mapped,
                                block["characters"],
                                principal_orig_id
                            ),
                            type_conversation=event.get("interaction_type"),
                            option_number=0,
                            state_game_init=id_map_states[str(index + 1)],
                            state_game_end=id_map_states[str(index + 2)] if str(index + 2) in id_map_states else "",
                            location_state_game_init=loc_start,
                            location_state_game_end=loc_end,
                            game_id=str(game_db.get("_id")),
                            is_final=False,
                            audio_mp3=None,
                            audio=None,
                            image=None
                        ),
                        user_id=game_provisional_db.get("created_by", "anonymous")
                    )

                    # Guardar mapeo de evento middle
                    event_provisional_id = event.get("id")
                    if event_provisional_id:
                        id_map_events[event_provisional_id] = str(created_middle_event.get("_id"))
                        # Guardar mapeo detallado con estado de juego
                        id_map_events_detailed[event_provisional_id] = {
                            "db_id": str(created_middle_event.get("_id")),
                            "state_game_id": id_map_states[index + 1],
                            "state_game_order": index + 1,
                            "event_type": "event_inter"
                        }

        await update_game_provisional_status(
            _id_game_provisional,
            "complete_provisional_game",
            70,
            "Game structure creation completed",
            task=str(game_db.get("_id"))
        )
        await asyncio.sleep(10)

        return "Game created successfully from provisional data"

    except Exception as e:
        return f"Failed to create game from provisional: {str(e)}"


def find_created_index(created_list, reused_list):
    """
    Busca los índices de personajes ya creados en la lista creada.

    Args:
        created_list (list[dict]): Lista de personajes ya creados con un campo 'id'.
        reused_list (list[dict]): Lista de personajes reutilizados con un campo 'id'.

    Returns:
        list[int]: Índices de los personajes reutilizados en la lista creada.
    """
    return [idx for char in reused_list for idx, person in enumerate(created_list) if person["id"] == char["id"]]


def create_game_structure(locations, events, interactions, characters):
    """
    Construye la estructura del juego agrupando por locación, eventos, interacciones y personajes.
    Incluye el tipo de interacción en cada evento si existe.
    """
    estructura = []
    personajes_por_locacion = {
        loc["id"]: [c for c in characters if c["id"] in loc.get("id_characters", [])]
        for loc in locations
    }
    interacciones_por_locacion = {}
    for inter in interactions:
        loc_id = inter.get('id_location', None)
        if loc_id:
            interacciones_por_locacion.setdefault(loc_id, []).append(inter)

    events_plus = create_intermediate_events(interactions)

    # Normalizar y combinar events_plus y events; mover 'scene_start' al inicio si existe
    combined_events = []
    for e in events:
        combined_events.append(e.dict() if hasattr(e, "dict") else e)
    for e in events_plus:
        combined_events.append(e.dict() if hasattr(e, "dict") else e)

    eventos_por_locacion = {}
    for event in combined_events:
        for loc_id in [event.get('id_location_start'), event.get('id_location_end')]:
            if loc_id:
                eventos_por_locacion.setdefault(loc_id, []).append(event)

    for idx, loc in enumerate(locations):
        is_last_loc = (idx == len(locations) - 1)
        location_data = loc.dict() if hasattr(loc, 'dict') else loc
        eventos = eventos_por_locacion.get(loc["id"], [])
        eventos_inicio = []
        eventos_final = []
        eventos_intermedios = []

        # Buscar tipo de interacción para esta locación
        interacciones = interacciones_por_locacion.get(loc["id"], [])
        interaction_type = interacciones[0]["type"] if interacciones else None

        for event in eventos:
            tipo = event.get("type")
            event_with_interaction = dict(event)
            event_with_interaction["interaction_type"] = interaction_type

            # Evento de inicio: tipo scene_start y locaciones iguales
            if tipo == "scene_start" and event.get("id_location_start") == event.get("id_location_end"):
                eventos_inicio.append(event_with_interaction)
            # Evento de final: tipo scene_end y locaciones iguales
            elif tipo == "scene_end" and event.get("id_location_start") == event.get("id_location_end"):
                eventos_final.append(event_with_interaction)
            # Evento intermedio: locaciones diferentes
            elif event.get("id_location_start") != event.get("id_location_end"):
                if is_last_loc:
                    # Si es la última locación, no permitir evento intermedio: tratar como final
                    event_with_interaction["type"] = "scene_end"
                    eventos_final.append(event_with_interaction)
                else:
                    eventos_intermedios.append(event_with_interaction)

        item = {
            "location": location_data,
            "event_start": eventos_inicio[0] if eventos_inicio else None,
            "event_end": eventos_final[0] if eventos_final else None,
            "events_middle": eventos_intermedios if eventos_intermedios else None,
            "interaction": [
                inter.dict() if hasattr(inter, 'dict') else inter
                for inter in interacciones
            ],
            "characters": [
                c.dict() if hasattr(c, 'dict') else c
                for c in personajes_por_locacion.get(loc["id"], [])
            ]
        }
        estructura.append(item)
    return estructura


# Evento intermedio entre locaciones, sin imagen
def create_intermediate_events(interactions):
    events = []

    def _get_field(obj, field, default=None):
        if isinstance(obj, dict):
            return obj.get(field, default)
        if hasattr(obj, field):
            return getattr(obj, field)
        if hasattr(obj, "dict"):
            try:
                return obj.dict().get(field, default)
            except Exception:
                return default
        return default

    if not interactions:
        return events

    try:
        n = len(interactions)
    except Exception:
        return events

    if n == 0:
        return events

    for i in range(n):
        inter_start = interactions[i]
        inter_end = interactions[i + 1] if (i + 1) < n else None

        loc_start_id = _get_field(inter_start, "id_location", None)
        loc_end_id = _get_field(inter_end, "id_location", None) if inter_end else loc_start_id

        # Usar solo los characters de la interacción actual (inter_start)
        start_chars = _get_field(inter_start, "id_characters", []) or []

        # Normalizar a lista y deduplicar manteniendo orden
        if not isinstance(start_chars, list):
            try:
                start_chars = list(start_chars)
            except Exception:
                start_chars = [start_chars]

        seen = set()
        chars_in_event = []
        for c in start_chars:
            if c not in seen:
                seen.add(c)
                chars_in_event.append(c)

        # Determinar tipo de evento

        if loc_start_id is not None and loc_start_id == loc_end_id:
            ev_type = "scene_end"
        else:
            ev_type = "event_inter"

        event = {
            "id": f"event_{i + 2}",
            "description": "",
            "visual_description": "",
            "type": ev_type,
            "id_characters": chars_in_event,
            "order": i + 1,
            "id_location_start": loc_start_id,
            "id_location_end": loc_end_id,
        }
        events.append(event)

    return events
