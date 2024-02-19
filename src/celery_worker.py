import os
import sys

import requests
from celery import Celery

from character.schemas import SchemaCreateCharacter

from location.schemas import SchemaCreateLocation

from scene.schemas import SchemaCreateScene

from object.schemas import SchemaCreateObject

from weapon.schemas import SchemaCreateForType

from script.schemas import SchemaPartialUpdateScript
from script.utils import get_script_locations_chapter_v2

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

# URL_API = "https://backend-dev.qwestar.ai"
URL_API = "http://192.168.1.45"


@celery.task(name="create_script_task")
def create_script_task(token: str,
                       game_history: str,
                       prompt_script: str,
                       prompt_scene: str,
                       game_id: str,
                       script_id: str,
                       current_user: str):
    # script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
    #     status=1
    # )

    response_script = get_script_locations_chapter_v2(game_history,
                                                      "1",
                                                      prompt_script,
                                                      prompt_scene)

    # create objects

    print("create objects")

    print(response_script["characters_locations"].keys())

    object_ = response_script["characters_locations"]["objects"]
    if object_:
        for i in object_:
            object_generate = SchemaCreateObject(
                name=i["name"],
                description=i["description"],
                function=i["function"],
                game_id=game_id,
                script_id=script_id,
                image="")

            object_ = requests.post(f"{URL_API}/v1/api/object/",
                                    json=object_generate.dict(),
                                    headers={"Authorization": "Bearer " + token})

            object_json = object_.json()

            image_generate = requests.get(f"{URL_API}/v1/api/object/generate-image/{object_json['id']}",
                                          headers={"Authorization": "Bearer " + token})

    print("objects created")





    # Create the locations
    branch_location = True
    locations_ = response_script["characters_locations"]["locations"]
    try:
        for i in locations_:
            location_generate = SchemaCreateLocation(
                title=i["name"],
                description=i["description"],
                image="",
                game_id=game_id,
                zoom=0.0)

            requests.post(f"{URL_API}/v1/api/location/",
                          json=location_generate.dict(),
                          headers={"Authorization": "Bearer " + token})

    except Exception as e:
        branch_location = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_location=2
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

        print(e)

    if branch_location:
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_location=1
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}/",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

    print("location created")





    # Create the characters
    branch_character = True
    character_ = response_script["characters_locations"]["characters"]

    print("character_ " + str(character_) + " " + str(len(character_)))
    try:
        for i in character_:

            character_generate = SchemaCreateCharacter(
                name=i["name"],
                genre=i["genre"],
                type=i["type"],
                description=i["description"],
                game_id=game_id,
                attempts=3)

            character_response = requests.post(f"{URL_API}/v1/api/characters/",
                                       json=character_generate.dict(),
                                       headers={"Authorization": "Bearer " + token})
            print("type " + i["type"])
            if i["type"] == "leading role":
                print("type check " + i["type"])
                for j in ["long", "short"]:
                    print("type " + j)
                    weapons_ = SchemaCreateForType(
                        type=j,
                        character_id=character_response.json()["id"],
                        script_id=script_id,
                        game_id=game_id
                    )

                    weapon_ = requests.post(f"{URL_API}/v1/api/weapon/",
                                            json=weapons_.dict(),
                                            headers={"Authorization": "Bearer " + token})

                    print("weapon_ " + str(weapon_.status_code))

    except Exception as e:

        e_type, e_object, e_traceback = sys.exc_info()

        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]

        e_message = str(e)

        e_line_number = e_traceback.tb_lineno

        print("e_type " + str(e_type))
        print("e_object " + str(e_object))
        print("e_traceback " + str(e_traceback))
        print("e_filename " + str(e_filename))
        print("e_message " + str(e_message))
        print("e_line_number " + str(e_line_number))

        branch_character = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_character=2
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

        print(e)

    if branch_character:
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_character=1
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

    print("character created")





    # Create the scenes
    scenes_ = response_script["scenes"]

    location_scene = ""
    branch_scene = True
    try:
        # print("scenes_ " + str(scenes_) + " " + str(len(scenes_)))
        count = 1
        for i in scenes_:
            # print("i " + str(i) + " " + str(len(scenes_)) + " " + str(count))
            for j in locations_:
                # print("i " + str(i["id_location"]) + " j " + str(j["id"]))
                if str(i["id_location"]) == str(j["id"]):
                    # print("i " + str(i["id_location"]) + " j " + str(j["id"]) + " " + str(j["name"]))
                    location_scene = (requests.get(f"{URL_API}/v1/api/location/by-field/?field=title&value={j['name']}",
                                     headers={"Authorization": "Bearer " + token})).json()
                    print("location_scene " , location_scene)
                    location_scene = location_scene["id"]

            characters_scene = []
            print("characters_scene " , i["characters"])
            for j in i["characters"]:
                print("j " , j)
                for k in character_:
                    print("k ", k)
                    if str(j["id"]) == str(k["id"]):
                        print("k ", k)
                        characters_scene.append(
                            requests.get(
                                f"{URL_API}/v1/api/characters/by-field/?field=name&value={k['name']}",
                                headers={"Authorization": "Bearer " + token}).json()["id"])

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
                questions=i["questions"],
                reward=i["reward"],
                count_enemies=i["count_enemies"],
                enemy_id=i["enemy_id"],
                is_subtractable=i["is_subtractable"]
            )
            count += 1

            print("scene_generate " + str(count))

            requests.post(f"{URL_API}/v1/api/scene/",
                          json=scene_generate.dict(),
                          headers={"Authorization": "Bearer " + token})

            # create_scene_service(db, scene_generate, user_id=current_user)
    except Exception as e:

        e_type, e_object, e_traceback = sys.exc_info()

        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]

        e_message = str(e)

        e_line_number = e_traceback.tb_lineno

        print("e_type " + str(e_type))
        print("e_object " + str(e_object))
        print("e_traceback " + str(e_traceback))
        print("e_filename " + str(e_filename))
        print("e_message " + str(e_message))
        print("e_line_number " + str(e_line_number))
        branch_scene = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_scene=2
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

        print(e)
    script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
        status_scene=1
    )
    if branch_scene:
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

        script_ = response_script["script"]

        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            title=script_["title"],
            description=script_["description"],
            status=1
        )


    try:

        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))


    except Exception as e:
        raise print(e)

    print("script created")
    #
    print("all created")
    return True

#
# @celery.task(name="create_task")
# def create_task(a, b, c):
#     time.sleep(a)
#     return b + c
