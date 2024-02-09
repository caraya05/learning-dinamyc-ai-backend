import os
import requests
from celery import Celery

from character.schemas import SchemaCreateCharacter
from location.schemas import SchemaCreateLocation
from scene.schemas import SchemaCreateScene
from script.schemas import SchemaPartialUpdateScript
from script.utils import get_script_locations_chapter_v2

celery = Celery(__name__)
celery.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

URL_API = "https://backend-dev.qwestar.ai"


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

    # Create the locations

    locations_ = response_script["characters_locations"]["locations"]

    for i in locations_:
        try:
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
            print(e)

    print("location created")

    # Create the characters

    character_ = response_script["characters_locations"]["characters"]

    for i in character_:
        try:
            character_generate = SchemaCreateCharacter(
                name=i["name"],
                genre=i["genre"],
                type=i["type"],
                description=i["description"],
                game_id=game_id,
                attempts=3)

            requests.post(f"{URL_API}/v1/api/characters/",
                          json=character_generate.dict(),
                          headers={"Authorization": "Bearer " + token})


        except Exception as e:
            print(e)
    print("character created")
    #
    # Create the scenes
    scenes_ = response_script["scenes"]

    location_scene = ""
    try:
        count = 1
        for i in scenes_:
            for j in locations_:
                # print("location", j["id"])
                # print("location 2", i["id_location"])
                if str(i["id_location"]) == str(j["id"]):
                    # print("location", j)
                    location_scene = \
                        requests.get(f"{URL_API}/v1/api/location/by-field/?field=title&value={j['name']}",
                                     headers={"Authorization": "Bearer " + token}).json()["id"]
            # print("location_scene", location_scene)
            # break
            # location_scene = get_location_by_field(db, "title", i["location"])

            characters_scene = []
            for j in i["characters"]:
                for k in character_:
                    # print("character", k["id"])
                    # print("character 2", j["id"])
                    if str(j["id"]) == str(k["id"]):
                        # print("character", k)
                        characters_scene.append(
                            requests.get(
                                f"{URL_API}/v1/api/characters/by-field/?field=name&value={k['name']}",
                                headers={"Authorization": "Bearer " + token}).json()["id"])
                # print("characters_scene", characters_scene)
                # break
                # characters_scene.append(get_character_by_field(db, "name", j["name"]).id)

            scene_generate = SchemaCreateScene(
                title=i["title"],
                description=i["description"],
                order=count,
                script_id=script_id,
                dynamic=i["dynamic"],
                content=i["content"],
                dialogues=i["dialogues"],
                characters_id=characters_scene,
                location_id=location_scene,
            )
            count += 1

            print("scene_generate " + str(count))

            requests.post(f"{URL_API}/v1/api/scene/",
                          json=scene_generate.dict(),
                          headers={"Authorization": "Bearer " + token})

            # create_scene_service(db, scene_generate, user_id=current_user)
    except Exception as e:
        print(e)

    script_ = response_script["script"]

    script_generate: SchemaPartialUpdateScript = SchemaPartialUpdateScript(
        title=script_["title"],
        description=script_["description"],
        status=1
    )
    try:

        response = requests.patch(f"{URL_API}/v1/api/script/{script_id}/",
                                  json=script_generate.dict(),
                                  headers={"Authorization": "Bearer " + token})

        print("res   " + str(response.json()))

    except Exception as e:
        raise print(e)

    print("script created")
    #
    print("all created")
    return "all created"

#
# @celery.task(name="create_task")
# def create_task(a, b, c):
#     time.sleep(a)
#     return b + c
