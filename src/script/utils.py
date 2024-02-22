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
    }

    prompt_script = prompt_script.replace("x_history", history)

    content_prompt = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {schema_script}"
        },
        # {
        #     "role": "assistant",
        #     "content": f"historia: {history}"
        # },
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
                # "weapons": {
                #     "id": "int (id of the weapon)",
                #     "name": "string (name of the weapon)",
                #     "description": "string (description of the weapon)",
                #     "type": "string (type of the weapon) (short, long)",
                #     "extra_data": {
                #         "color_body": "string (color of the body of the weapon in format hexadecimal)",
                #         "color_tip": "string (color of the tip of the weapon in format hexadecimal)",
                #         "color_complement_1": "string (color of the complement 1 of the weapon in format hexadecimal)",
                #         "color_complement_2": "string (color of the complement 2 of the weapon in format hexadecimal)",
                #     }
                # }
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
            "content": f"los weapon solo los debe tener el leading role y el enemy, responde el prompt con la siguiente estructura JSON: {schema_characters_locations}"
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

    schema_scene = {
        "number": "int (number of the scene described by the user)",
        "title": "string (title of the scene)",
        "description": "string (description of the scene)",
        "content": "string (content of the scene)",
        "dynamic": "string (dynamics of the scene deliver, dialog, battle, battle group, search, question. just one option)",
        "reward": "string (reward of the scene)",
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
        "objects": [
            {
                "id": "int (id of the object)",
            },
        ],
        "id_location": "int (id of the location)",
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
        "is_subtractable": "bool (if the object to be entered is subtractable)"
    }

    scenes_generated = []

    for i in range(4):
        prompt_scene = prompt_scene.replace("x_scene", f"{i + 1}")
        prompt_scene = prompt_scene.replace("x_script", num)
        content_prompt = [
            {
                "role": "system",
                "content": f"responde el prompt con la siguiente estructura JSON: {schema_scene}"
            },
            {
                "role": "assistant",
                "content": f"historia: {history} \n"
                           f"personajes y lugares: {characters_locations_generated}"
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

        scenes_generated.append(json.loads(response_scene))

        print("scene_generated" + str(i + 1), time.time() - star_time)

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
        "objects": [],
        "id_location": 0,
        "characters": [],
        "valid_locations": [],
        "count_enemies": 0,
        "enemy_id": 0,
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
            "role": "assistant",
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
