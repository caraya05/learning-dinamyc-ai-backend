import json
import time
import random
from gpt_ai.utils import generate_gpt4_
from gpt_ai.utils import generate_image_dalle


# import jsonschema
# from jsonschema import validate

def get_script_locations_chapter_v2(history: str,
                                    num: str,
                                    prompt_script: str,
                                    prompt_script_system: str,
                                    prompt_scene: str,
                                    prompt_scene_system: str,
                                    prompt_imagen_scene_cero: str,
                                    prompt_text_introduction_scene_cero: str,
                                    prompt_character_locations: str,
                                    prompt_character_locations_system: str,
                                    prompt_before_battle: str,
                                    prompt_finish_chapter: str):

    star_time = time.time()

    schema_script = {
        "number": "int (number of the chapter)",
        "title": "string (title of the chapter)",
        "description": "string (full and detailed description of what happens in the chapter, including settings and characters.)",
        "scenes": [
            {
                "number": "int (number of the scene)",
                "description": "string (description of the scene)",
                "location": "string (location of the scene)"
            }
        ]

    }

    prompt_script = prompt_script.replace("x_history", history)

    content_prompt = [
        {
            "role": "system",
            "content": f"{prompt_script_system}"
            # f"en cada escena debe haber 2 personajes interactuando, "
                       f"responde el prompt con la siguiente estructura JSON: {schema_script}"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt_script
                }
            ]
        }
    ]

    response_script = generate_gpt4_(content_prompt=content_prompt,
                                     type_text="script",
                                     max_tokens=4096, )

    script_generated = json.loads(response_script)

    print("script_generated", time.time() - star_time)

    schema_characters_locations = {
        "locations": [
            {
                "id": "int (location id greater than 1)",
                "name": "string (name of the location)",
                "description_general": "string (general description of the location)",
                "description_indoor": "string (Generates a 5-line isometric view description of a wall, and a 5-line description of the floor adjacent to this stage wall, the space must be closed and covered).",
                "description_outdoor": "string (Generates a 5-line isometric view description of a wall, and a 5-line description of the floor next to this stage wall)."
            }
        ],
        "characters": [
            {
                "id": "int (character id greater than 1) ",
                "name": "string (name of the character)",
                "description": "string (description of the character in detail that can be used to generate an image)",
                "type": "string (the character types are: leading role, other, enemy, mini enemy, antagonist."
                        "There can only be one antagonist, one leading role, one enemy , mini enemy that are animals and many others. ) ",
                "genre": "string (genre of the character is man or woman )",
                "extra_data": {
                    "skin_color": "string or None (skin color of the character in format hexadecimal)",
                    "hair_color": "string or None (hair color of the character in format hexadecimal)",
                    "eye_color": "string or None (eye color of the character in format hexadecimal)",
                    "lips_color": "string or None (lips color of the character in format hexadecimal)",
                    "shoes_color": "string or None (shoes color of the character in format hexadecimal)",
                    "pants_color": "string or None (pants color of the character in format hexadecimal)",
                    "shirt_color": "string or None (shirt color of the character in format hexadecimal)",
                    "type_combing": "string or None (type of combing of the character)",
                },
                "text_idle": {
                    "dialogues": [
                        {
                            "location_id": "int (id of the location)",
                            "dialogue": "string (dialogue of the character in the location)"
                        }
                    ]
                },
            },
        ],
        "objects": [
            {
                "id": "int (id of the object)",
                "name": "string (name of the object)",
                "description": "string (description of the object in detail to generate an image of the object)",
                "function": "string (describes the functioning of the object in history)"
            }
        ],
        "summary": "string (summary of all characters and locations)"
    }

    content_prompt = [
        {
            "role": "system",
            "content": f"{prompt_character_locations_system}"
            # f"los personajes deben estar humanizados a excepción del mini enemy,"
            #            f"crea un personaje de cada tipo leading role, other, enemy, antagonist acorde a la historia."
            #            f" crea el mini enemy siempre y debe ser un zorro marron o un ave negra, "
            #            f"solo puede haber un antagonist, un leading role, un enemy y otros son personajes de relleno. "
            #            f"los escenarios deben ser cerrados y cubiertos, "
            #            f"garantiza que esten las locaciones, los personajes, los objetos, "
                       f" responde el prompt con la siguiente estructura JSON: {schema_characters_locations}"
        },
        {
            "role": "assistant",
            "content": f"historia: {history} \n"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"{prompt_character_locations}"
                    # "Dame una lista con nombre, y descripción física, género del protagonista, el antagonista, "
                    #     "y los personajes que aparecen en las primeras 4 escenas. Dale un nombre muy atractivo, crea siempre el mini enemy, "
                    #     "al juego y que genere recordación. también dame una lista con nombre y descripción de los "
                    #     "lugares donde se desarrollan las primeras 4 escenas. ademas dame un listado los objetos que aparecen en la historia."
                }
            ]
        }
    ]

    response_characters_locations = generate_gpt4_(content_prompt=content_prompt,
                                                   type_text="script",
                                                   max_tokens=4096, )

    characters_locations_generated = json.loads(response_characters_locations)

    # for i in range(len(characters_locations_generated["locations"])):
    #     characters_locations_generated["locations"][i]["id"] = i + 1
    #
    print("characters", str(characters_locations_generated["characters"]))

    brand_antagonist = False
    for i in range(len(characters_locations_generated["characters"])):
        if characters_locations_generated["characters"][i]["type"] == "mini enemy":
            print("si hay mini enemy")

    # for i in range(len(characters_locations_generated["objects"])):
    #     characters_locations_generated["objects"][i]["id"] = i + 1

    print("characters_locations_generated", time.time() - star_time)

    # print("characters_locations_generated", characters_locations_generated)

    schema_scene = {
        "number": "int (number of the scene described by the user)",
        "title": "string (title of the scene)",
        "description": "string (description of the scene)",
        "content": "string (content of the scene)",
        "dynamic": "string (dynamics of the scene "
                   "Delivery, a scene in which one character finds an object and must deliver it to another character in another location. "
                   "Dialog, where two characters converse. Battle, a combat scene with an enemy."
                   " Battle Group, a combat scene with a number of mini enemies. "
                   "Search, a scene where a character searches for an object."
                   " Question, a scene where a character asks a question to another character. just one option)",
        "reward": "string (scene reward info if the scene is dialog only, next if no item is delivered,"
                  " item if item is delivered. only one choice)",
        "start_dialogues": [
            {
                "id_character": "string (id of the character)",
                "content": "string (content of the dialogue)"
            },
        ],
        "end_dialogues": [
            {
                "id_character": "string (id of the character)",
                "content": "string (content of the dialogue)"
            }
        ],
        "questions": {
            "options": [
                {
                    "id": "int (number of the option)",
                    "content": "string (content of the option)"
                },
            ],
            "correct_option": "int (number of the correct option)",
            "feedback": "string (feedback of the correct option)",
            "feedback_incorrect": "string (feedback of the incorrect option)"
        },
        "object_id": "int (id of the object)",
        "id_location": "int (location ids different from those already used)",
        "valid_locations": [
            {
                "id": "int (id of the location (valid locations for the scene)",
            },
        ],
        "is_subtractable": "bool (if the object is kept by the player it is true and if not it is false)",
        "delivery_location_id": "int (id of the location where the object is delivered)",
        "delivery_character_id": "int (id of the character who receives the object)"
    }

    scenes_generated = []

    location_id_used = []

    prompt_scene_copy = prompt_scene

    for i in range(4):
        # print("scene to generate", i + 1)
        prompt_scene = prompt_scene.replace("x_scene", f"{i + 1}")
        prompt_scene = prompt_scene.replace("x_script", num)

        # print("prompt_scene", prompt_scene)

        content_prompt = [
            {
                "role": "system",
                "content": f"{prompt_scene_system}"
                #     f"Garantiza que en cada escena creada deben tener solo 2 personajes y uno de esos sea el personaje principal y el otro puede ser el mini enemigo, el enemigo o otro, "
                #            f"tambien varia cada en escena en difrentes locaciones, "
                #            f"solo la dinamica de question debe tener questions,"
                #            f"todas las escenas deben tener la locacion diferente,"
                #            f"las opciones de las preguntas no deben ser mas de 3, "
                #            f"el tipo de dinamica battle group debe ser solo entre el principal y el mini enemigo,"
                # # f"el tipo de dinamica battle debe ser solo entre el principal y el enemigo, "
                #            f"el tipo de dinamica search debe tener un objeto, dos personajes, ni el enemy, de reward item o next no puede tener questions,"
                #            f"el tipo de dinamica dialog debe tener dos personajes y de reward info, "
                #            f"el tipo de dinamica delivery es la unica que tiene delivery_location_id, delivery_character_id y "
                #            f"el delivery_location_id debe ser diferente a el location_id de la escena y el delivery_character_id deber ser difernente y "
                #            f" debe tener dos personajes y un tercero que es al que le entrega el objecto y de reward next,"
                #            f"si la recompenza es item, is_subtractable debe ser false y la dinamica debe ser delivery,"
                #            f"si la recompenza es item, is_subtractable debe ser true y la dinamica debe ser search,"
                #            f"las dinamicas de dialog, question, search, delivery, no puede ser un mini enemy, ni el enemy,"
                #            f"las dinamicas de battle, battle group, no puede ser un other, ni antagonista,"
                # # f"las dinamicas de search, battle, battle group, no puede tener questions, "
                #            f"las dinamicas de search no puede tener questions, "
                #            f"verificar los tipos de personajes para las dinamicas si no estan presentes usar otra dinamica,"
                #            f"la primera escena debe ser de dinamica question,"
                #            f"la segunda escena debe ser de dinamica search, "
                #            f"la tercera de dinamica delivery y "
                #            f"la cuarta de dinamica battle group,"
                # # f"la primera escena debe ser un dialogo, la segunda debe ser una busqueda de un objeto,"
                #            f"characters debe contendra los id de los personajes que aparecen en la escena que estan en los dialogos, "
                # # f"la tercera debe ser un pregunta y la cuarta de pelea grupal,"
                # # f"en cada escena solo pueden haber 2 personajes, "
                           f"responde el prompt con la siguiente estructura JSON: {schema_scene}"
            },
            {
                "role": "system",
                "content": f"> historia: {history} \n"
                           f"> personajes y lugares: {characters_locations_generated}\n"
                           f"> locaciones usadas, no repetir: {location_id_used} \n"
                           f"> escena anterior: {scenes_generated[i - 1] if scenes_generated else ''} \n"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_scene
                    }
                ]
            }
        ]

        response_scene = generate_gpt4_(content_prompt=content_prompt,
                                        type_text="script",
                                        max_tokens=4096, )

        scene_generated_json = json.loads(response_scene)

        location_id_used.append(scene_generated_json["id_location"])

        characters_scene = []

        if scene_generated_json["dynamic"] == "Battle Group":
            print("si hay battle group")
            scene_generated_json["count_enemies"] = random.randint(1, 3)
            scene_generated_json["delivery_location_id"] = ""
            scene_generated_json["delivery_character_id"] = ""
            scene_generated_json["object_id"] = ""
            scene_generated_json["is_subtractable"] = False
            scene_generated_json["questions"] = None
            scene_generated_json["reward"] = "next"

            for k in characters_locations_generated["characters"]:
                if k["type"] == "mini enemy":
                    print("si hay mini enemy en battle group", k["id"])
                    scene_generated_json["enemy_id"] = k["id"]
        if "start_dialogues" in scene_generated_json:
            for h in range(len(scene_generated_json["start_dialogues"])):
                if {"id": scene_generated_json["start_dialogues"][h]["id_character"]} not in characters_scene:
                    characters_scene.append({"id": scene_generated_json["start_dialogues"][h]["id_character"]})

        if "end_dialogues" in scene_generated_json:
            for h in range(len(scene_generated_json["end_dialogues"])):
                if {"id": scene_generated_json["end_dialogues"][h]["id_character"]} not in characters_scene:
                    characters_scene.append({"id": scene_generated_json["end_dialogues"][h]["id_character"]})

        scene_generated_json["characters"] = characters_scene

        brand_enemies = False
        brand_mini_enemies = False
        if len(scene_generated_json["characters"]) > 0:
            for i in range(len(scene_generated_json["characters"])):
                for j in range(len(characters_locations_generated["characters"])):
                    if scene_generated_json["characters"][i]["id"] == characters_locations_generated["characters"][j][
                        "id"]:
                        if characters_locations_generated["characters"][j]["type"] == "enemy":
                            brand_enemies = True
                            scene_generated_json["enemy_id"] = characters_locations_generated["characters"][j]["id"]
                        if characters_locations_generated["characters"][j]["type"] == "mini enemy":
                            brand_mini_enemies = True
                            scene_generated_json["count_enemies"] = random.randint(1, 3)
                            scene_generated_json["enemy_id"] = characters_locations_generated["characters"][j]["id"]

        if brand_enemies:
            scene_generated_json["enemy_id"] = ""
            scene_generated_json["count_enemies"] = 0

        if brand_mini_enemies:
            scene_generated_json["count_enemies"] = 0
            scene_generated_json["enemy_id"] = ""

        # print(scene_generated_json["questions"])
        if str(scene_generated_json["dynamic"]).upper() != "Question".upper():
            scene_generated_json["questions"] = None
        # if "questions" in scene_generated_json:
        #     if str(scene_generated_json["questions"]) == str({'options': [], 'correct_option': None, 'feedback': '',
        #                                              'feedback_incorrect': ''}) and scene_generated_json["dynamic"] != "Question":
        #         scene_generated_json["questions"] = None

        scenes_generated.append(scene_generated_json)

        # print("location_id_used", location_id_used)
        #
        # print("scene_generated" + str(i + 1), time.time() - star_time)
        #
        # print("scene_generated" + str(i + 1), scene_generated_json)

        prompt_scene = prompt_scene_copy

    print("scenes_generated", time.time() - star_time)

    for i in range(len(scenes_generated)):
        if scenes_generated[i]["dynamic"] == "Delivery":
            print("si hay delivery")
            if scenes_generated[i]["delivery_location_id"] == scenes_generated[i]["id_location"]:
                print("es la misma locacion")
            else:
                print("no es la misma locacion")

            if scenes_generated[i]["delivery_character_id"] in scenes_generated[i]["characters"]:
                print("si esta el personaje")
            else:
                print("no esta el personaje")

        if scenes_generated[i]["dynamic"] == "Battle group":
            print("si hay battle group")

    scene_cero = {
        "number": 0,
        "title": "introduction chapter",
        "description": "",
        "content": "",
        "dynamic": "",
        "reward": "",
        "start_dialogues": [],
        "end_dialogues": [],
        "questions": {},
        "object_id": [],
        "id_location": 0,
        "characters": [],
        "valid_locations": [],
        "count_enemies": 0,
        "enemy_id": "",
        "is_subtractable": False
    }

    location_scene = scenes_generated[0]["id_location"]

    for i in range(len(characters_locations_generated["locations"])):
        if characters_locations_generated["locations"][i]["id"] == location_scene:
            location_scene = characters_locations_generated["locations"][i]["description_outdoor"]
            break

    prompt_image_scene_cero = prompt_imagen_scene_cero.replace("x_location", location_scene)

    prompt_text_scene_cero = prompt_text_introduction_scene_cero

    json_content_scene_cero = {
        "description_introduction": "string (description of the introduction)",
    }

    prompt_content = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {json_content_scene_cero}"
        },
        {
            "role": "user",
            "content": f"historia: {history}"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt_text_scene_cero
                }
            ]
        }
    ]

    prompt_text_scene_cero = generate_gpt4_(content_prompt=prompt_content,
                                            type_text="scene cero",
                                            max_tokens=4096)

    response_image_scene_cero = generate_image_dalle(prompt=prompt_image_scene_cero,
                                                     quality="hd",
                                                     size="1024x1024"
                                                     )

    prompt_text_scene_cero = json.loads(prompt_text_scene_cero)

    scene_cero["start_content"] = prompt_text_scene_cero["description_introduction"]
    scene_cero["start_image"] = response_image_scene_cero

    scenes_generated.insert(0, scene_cero)

    image_before_battle = ""
    image_finish_chapter = ""

    scene_description = ""
    character1_description = ""
    character2_description = ""

    for i in scenes_generated:

        if i["dynamic"] == "Battle Group" or i["dynamic"] == "Battle":
            scene_description = i["description"]
            for j in characters_locations_generated["characters"]:
                if j["type"] == "leading role":
                    character1_description = j["description"]
                if j["type"] == "mini enemy":
                    character2_description = j["description"]
            break

    prompt_finish_chapter = prompt_finish_chapter.replace("x_scene", scene_description)

    prompt_finish_chapter = prompt_finish_chapter.replace("x_character", f"personaje: {character1_description}/n mini enemigo: {character2_description}")

    image_finish_chapter = generate_image_dalle(prompt= prompt_finish_chapter,
                                                quality="hd",
                                                size="1024x1024")


    scene_finish_chapter = scene_cero
    scene_finish_chapter["start_content"] = "Finish chapter"
    scene_finish_chapter["start_image"] = image_finish_chapter
    scene_finish_chapter["number"] = 5
    scene_finish_chapter["title"] = "Finish chapter"
    scenes_generated.insert(5, scene_finish_chapter)





    return {
        "script": script_generated,
        "characters_locations": characters_locations_generated,
        "scenes": scenes_generated
    }


def get_weapon_image(prompt_weapon: str,
                     type_weapon: str,
                     description: str,
                     extra_data: dict):
    complement = (f"description: {description} \n"
                  f"extra_data: {extra_data}"
                  f"tipo: {type_weapon}")

    content_prompt = prompt_weapon.replace("x_weapon", complement)

    response_image_weapon = generate_image_dalle(prompt=content_prompt,
                                                 quality="hd",
                                                 size="1024x1024")

    return response_image_weapon


def get_object_image(prompt_object: str,
                     description: str):
    complement = f"description: {description}"

    content_prompt = prompt_object.replace("x_object", complement)

    response_image_object = generate_image_dalle(prompt=content_prompt,
                                                 quality="hd",
                                                 size="1024x1024")

    return response_image_object
