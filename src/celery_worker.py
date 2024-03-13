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

URL_API = "https://backend-dev.qwestar.ai" # dev
# URL_API = "http://192.168.1.45" #casa
# URL_API = "http://10.215.58.18"  # wework usaquen
# URL_API = "http://192.168.100.169" #telefono


@celery.task(name="create_script_task")
def create_script_task(game_id: str,
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
                       prompt_image_game_over: str,):
    response_script = get_script_locations_chapter_v2(game_history,
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
                                                      prompt_image_game_over)

    response_all = f"ai generated - {game_id} "

    # create objects

    print("create objects")

    object_ = response_script["characters_locations"]["objects"]
    if object_:
        try:
            for i in object_:
                object_generate = SchemaCreateObject(
                    name=i["name"],
                    description=i["description"],
                    function=i["function"],
                    game_id=game_id,
                    script_id=script_id,
                    image="")

                object__ = requests.post(f"{URL_API}/v1/api/object/",
                                         json=object_generate.dict(),
                                         headers={"Authorization": "Bearer " + token})

                object_json = object__.json()

                requests.get(f"{URL_API}/v1/api/object/generate-image/{object_json['id']}",
                             headers={"Authorization": "Bearer " + token})

            response_all += " Objects created "

        except Exception as e:
            # script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            #                 status_object=2
            #             )
            # response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
            #                           json=script_generate.dict(),
            #                           headers={"Authorization": "Bearer " + token})

            # print("res   " + str(response.json()))

            response_all += " Object not created " + str(e)

            print(e)

    print("objects created")

    # Create the locations
    branch_location = True
    locations_ = response_script["characters_locations"]["locations"]
    try:
        for i in locations_:
            location_generate = SchemaCreateLocation(
                title=i["name"],
                description=i["description_indoor"],
                image="",
                game_id=game_id,
                zoom=0.0)

            requests.post(f"{URL_API}/v1/api/location/",
                          json=location_generate.dict(),
                          headers={"Authorization": "Bearer " + token})

        response_all += " Location created "

    except Exception as e:
        branch_location = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_location=2
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

        response_all += " Location not created " + str(e)

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

    try:
        for i in character_:
            if "text_idle" in i:
                for j in i["text_idle"]["dialogues"]:
                    for k in locations_:
                        if str(j["location_id"]) == str(k["id"]):
                            location_scene = (
                                requests.get(f"{URL_API}/v1/api/location/by-field/?field=title&value={k['name']}&game_id={game_id}",
                                             headers={"Authorization": "Bearer " + token})).json()
                            j["location_id"] = location_scene["id"]

            character_generate = SchemaCreateCharacter(
                name=i["name"],
                genre=i["genre"] if "genre" in i else None,
                type=i["type"],
                description=i["description"],
                game_id=game_id,
                attempts=3,
                extra_data=i["extra_data"] if "extra_data" in i else {},
                text_idle=i["text_idle"] if "text_idle" in i else [],
            )

            character_response = requests.post(f"{URL_API}/v1/api/characters/",
                                               json=character_generate.dict(),
                                               headers={"Authorization": "Bearer " + token})

            if character_response.status_code == 200:
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

                        requests.post(f"{URL_API}/v1/api/weapon/",
                                      json=weapons_.dict(),
                                      headers={"Authorization": "Bearer " + token})

        response_all += " Character created "

    except Exception as e:

        response_all += " Character not created " + str(e)

        e_type, e_object, e_traceback = sys.exc_info()

        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]

        e_message = str(e)

        e_line_number = e_traceback.tb_lineno

        branch_character = False
        script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
            status_character=2
        )
        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

        print("e_type " + str(e_type))
        print("e_object " + str(e_object))
        print("e_traceback " + str(e_traceback))
        print("e_filename " + str(e_filename))
        print("e_message " + str(e_message))
        print("e_line_number " + str(e_line_number))

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

    branch_scene = True
    try:
        # print("scenes_ " + str(scenes_) + " " + str(len(scenes_)))
        count = 0
        for i in scenes_:

            print("escene a crear " + str(i) + " " + str(scenes_) + " " + str(count))

            location_scene = ""
            # print("i " + str(i) + " " + str(len(scenes_)) + " " + str(count))
            for j in locations_:
                # print("i " + str(i["id_location"]) + " j " + str(j["id"]))
                if str(i["id_location"]) == str(j["id"]):
                    # print("i " + str(i["id_location"]) + " j " + str(j["id"]) + " " + str(j["name"]))
                    location_scene = (requests.get(f"{URL_API}/v1/api/location/by-field/?field=title&value={j['name']}&game_id={game_id}",
                                                   headers={"Authorization": "Bearer " + token})).json()
                    # print("location_scene ", location_scene)
                    location_scene = location_scene["id"]

            characters_scene = []
            # print("characters_scene ", i["characters"])
            for j in i["characters"]:
                # print("j ", j)
                for k in character_:
                    # print("k ", k)
                    if str(j["id"]) == str(k["id"]):
                        # print("k ", k)

                        character_by_field = requests.get(
                            f"{URL_API}/v1/api/characters/by-field/?field=name&value={k['name']}&game_id={game_id}",
                            headers={"Authorization": "Bearer " + token})

                        if character_by_field.status_code == 200:
                            characters_scene.append(character_by_field.json()["id"])

            for dialogues_start in i["start_dialogues"]:
                for k in character_:
                    print("dialogues_start ", dialogues_start["id_character"])
                    print("k ", k["id"])

                    if str(dialogues_start["id_character"]) == str(k["id"]):

                        character_by_field = requests.get(
                            f"{URL_API}/v1/api/characters/by-field/?field=name&value={k['name']}&game_id={game_id}",
                            headers={"Authorization": "Bearer " + token})

                        print("character_by_field ", character_by_field.json())

                        if character_by_field.status_code == 200:
                            dialogues_start["id_character"] = character_by_field.json()["id"]

            for dialogues_end in i["end_dialogues"]:
                for k in character_:
                    print("dialogues_end ", dialogues_end["id_character"])
                    print("k ", k["id"])
                    if str(dialogues_end["id_character"]) == str(k["id"]):
                        character_by_field = requests.get(
                            f"{URL_API}/v1/api/characters/by-field/?field=name&value={k['name']}&game_id={game_id}",
                            headers={"Authorization": "Bearer " + token})

                        print("character_by_field ", character_by_field.json())

                        if character_by_field.status_code == 200:
                            dialogues_end["id_character"] = character_by_field.json()["id"]

            # print("enemy_id " + str(i["enemy_id"]) + " " + str(i["enemy_id"]) != "" + " " + str("enemy_id" in i.keys()))

            if "enemy_id" in i and i["enemy_id"] != "":
                print("enemy_id " + str(i["enemy_id"]))

                for character_enemy in character_:

                    if str(i["enemy_id"]) == str(character_enemy["id"]) and i[
                        "enemy_id"] != "" and "enemy_id" in i.keys():
                        character_by_field = requests.get(
                            f"{URL_API}/v1/api/characters/by-field/?field=name&value={character_enemy['name']}&game_id={game_id}",
                            headers={"Authorization": "Bearer " + token})

                        if character_by_field.status_code == 200:
                            i["enemy_id"] = character_by_field.json()["id"]

            object_id = ""

            if "object_id" in i:
                for k in object_:
                    if str(i["object_id"]) == str(k["id"]):
                        object_id = requests.get(
                            f"{URL_API}/v1/api/object/by-field/?field=name&value={k['name']}&game_id={game_id}",
                            headers={"Authorization": "Bearer " + token}).json()["id"]

            print("scene_generate " + str(count) + str(i))

            if "questions" in i:
                if i["questions"] == {'options': [], 'correct_option': None, 'feedback': '',
                                      'feedback_incorrect': ''}:
                    i["questions"] = None

            if "delivery_location_id" in i:
                if i["delivery_location_id"] == "":
                    location_delivery = None
                else:
                    for j in locations_:
                        if str(j["id"]) == str(i["delivery_location_id"]):
                            location_delivery = requests.get(
                                f"{URL_API}/v1/api/location/by-field/?field=title&value={j['name']}&game_id={game_id}",
                                headers={"Authorization": "Bearer " + token}).json()["id"]
            else:
                location_delivery = None

            if "delivery_character_id" in i:
                if i["delivery_character_id"] == "":
                    character_delivery = None
                else:
                    for j in character_:
                        if str(j["id"]) == str(i["delivery_character_id"]):
                            character_delivery = requests.get(
                                f"{URL_API}/v1/api/characters/by-field/?field=name&value={j['name']}&game_id={game_id}",
                                headers={"Authorization": "Bearer " + token}).json()["id"]
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

            requests.post(f"{URL_API}/v1/api/scene/",
                          json=scene_generate.dict(),
                          headers={"Authorization": "Bearer " + token})

        response_all += " Scene created "

        # create_scene_service(db, scene_generate, user_id=current_user)
    except Exception as e:

        response_all += " Scene not created " + str(e)

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

        response_all += " Script created "

        print("res   " + str(response.json()))


    except Exception as e:

        response_all += " Script not created " + str(e)

        raise print(e)

    print("script created")

    return response_all
