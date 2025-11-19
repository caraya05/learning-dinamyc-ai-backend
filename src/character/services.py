import traceback
from datetime import datetime
from io import BytesIO
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from openai import BaseModel
from pydantic import Field

from celery_worker import generate_character_task
from celery_worker import update_character_task
from celery_worker import generate_voice_character_task
from celery_worker import generate_image_character_task

from character.models import Character
from character.models import CharacterGLIC
from character.schemas import SchemaCreateCharacter, ConversationsCharacter
from character.schemas import CharacterLocationModel

from core.database import db
from gpt_ai.utils import openai_generator
from state_game.services import get_state_game_by_game_id
from state_game.services import get_state_game_by_id
from state_glic.services import create_state_glic
from state_glic.services import get_list_state_glic_by_element_id

from task.services import create_task_service
from task.services import update_task_service
from user.services import validate_star_user_service, disable_user_service
from utils import upload_image


async def get_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    character_db["_id"] = str(character_db["_id"])
    character_db["state_game"] = await get_list_state_glic_by_element_id(character_id)

    return character_db


async def get_characters_service(
        skip: int = 1, limit: int = 100, game_id: str = None, user_id: str = None
):
    try:

        if not game_id:
            characters_db = (
                await db["character"]
                .find({"created_by": user_id})
                .skip((skip - 1) * limit)
                .limit(limit)
                .to_list(None)
            )

        else:
            characters_db = (
                await db["character"]
                .find({"game_id": game_id})
                .skip((skip - 1) * limit)
                .limit(limit)
                .to_list(None)
            )
        for i in characters_db:
            i["_id"] = str(i["_id"])
            i["state_game"] = await get_list_state_glic_by_element_id(i["_id"])
        return characters_db
    except Exception as e:
        print(f"Error in get characters service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def get_all_character_service(user_id: str, skip: int = 1, limit: int = 10):
    try:
        characters_db = await (
            db["character"]
            .find({"created_by": user_id})
            .sort("created_at", -1)
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )

        for i in characters_db:
            i["_id"] = str(i["_id"])
            i["state_game"] = await get_list_state_glic_by_element_id(i["_id"])

        return characters_db
    except Exception as e:
        print(f"Error in get all character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def get_characters_by_location_service(
        skip: int = 1, limit: int = 100, location_id: str = None
):
    try:
        location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
        if not location_db:
            return []

        characters_locations_db = (
            await db["state_glic"]
            .find({"type_element": "character", "data.locations_id": {"$in": [location_id]}})
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )
        if not characters_locations_db:
            return []

        character_ids = [
            ObjectId(character_location["element_id"])
            for character_location in characters_locations_db
        ]
        characters_db = await db["character"].find({"_id": {"$in": character_ids}}).to_list(None)

        for character_db in characters_db:
            character_db["_id"] = str(character_db["_id"])
            character_db["state_game"] = [
                character_location
                for character_location in characters_locations_db
                if character_location["element_id"] == str(character_db["_id"])
            ]

        return characters_db

    except Exception as e:
        print(f"Error in get_characters_by_location_service: {str(e)}")
        return []


async def create_character_service(character: SchemaCreateCharacter, user_id: str, game_id: str, file: UploadFile | None = None):
    try:
        if character.prompt_user:
            response_moderation_prompt_user = await openai_generator.moderation_text(
                text=character.prompt_user, user_id=user_id
            )
            if response_moderation_prompt_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Prompt user not allowed",
                )
        if character.prompt_user_dialog:
            response_moderation_dialog = await openai_generator.moderation_text(
                text=character.prompt_user_dialog, user_id=user_id
            )
            if response_moderation_dialog:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dialog not allowed",
                )

        await validate_star_user_service(user_id=user_id)
        await disable_user_service(user_id=user_id, section="character")

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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File is empty",
                )
            file.file.seek(0)  # Reset file pointer to the beginning
            if file.content_type not in ["image/jpeg", "image/png"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File type not allowed, only jpeg and png",
                )
            if file.content_type == "image/jpeg":
                file_name = f"characters-reference/{uuid4()}.jpg"
            elif file.content_type == "image/png":
                file_name = f"characters-reference/{uuid4()}.png"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File type not allowed, only jpeg and png",
                )
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

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(character_created.inserted_id),
            _element_type="character",
            _process="create_character",
        )

        task_celery = generate_character_task.delay(
            _character_id=str(character_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db["_id"]),
            _location_id=character.location_id,
            _state_game_id=state_game['_id'],
            _game_id=game_id,
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        await db["character"].update_one(
            {"_id": character_created.inserted_id},
            {"$set": {"tasks_request": [str(task_db["_id"])]}},
        )

        if character_db := await db["character"].find_one({"_id": character_created.inserted_id}):
            character_db["task_id"] = str(task_db["_id"])
            character_db["state_game"] = await get_list_state_glic_by_element_id(
                character_created.inserted_id
            )
            return character_db
    except Exception as e:
        print(f"Error in create character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not created",
        )


async def get_character_leading_role_service(game_id: str):
    try:
        character_db = await db['character'].find_one({'game_id': game_id, 'type': 'leading role'})
        if not character_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found",
            )
        return character_db
    except Exception as e:
        print(f"Error in get character leading role service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character not found",
        )


async def update_character_service(
        character_id: str,
        user_id: str,
        name: str = None,
        options_dialog: dict = None,
        prompt_user: str = None,
        dialog: str = None,
        type_dialog: str = None,
        game_id: str = None,
        location_id: str = None,
        state_game: str = None,
):
    try:
        if prompt_user:
            moderation_prompt_user = await openai_generator.moderation_text(
                text=prompt_user, user_id=user_id
            )
            if moderation_prompt_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Prompt user not allowed",
                )
        if dialog:
            moderation_dialog = await openai_generator.moderation_text(text=dialog, user_id=user_id)
            if moderation_dialog:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dialog not allowed",
                )

        await validate_star_user_service(user_id=user_id)
        await disable_user_service(user_id=user_id, section="character")

        if not state_game:
            state_game = await get_state_game_by_game_id(game_id)
        else:
            state_game = await get_state_game_by_id(state_game)

        character_state_db = await db["state_glic"].find_one(
            {"element_id": character_id, "state": state_game["_id"]}
        )

        if not character_state_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State element not found",
            )

        name_or_prompt_user_changed = (
                prompt_user and prompt_user != character_state_db['data']["prompt_user"]
        )

        dialog_changed = (
                                 dialog and dialog != character_state_db['data']["prompt_user_dialog"]
                         ) or (type_dialog and type_dialog != character_state_db['data']["conversation_type"])

        update_fields = {"updated_at": datetime.utcnow()}
        if name is not None:
            update_fields["name"] = name
        if prompt_user is not None:
            update_fields["prompt_user"] = prompt_user

        if name is not None:
            character_state_db["data"]["name"] = name
        if prompt_user is not None:
            character_state_db["data"]["prompt_user"] = prompt_user
        if dialog is not None:
            character_state_db["data"]["prompt_user_dialog"] = dialog
        if type_dialog is not None:
            character_state_db["data"]["conversation_type"] = type_dialog
        if options_dialog is not None:
            character_state_db["data"]["options_dialog"] = options_dialog

        await db["state_glic"].update_one(
            {"_id": character_state_db["_id"]},
            {"$set": {"data": character_state_db["data"]}},
        )

        character_db = await db["character"].find_one({"_id": ObjectId(character_id)})

        if not character_db["game_id"]:
            game_db = await db["game"].find_one({"characters_id": {"$in": [character_id]}})
            if game_db:
                character_db["game_id"] = str(game_db["_id"])
        if name_or_prompt_user_changed or dialog_changed:
            task_db = await create_task_service(
                _task_id="",
                _user_id=user_id,
                _task_data={},
                _element_id=str(character_id),
                _element_type="character",
                _process="update_character",
            )
            task_celery = update_character_task.delay(
                _character_id=str(character_id),
                _user_id=user_id,
                _task_id=str(task_db["_id"]),
                _game_id=character_db["game_id"],
                _updated_data=name_or_prompt_user_changed,
                _updated_voice=dialog_changed,
                _state_game_id=state_game["_id"],
                _location_id=location_id,
            )
            await update_task_service(
                _id=str(task_db["_id"]),
                _task_id=task_celery.id,
            )
            character_db["tasks_request"].append(str(task_db["_id"]))
            await db["character"].update_one(
                {"_id": ObjectId(character_id)},
                {"$set": {"tasks_request": character_db["tasks_request"]}},
            )
            character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
            character_db["task_id"] = str(task_db["_id"])
            character_db["state_game"] = await get_list_state_glic_by_element_id(character_id)
            return character_db
        character_db["state_game"] = await get_list_state_glic_by_element_id(character_id)
        return character_db
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in update character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not updated",
        )


async def generate_image_character_service(character_id: str, user_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    try:
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=character_id,
            _element_type="character",
            _process="generate_image_character",
        )
        task_celery = generate_image_character_task.delay(
            _character_id=character_id, _user_id=user_id, _task_id=str(task_db["_id"])
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery,
        )
        character_db["tasks_request"].append(str(task_db["_id"]))
        await db["character"].update_one(
            {"_id": ObjectId(character_id)},
            {"$set": {"tasks_request": character_db["request_tasks"]}},
        )
        character_db["task_id"] = str(task_db["_id"])
        return character_db
    except Exception as e:
        # print(f"Error in generate image character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not generated",
        )


async def delete_character_service(character_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )
    # if character_db['image']:
    #     delete_image(character_db['image'])
    if (
            character_location_db := await db["character_location"]
                    .find({"character_id": character_id})
                    .to_list(None)
    ):
        for character_location in character_location_db:
            await db["character_location"].delete_one({"_id": character_location["_id"]})
    delete_character = await db["character"].delete_one({"_id": ObjectId(character_id)})
    if delete_character:
        return True
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Character not found",
    )


async def add_character_to_location_service(character_id: str, location_id: str):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not character_db or not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character or Location not found",
        )
    try:
        existing_entry = await db["character_location"].find_one(
            {"character_id": character_id, "location_id": location_id}
        )
        if existing_entry:
            return "Character already added to location"

        character_location_data = CharacterLocationModel(
            character_id=character_id,
            location_id=location_id,
            characteristics={},
            created_by=character_db["created_by"],
            updated_by=character_db["updated_by"],
        )
        await db["character_location"].insert_one(character_location_data.dict())

    except Exception as e:
        print(f"Error in add character to location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not added to location",
        )

    return "character added to location"


async def add_or_edit_character_location(
        character_id: str,
        location_id: str,
        game_id: str,
        characteristics: dict,
        user_id: str,
        state_game: str = None,
):
    existing_entry = await db["character_location"].find_one(
        {"character_id": character_id, "location_id": location_id}
    )

    if not state_game:
        state_game_id = await get_state_game_by_game_id(game_id)
    else:
        state_game_id = await get_state_game_by_id(state_game)

    element_state_db = await db["state_glic"].find_one(
        {"element_id": character_id, "state": state_game_id["_id"]}
    )

    element_state_db["data"]["characteristics"] = characteristics

    await db["state_glic"].update_one(
        {"_id": element_state_db["_id"]},
        {"$set": {"data": element_state_db["data"]}},
    )

    # if existing_entry:
    #     await db["character_location"].update_one(
    #         {"_id": existing_entry["_id"]},
    #         {
    #             "$set": {
    #                 "characteristics": characteristics,
    #                 "updated_by": user_id,
    #                 "updated_at": datetime.utcnow(),
    #             }
    #         },
    #     )
    return "Character location updated successfully"
    # else:
    #     character_location_data = CharacterLocationModel(
    #         character_id=character_id,
    #         location_id=location_id,
    #         characteristics=characteristics,
    #         created_by=user_id,
    #         updated_by=user_id,
    #     )
    #     await db["character_location"].insert_one(character_location_data.dict())
    #     return "Character location added successfully"


async def remove_character_location(character_id: str, location_id: str):
    existing_entry = await db["character_location"].find_one(
        {"character_id": character_id, "location_id": location_id}
    )

    if existing_entry:
        await db["character_location"].delete_one({"_id": existing_entry["_id"]})
        return "Character location removed successfully"
    return "Character location not found"


async def new_interaction_character_service(
        location_id: str,
        game_id: str,
        character_id: str,
        conversation_type: str,
        conversation: list[ConversationsCharacter],
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
    if options_dialog:
        options_dialog = options_dialog

    if conversation:
        conversation = [conv.dict() for conv in conversation]

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


class SchemaResponseOpenAnswer(BaseModel):
    response_criteria: str = Field(description="Response answer")
    audio: str = Field(description="Audio")
    reason: str = Field(description="Reason")


async def answer_open_question_service(
        location_id: str,
        character_id: str,
        prompt_user_answer: str,
        user_id: str,
        state_game: str = None,
):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})

    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    if not state_game:
        state_game = await get_state_game_by_game_id(character_db["game_id"])
        state_game = state_game["_id"]

    state_element_db = await db["state_glic"].find_one(
        {"element_id": character_id, "state": state_game}
    )

    if not state_element_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="State element not found",
        )

    try:
        criteria = {}
        # for location in state_element_db['data']['interaction']:
        #     if location["location_id"] == location_id:
        #         all_dialogs = []
        #         for question in location["options_dialog"]["prompt_user_question"]:
        #             all_dialogs.append(question["dialog"])
        #
        #         criteria["question"] = [question["dialog"] for question in
        #                                 location["options_dialog"]["prompt_user_question"]]
        #         options_answer = []
        #         for criteria_db in location["options_dialog"]["options"]:
        #             if criteria_db["prompt_user_guideline"] and criteria_db["prompt_user_answer"]:
        #                 options_answer.append(
        #                     {
        #                         "criteria_evaluated": criteria_db["prompt_user_guideline"],
        #                         "response_criteria": criteria_db["prompt_user_answer"]["dialog"],
        #                         "audio": criteria_db["prompt_user_answer"]["audio"],
        #                     }
        #                 )
        #
        #         criteria["options_answer"] = options_answer
        # response = await openai_generator.generate_gpt(
        #     content_prompt=[
        #         {
        #             "role": "system",
        #             "content": f"Eres un evaluador de respuestas de preguntas abiertas, "
        #                        f"por favor evalúa la respuesta que da el usuario, respecto a un pregunta teniendo encuenta"
        #                        f" la un criteria a evaluar y dando la respuesta de las opciones que tienes en criterios y respuestas,"
        #                        f"no te puedes salir de las opciones que tienes en criterios y respuestas",
        #         },
        #         {
        #             "role": "system",
        #             "content": f"pregunta: {criteria['question']}"
        #                        f"criterios a evaluar y respuestas: {criteria['options_answer']}",
        #         },
        #         {
        #             "role": "user",
        #             "content": [
        #                 {
        #                     "type": "text",
        #                     "text": f"respuesta del usuario: {prompt_user_answer}",
        #                 },
        #             ],
        #         },
        #     ],
        #     model="gpt-4o-mini-2024-07-18",
        #     max_tokens=4096,
        #     response_format=SchemaResponseOpenAnswer,
        #     user_id=user_id,
        #     type_generation="validate_open_answer",
        # )

        for location in state_element_db['data']['interaction']:
            if location["location_id"] == location_id:
                all_dialogs = []
                for question in location["options_dialog"]["prompt_user_question"]:
                    all_dialogs.append(question["dialog"])

                criteria["question"] = [question["dialog"] for question in
                                        location["options_dialog"]["prompt_user_question"]]
                options_answer = []
                for criteria_db in location["options_dialog"]["options"]:
                    if criteria_db["prompt_user_guideline"] and criteria_db["prompt_user_answer"]:
                        options_answer.append(
                            {
                                "criteria_evaluated": criteria_db["prompt_user_guideline"],
                                "response_criteria": criteria_db["prompt_user_answer"]["dialog"],
                                "audio": criteria_db["prompt_user_answer"]["audio"],
                            }
                        )

                criteria["options_answer"] = options_answer

                # Obtener el primer elemento del array
                first_answer = options_answer[0] if options_answer else None

                return {
                    "detail": {
                        "response_answer": first_answer["response_criteria"] if first_answer else None,
                        "audio": first_answer["audio"] if first_answer else None,
                    }
                }
    except Exception as e:
        print(f"Error in answer open question service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not generated",
        )


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
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND, detail="State element not found"
                        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Character not deactivated."
        )


class SchemaResponseOpenTalk(BaseModel):
    response_criteria: str = Field(description="Response answer")
    reason: str = Field(description="Reason")


class SchemaResponseOpenTalkArray(BaseModel):
    responses: list[SchemaResponseOpenTalk] = Field(description="Responses")


async def answer_open_talk_service(
        location_id: str,
        character_id: str,
        prompt_user_answer: str,
        user_id: str,
        state_game: str = None,
        id_conversation: str = None,
):
    character_db = await db["character"].find_one({"_id": ObjectId(character_id)})

    if not character_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    if not state_game:
        state_game = await get_state_game_by_game_id(character_db["game_id"])
        state_game = state_game["_id"]

    state_element_db = await db["state_glic"].find_one(
        {"element_id": character_id, "state": state_game}
    )

    if not state_element_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="State element not found",
        )

    try:
        if not id_conversation:
            response_user = await db["response_user"].insert_one({
                "user_id": user_id,
                "character_id": character_id,
                "location_id": location_id,
                "state_game": state_game,
                "conversation": [
                    {
                        "user_question": prompt_user_answer,
                        "ai_response": None
                    }
                ],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            response_user = await db["response_user"].find_one({"_id": response_user.inserted_id})

        else:
            response_user = await db["response_user"].find_one({"_id": ObjectId(id_conversation)})
            if not response_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Response user not found",
                )

            conversation = response_user.get("conversation", [])
            conversation.append({
                "id_conversation": id_conversation,
                "user_question": prompt_user_answer,
                "ai_response": None
            })

            await db["response_user"].update_one(
                {"_id": response_user["_id"]},
                {"$set": {"conversation": conversation, "updated_at": datetime.utcnow()}}
            )


        response_user = await db["response_user"].find_one({"_id": response_user["_id"]})
        conversation_context = response_user.get("conversation", [])

        conversation_guideline = None

        count_interactions = 0

        criteria = {}
        for location in state_element_db['data']['interaction']:
            if location["location_id"] == location_id:
                all_dialogs = []
                conversation_guideline = location["options_dialog"]["prompt_user_guideline"]
                count_interactions = location["options_dialog"]["num_interaction"]
                for question in location["options_dialog"]["prompt_user_question"]:
                    all_dialogs.append(question["dialog"])

                criteria["question"] = [question["dialog"] for question in
                                        location["options_dialog"]["prompt_user_question"]]
                options_answer = []
                for criteria_db in location["options_dialog"]["options"]:
                    if criteria_db["prompt_user_guideline"] and criteria_db["prompt_user_answer"]:
                        options_answer.append(
                            {
                                "criteria_evaluated": criteria_db["prompt_user_guideline"],
                                "response_criteria": criteria_db["prompt_user_answer"],
                                "audio": None,
                            }
                        )

                criteria["options_answer"] = options_answer

        if not conversation_guideline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation guideline not found",
            )

        if len(conversation_context) <= count_interactions - 1:
            ai_response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f"Eres un evaluador de conversaciones. Responde únicamente basándote en el rol de la IA: "
                                   f"{conversation_guideline}. No tomes en cuenta criterios ni preguntas en esta etapa el array de respuestas solo debe tener 1 respuesta.",
                    },
                    {
                        "role": "system",
                        "content": f"Contexto de la conversación: {conversation_context},"
                                   f" turno de conversación actual: {len(conversation_context)},"
                                   f" cantidad de interacciones máximas: {count_interactions}",
                    },
                    {
                        "role": "user",
                        "content": prompt_user_answer
                    }
                ],
                model="gpt-4o-mini-2024-07-18",
                max_tokens=4096,
                response_format=SchemaResponseOpenTalkArray,
                user_id=user_id,
                type_generation="validate_open_talk",
            )
        elif len(conversation_context) == count_interactions:
            ai_response = await openai_generator.generate_gpt(
                content_prompt=[
                    {
                        "role": "system",
                        "content": f"Eres un evaluador de conversaciones. En esta última interacción, evalúa la respuesta del usuario "
                                   f"basándote en los criterios de evaluación y el guion de respuesta proporcionados. "
                                   f"Por ejemplo, si el criterio evaluado es 'Conciencia ambiental' y la respuesta definida es 'Es importante cuidar el medio ambiente', "
                                   f"genera una respuesta como 'Debemos cuidar el planeta' como la primera respuesta, mientras que la segunda será la respuesta definida. "
                                   f"La primera respuesta debe ser generada por la IA, basada en el contexto de la conversación y el guion, "
                                   f"y debe ser coherente con el rol de la IA, la opción de criterio seleccionada y "
                                   f"esta respuesta no debe terminar en una pregunta, generar dudas, cambios de decisión ni causar confusión con la opción seleccionada. "
                                   f"Tampoco debe coincidir con ninguna de las opciones de criterio. "
                                   f"Selecciona uno de los criterios a evaluar y genera una respuesta dirigida a esa opción como la segunda respuesta. "
                                   f"El array de respuestas debe contener exactamente 2 respuestas, las primera respuesta no debe ser la misma que la segunda o coincidir con ninguna de las opciones de criterio. ",
                    },
                    {
                        "role": "system",
                        "content":
                            f"criterios a evaluar y respuestas: {criteria['options_answer']},"
                            f"rol de la IA: {conversation_guideline}",
                    },
                    {
                        "role": "system",
                        "content": f"Contexto de la conversación: {conversation_context},"
                                   f" turno de conversación actual: {len(conversation_context)},"
                                   f" cantidad de interacciones máximas: {count_interactions}",
                    },
                    {
                        "role": "user",
                        "content": prompt_user_answer
                    }
                ],
                model="gpt-4o-mini-2024-07-18",
                max_tokens=4096,
                response_format=SchemaResponseOpenTalkArray,
                user_id=user_id,
                type_generation="validate_open_talk",
            )
        else:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation finished",
            )

        await db["response_user"].update_one(
                {"_id": response_user["_id"]},
                {"$set": {"conversation.$[elem].ai_response": [{"response_answer": response_ai.response_criteria} for
                                                               response_ai in ai_response.responses]}},
                array_filters=[{"elem.user_question": prompt_user_answer}]
            )


        return {
            "detail": {
                "response_answer": ai_response.responses[0].response_criteria,
                "audio": None,
                "is_final": len(conversation_context) == count_interactions,
                "conversation_id": str(response_user["_id"]),
                "conversation": [{"response_answer": response_ai.response_criteria, "audio": None}
                                 for response_ai in
                                 ai_response.responses],
            }
        }

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in answer open talk service: {str(e)}")
        raise HTTPException(
            status_code=e.status_code if hasattr(e, 'status_code') else status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail) if hasattr(e, 'detail') else "Answer not generated",
        )
