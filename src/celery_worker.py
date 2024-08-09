import json
import os
import sys
from uuid import uuid4

import requests
from bson import ObjectId

from celery import Celery

from character.schemas import SchemaCreateCharacter
from core import db
from gpt_ai.utils import generate_image_dalle, generate_gpt4o

from location.schemas import SchemaCreateLocation

from scene.schemas import SchemaCreateScene

from object.schemas import SchemaCreateObject

from script.schemas import SchemaPartialUpdateScript
from script.utils import get_script_locations_chapter_v2
from utils import upload_image

import asyncio

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

URL_API = os.getenv("URL_API", "http://localhost:8000")


# @celery.task(name="customized_character")
# def customized_character(
#         game_id: str,
#         token: str,
#         character_id: str,
#         character_name: str,
#         character):

@celery.task(name="create_script_task")
def create_script_task(
        game_id: str,
        token: str,
        game_history: str,
        prompt_script: str,
        prompt_script_system: str,
        prompt_scene: str,
        prompt_scene_system: str,
        script_id: str,
        prompt_imagen_scene_cero: str,
        prompt_text_introduction_scene_cero: str,
        prompt_character_locations: str,
        prompt_character_locations_system: str,
        prompt_finish_chapter: str,
        prompt_text_finish_chapter: str,
        prompt_image_game_over: str,
):
    response_script = get_script_locations_chapter_v2(
        game_history,
        "1",
        prompt_script,
        prompt_script_system,
        prompt_scene,
        prompt_scene_system,
        prompt_imagen_scene_cero,
        prompt_text_introduction_scene_cero,
        prompt_character_locations,
        prompt_character_locations_system,
        prompt_finish_chapter,
        prompt_text_finish_chapter,
        prompt_image_game_over,
    )

    response_all = f"ai generated - {game_id} "

    # create objects

    objects_created = []
    characters_created = []
    locations_created = []

    object_ = response_script["characters_locations"]["objects"]
    if object_:
        try:
            for i in object_:
                print("object " + str(i))
                object_generate = SchemaCreateObject(
                    name=i["name"],
                    description=i["description"],
                    function=i["function"],
                    game_id=game_id,
                    script_id=script_id,
                    image="",
                )

                object__ = requests.post(
                    f"{URL_API}/v1/api/object/",
                    json=object_generate.dict(),
                    headers={"Authorization": "Bearer " + token},
                )

                object_json = object__.json()

                print("object_json " + str(object_json))

                objects_created.append(object_json)

                requests.get(
                    f"{URL_API}/v1/api/object/generate-image/{object_json['_id']}",
                    headers={"Authorization": "Bearer " + token},
                )

            response_all += " Objects created "

        except Exception as e:
            e_type, e_object, e_traceback = sys.exc_info()

            e_filename = os.path.split(e_traceback.tb_frame.f_code.co_filename)[1]

            e_message = str(e)

            e_line_number = e_traceback.tb_lineno

            script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
                status_object=2
            )
            response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                      json=script_generate.dict(),
                                      headers={"Authorization": "Bearer " + token})

            print("res   " + str(response.json()))

            response_all += " Object not created " + str(e)

            print("File " + str(e_filename))
            print("Message " + str(e_message))
            print("Line " + str(e_line_number))
            print("Object " + str(e_object))
            print("Type " + str(e_type))
            print("Traceback " + str(e_traceback))

    print("objects created")

    # Create the locations
    branch_location = True
    locations_ = response_script["characters_locations"]["locations"]
    try:
        for i in locations_:
            print("location " + str(i))

            location_generate = SchemaCreateLocation(
                title=i["name"],
                description=i["description_indoor"],
                image="",
                game_id=game_id,
                zoom=0.0,
            )

            locations__ = requests.post(
                f"{URL_API}/v1/api/location/",
                json=location_generate.dict(),
                headers={"Authorization": "Bearer " + token},
            )

            location_json = locations__.json()

            print("location_json " + str(location_json))

            locations_created.append(location_json)

        response_all += " Location created "

    except Exception as e:
        branch_location = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(status_location=2)
        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        print("res   " + str(response.json()))

        response_all += " Location not created " + str(e)

        print(e)

    if branch_location:
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(status_location=1)
        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}/",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        print("res   " + str(response.json()))

    print("location created")

    # Create the characters
    branch_character = True
    character_ = response_script["characters_locations"]["characters"]

    try:
        for i in character_:
            if "text_idle" in i:
                for j in i["text_idle"]["dialogues"]:
                    for k in locations_:
                        if str(j["location_id"]) == str(k["id"]):
                            for l in locations_created:
                                if l["title"] == k["name"]:
                                    j["location_id"] = l["_id"]

            print("character " + str(i))

            character_generate = SchemaCreateCharacter(
                name=i["name"],
                gender=i["gender"] if "gender" in i and i["gender"] in ["man", "woman"] else "animal",
                type=i["type"],
                description=i["description"],
                game_id=game_id,
                attempts=3,
                extra_data=i["extra_data"] if "extra_data" in i else {},
                text_idle=i["text_idle"] if "text_idle" in i else [],

            )

            character_response = requests.post(
                f"{URL_API}/v1/api/characters/",
                json=character_generate.dict(),
                headers={"Authorization": "Bearer " + token},
            )

            # if character_response.status_code == 200:
            #     print("type " + i["type"])
            #     if i["type"] == "leading role":
            #         print("type check " + i["type"])
            #         for j in ["long", "short"]:
            #             print("type " + j)
            #             weapons_ = SchemaCreateForType(
            #                 type=j,
            #                 character_id=character_response.json()["id"],
            #                 script_id=script_id,
            #                 game_id=game_id,
            #             )
            #
            #             requests.post(
            #                 f"{URL_API}/v1/api/weapon/",
            #                 json=weapons_.dict(),
            #                 headers={"Authorization": "Bearer " + token},
            #             )

            character_json = character_response.json()

            print("character_json " + str(character_json))

            characters_created.append(character_json)

        response_all += " Character created "

    except Exception as e:

        response_all += " Character not created " + str(e)

        e_type, e_object, e_traceback = sys.exc_info()

        e_filename = os.path.split(e_traceback.tb_frame.f_code.co_filename)[1]

        e_message = str(e)

        e_line_number = e_traceback.tb_lineno

        branch_character = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(status_character=2)
        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        print("res   " + str(response.json()))

        print("e_type " + str(e_type))
        print("e_object " + str(e_object))
        print("e_traceback " + str(e_traceback))
        print("e_filename " + str(e_filename))
        print("e_message " + str(e_message))
        print("e_line_number " + str(e_line_number))

    if branch_character:
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(status_character=1)
        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        print("res   " + str(response.json()))

    print("character created")

    # Create the scenes
    scenes_ = response_script["scenes"]

    branch_scene = True
    try:
        count = 0
        for i in scenes_:
            location_scene = ""
            for j in locations_:
                if str(i["id_location"]) == str(j["id"]):
                    for k in locations_created:
                        if k["title"] == j["name"]:
                            location_scene = k["_id"]
            characters_scene = []
            for j in i["characters"]:
                for k in character_:
                    if str(j["id"]) == str(k["id"]):
                        for l in characters_created:
                            if l["name"] == k["name"]:
                                characters_scene.append(l["_id"])

            for dialogues_start in i["start_dialogues"]:
                for k in character_:
                    # print("dialogues_start ", dialogues_start["id_character"])
                    # print("k ", k["id"])

                    if str(dialogues_start["id_character"]) == str(k["id"]):

                        for l in characters_created:
                            if l["name"] == k["name"]:
                                dialogues_start["id_character"] = l["_id"]

            for dialogues_end in i["end_dialogues"]:
                for k in character_:

                    if str(dialogues_end["id_character"]) == str(k["id"]):
                        for l in characters_created:
                            if l["name"] == k["name"]:
                                dialogues_end["id_character"] = l["_id"]

            if "enemy_id" in i and i["enemy_id"] != "":
                for character_enemy in character_:

                    if (
                            str(i["enemy_id"]) == str(character_enemy["id"])
                            and i["enemy_id"] != ""
                            and "enemy_id" in i.keys()
                    ):
                        for k in characters_created:
                            if k["name"] == character_enemy["name"]:
                                i["enemy_id"] = k["_id"]

            object_id = ""

            if "object_id" in i:
                for k in object_:
                    if str(i["object_id"]) == str(k["id"]):
                        for l in objects_created:
                            if l["name"] == k["name"]:
                                object_id = l["_id"]
            # print("scene_generate " + str(count) + str(i))

            if "questions" in i:
                if i["questions"] == {
                    'options': [],
                    'correct_option': None,
                    'feedback': '',
                    'feedback_incorrect': '',
                }:
                    i["questions"] = None

            if "delivery_location_id" in i:
                if i["delivery_location_id"] == "":
                    location_delivery = None
                else:
                    for j in locations_:
                        if str(j["id"]) == str(i["delivery_location_id"]):
                            for k in locations_created:
                                if k["title"] == j["name"]:
                                    location_delivery = k["_id"]
            else:
                location_delivery = None

            if "delivery_character_id" in i:
                if i["delivery_character_id"] == "":
                    character_delivery = None
                else:
                    for j in character_:
                        if str(j["id"]) == str(i["delivery_character_id"]):
                            for k in characters_created:
                                if k["name"] == j["name"]:
                                    character_delivery = k["_id"]
            else:
                character_delivery = None

            scene_generate = SchemaCreateScene(
                title=i["title"],
                description=i["description"],
                order=count,
                script_id=script_id,
                game_id=game_id,
                dynamic=i["dynamic"],
                content=i["content"],
                characters_id=characters_scene,
                location_id=location_scene,
                start_dialogues=i["start_dialogues"],
                end_dialogues=i["end_dialogues"],
                questions=i["questions"] if "questions" in i else None,
                reward=i["reward"],
                count_enemies=i["count_enemies"] if "count_enemies" in i else 0,
                enemy_id=i["enemy_id"] if "enemy_id" in i else "",
                is_subtractable=True if "is_subtractable" in i and i['is_subtractable'] else False,
                start_content=i["start_content"] if "start_content" in i.keys() else "",
                start_image=i["start_image"] if "start_image" in i.keys() else "",
                object_id=object_id,
                delivery_location_id=location_delivery,
                delivery_character_id=character_delivery,
                image_defeat=i["game_over_image"] if "game_over_image" in i.keys() else None,
            )
            count += 1

            print("scene_generate " + str(count))

            # TODO: fix aca
            requests.post(
                f"{URL_API}/v1/api/scene/",
                json=scene_generate.dict(),
                headers={"Authorization": "Bearer " + token},
            )

        response_all += " Scene created "

        # create_scene_service(db, scene_generate, user_id=current_user)
    except Exception as e:

        response_all += " Scene not created " + str(e)

        e_type, e_object, e_traceback = sys.exc_info()

        e_filename = os.path.split(e_traceback.tb_frame.f_code.co_filename)[1]

        e_message = str(e)

        e_line_number = e_traceback.tb_lineno

        print("e_type " + str(e_type))
        print("e_object " + str(e_object))
        print("e_traceback " + str(e_traceback))
        print("e_filename " + str(e_filename))
        print("e_message " + str(e_message))
        print("e_line_number " + str(e_line_number))
        branch_scene = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(status_scene=2)
        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        print("res   " + str(response.json()))

        print(e)
    script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(status_scene=1)
    if branch_scene:
        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        # print("res   " + str(response.json()))

        script_ = response_script["script"]

        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            title=script_["title"], description=script_["description"], status=1
        )

    try:

        response = requests.patch(
            f"{URL_API}/v1/api/script/{script_id}",
            json=script_generate.dict(),
            headers={"Authorization": "Bearer " + token},
        )

        response_all += " Script created "

        # print("res   " + str(response.json()))

    except Exception as e:

        response_all += " Script not created " + str(e)

        raise print(e)

    print("script created")

    return response_all


async def async_create_cover_image_task(game_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            return False

        if game_db.get('image', None):
            return True

        first_location = None
        first_character = None
        if game_db.get('locations_id'):
            first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if game_db.get('characters_id'):
            first_character = await db['character'].find_one({'_id': ObjectId(game_db['characters_id'][0])})
        if not first_location or not first_character:
            return False
        # Generate the prompt for the cover image
        prompt = (f"Generate a image in 3D animation style of extraordinary quality for the game "
                  f"'{game_db['title']}' featuring the character {first_character['prompt_user']}'"
                  f" in the location '{first_location['prompt_user']}'. The scene should depict an "
                  f"action-packed moment that captures the essence of the game.")
        image = generate_image_dalle(prompt=prompt,
                                     quality="hd",
                                     size="1024x1792")

        image = upload_image(
            url_image=image,
            file_name=f"covers/{uuid4()}.jpg",
            size=(512, 896)
        )

        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'image': image}})
        return True

    except Exception as e:
        print(f"Error Cover Image: {str(e)}")
        return False


@celery.task(name="create_cover_image_task")
def create_cover_image_task(game_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_create_cover_image_task(game_id))


async def async_generate_context_init_game_task(game_id: str):
    try:

        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            return False

        if game_db.get('history'):
            return True

        game_name = game_db.get('title')
        if not game_name:
            return False

        if not game_db.get('locations_id'):
            return False

        first_location = await db['location'].find_one({'_id': ObjectId(game_db['locations_id'][0])})
        if not first_location:
            return False

        location_description = first_location.get('prompt_user')
        if not location_description:
            return False

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator."},
            {"role": "user",
             "content": f"Generate the story init for the game '{game_name}' set in the location "
                        f"'{first_location['title']}'. The location is described as: {location_description}. "
                        f"Respond only with the text of the story in JSON format: {{'story': '<story_text>'}}"}
        ]
        story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story init",
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        story = json.loads(story)
        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'history': story['story']}})

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


@celery.task(name="generate_context_init_game_task")
def generate_context_init_game_task(game_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_context_init_game_task(game_id))


async def async_generate_context_new_location(game_id: str, location_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            return False

        game_name = game_db.get('title')
        if not game_name:
            return False

        game_story = game_db.get('history', '')

        location_db = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_db:
            return False

        location_description = location_db.get('prompt_user')
        if not location_description:
            return False

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator."},
            {"role": "user",
             "content": f"Continue the story for the game '{game_name}' set in the new location '{location_db['title']}'. "
                        f"The current story is: {game_story}. The location is described as: {location_description}."
                        f"Respond only with the text of the story in JSON format: {{'story': '<story_text>'}}"}
        ]
        story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story location",
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        story = json.loads(story)
        await db['location'].update_one({'_id': ObjectId(location_id)}, {'$set': {'history': story['story']}})

        location_db = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_db:
            return False

        new_location_story = location_db.get('history')
        if not new_location_story:
            return False

        content_prompt = [
            {"role": "system", "content": "You are a creative story generator,"},
            {"role": "user",
             "content": f"Continue the history for the game '{game_name}' using the new location story: {new_location_story}. "
                        f"The current game story is: {game_story}."
                        f"should be a maximum of 1000 words. "
                        f"Respond only with the text of the story in JSON format: {{'story': '<story_text>'}}"}
        ]
        new_story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="story continuation",
            max_tokens=1000,
            model="gpt-4o-mini"
        )

        new_story = json.loads(new_story)

        await db['game'].update_one({'_id': ObjectId(game_id)}, {'$set': {'history': new_story['story']}})

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


@celery.task(name="generate_context_new_location")
def generate_context_new_location(game_id: str, location_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_context_new_location(game_id, location_id))


async def async_generate_context_new_character(game_id: str, character_id: str, location_id: str):
    try:
        game_db = await db['game'].find_one({'_id': ObjectId(game_id)})
        if not game_db:
            print("game not found")
            return False

        game_name = game_db.get('title')
        if not game_name:
            print("game name not found")
            return False

        game_story = game_db.get('history', '')

        character_db = await db['character'].find_one({'_id': ObjectId(character_id)})
        if not character_db:
            print("character not found")
            return False

        character_description = character_db.get('prompt_user')
        if not character_description:
            print("character description not found")
            return False

        location_description = await db['location'].find_one({'_id': ObjectId(location_id)})
        if not location_description:
            print("location not found")
            return False

        location_history = location_description.get('history', '')

        if not location_history:
            location_history = location_description.get('prompt_user', '')

        content_prompt = [
            {"role": "system", "content": "You are a creative dialogue generator."},
            {"role": "user",
             "content": f"Generate a first-person text about the role of the character '{character_db['name']}' in the game '{game_name}'. "
                        f"The current story is: {game_story}. The character is described as: {character_description}. "
                        f"The location's current story is: {location_history}. "
                        f"Respond only with the text about the character's role in JSON format: {{'role': '<role_text>'}}"}
        ]
        story = generate_gpt4o(
            content_prompt=content_prompt,
            type_text="character dialogue",
            max_tokens=2000,
            model="gpt-4o-mini"
        )

        story = json.loads(story)
        await db['character'].update_one({'_id': ObjectId(character_id)}, {'$set': {'presentation': story['dialogue']}})

        return True

    except Exception as e:
        print(f"Error generating story: {str(e)}")
        return False


@celery.task(name="generate_context_new_character")
def generate_context_new_character(game_id: str, character_id: str, location_id: str):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(async_generate_context_new_character(game_id, character_id, location_id))
