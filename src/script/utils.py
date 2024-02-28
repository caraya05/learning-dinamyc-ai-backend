import json
import time

from gpt_ai.utils import generate_gpt4_
from gpt_ai.utils import generate_image_dalle


def get_script_locations_chapter_v2(history: str, num: str,
                                    prompt_script: str,
                                    prompt_scene: str,
                                    # prompt_image_locations: str
                                    ):
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
            "content": f"responde el prompt con la siguiente estructura JSON: {schema_script}"
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
                "description": "string (Generate a 5-line description of one wall of each of these scenarios, and a 5-line description of the floor attached to this wall of each of these enclosed and covered scenarios.)"
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
                    "skin_color": "string (skin color of the character in format hexadecimal)",
                    "hair_color": "string (hair color of the character in format hexadecimal)",
                    "eye_color": "string (eye color of the character in format hexadecimal)",
                    "lips_color": "string (lips color of the character in format hexadecimal)",
                    "shoes_color": "string (shoes color of the character in format hexadecimal)",
                    "pants_color": "string (pants color of the character in format hexadecimal)",
                    "shirt_color": "string (shirt color of the character in format hexadecimal)",
                    "type_combing": "string (type of combing of the character)",
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
            "content": f"los weapon solo los debe tener el leading role,"
                       f"los escenarios deben ser cerrados y cubiertos ,"
                       f", responde el prompt con la siguiente estructura JSON: {schema_characters_locations}"
        },
        {
            "role": "assistant",
            "content": f"historia: {script_generated['description']} \n"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Dame una lista con nombre, y descripción física, género del protagonista, el antagonista, "
                            "y los personajes que aparecen en las primeras 4 escenas. Dale un nombre muy atractivo "
                            "al juego y que genere recordación. también dame una lista con nombre y descripción de los "
                            "lugares donde se desarrollan las primeras 4 escenas. ademas dame un listado los objetos que aparecen en la historia"
                }
            ]
        }
    ]

    response_characters_locations = generate_gpt4_(content_prompt=content_prompt,
                                                   type_text="script",
                                                   max_tokens=4096, )

    characters_locations_generated = json.loads(response_characters_locations)

    print("characters_locations_generated", time.time() - star_time)

    # print("characters_locations_generated", characters_locations_generated)

    schema_scene = {
        "number": "int (number of the scene described by the user)",
        "title": "string (title of the scene)",
        "description": "string (description of the scene)",
        "content": "string (content of the scene)",
        "dynamic": "string (dynamics of the scene delivery, dialog, battle, battle group, search, question. just one option)",
        "reward": "string (scene reward info if the scene is dialogue only, next if no item is delivered, item if item is delivered. only one choice)",
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
        "characters": [
            {
                "id": "int (id of the character)",
            },
        ],
        "valid_locations": [
            {
                "id": "int (id of the location (valid locations for the scene)",
            },
        ],
        "count_enemies": "int (number of enemies in the scene)",
        "enemy_id": "int (id of the enemy)",
        "is_subtractable": "bool (if the object is kept by the player it is true and if not it is false)"
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
                "content": f"Garantiza que en cada escena creada el personaje principal siempre este presente y "
                           f"tambien varia cada en escena en difrentes locaciones, no puede repetir escenario y location,"
                           f"solo la dinamica de question puede tener preguntas, "
                           f"la primera escena debe ser un dialogo, la segunda debe ser una busqueda de un objeto,"
                           f"la tercera debe ser un pregunta y la cuarta de pelea grupal,"
                           f"en cada escena solo pueden haber 2 personajes y 1 locacion,"
                           f"responde el prompt con la siguiente estructura JSON: {schema_scene}"
            },
            {
                "role": "system",
                "content": f"> historia: {history} \n"
                           f"> personajes y lugares: {characters_locations_generated}\n"
                           f"> locaciones usadas, no repetir: {location_id_used} \n"
                           f"> escenas generadas: {script_generated['scenes']} \n"
                           f"> escena {scenes_generated[i - 1] if scenes_generated else ''} \n"
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

        scenes_generated.append(scene_generated_json)

        # print("location_id_used", location_id_used)
        #
        # print("scene_generated" + str(i + 1), time.time() - star_time)
        #
        # print("scene_generated" + str(i + 1), scene_generated_json)

        prompt_scene = prompt_scene_copy

    print("scenes_generated", time.time() - star_time)

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
            location_scene = characters_locations_generated["locations"][i]["description"]
            break

    prompt_image_scene_cero = (f"Genera una imagen en arte voxel y vista isométrica de 1024x1024 "
                               f"del exterior del {location_scene} de la escena 1")

    prompt_text_scene_cero = (f"Genera una introducción que debe decir un narrador antes de la primera escena de"
                              f" esta historia, que coloque en contexto y le genere expectativa al jugador,"
                              f" en no más de 6 renglones. (En inglés)")

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
                                                 size="1024x1024"
                                                 )

    return response_image_weapon


def get_object_image(prompt_object: str,
                     description: str):
    complement = f"description: {description}"

    content_prompt = prompt_object.replace("x_object", complement)

    response_image_object = generate_image_dalle(prompt=content_prompt,
                                                 quality="hd",
                                                 size="1024x1024")

    return response_image_object
