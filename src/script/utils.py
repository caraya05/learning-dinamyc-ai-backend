import json
import time

from gpt_ai.utils import generate_gpt4_
# from gpt_ai.utils import generate_image_dalle


def get_script_locations_chapter(synopsis: str, num: str, prompt_script: str):
    schema_script = {
        "number": "int (number of the chapter)",
        "title": "string (title of the chapter)",
        "description": "string (description of the chapter)",
        "characters": [
            {
                "name": "string (name of the character)",
                "description": "string (description of the character in detail that can be used to generate an image)",
                "type": "string (the character types are: leading role, other, enemy, antagonist."
                        "There can only be one antagonist, one leading role, one enemy and many others. ) ",
                "genre": "string (genre of the character is man or woman )"
            },
        ],
        "locations": [
            {
                "name": "string (name of the location)",
                "description": "string (description of the location in detail to generate an image of the location)"
            }
        ],
        "objects": [
            {
                "name": "string (name of the object)",
                "description": "string (description of the object)"
            }
        ],
        "scenes": [
            {
                "number": "int (number of the scene)",
                "title": "string (title of the scene)",
                "description": "string (description of the scene)",
                "content": "string (content of the scene)",
                "dynamic": "string (dynamics of the scene search, deliver, talk, questions, confront)",
                "dialogues": [
                    {
                        "character": "string (name of the character)",
                        "content": "string (content of the dialogue)"
                    },
                ],
                "objects": [
                    {
                        "name": "string (name of the object)",
                    },
                ],
                "location": "string (name of the location)",
                "characters": [
                    {
                        "name": "string (name of the character)",
                    },
                ],
            }
        ],
    }

    text_user = prompt_script.replace("x_num", num)

    #
    prompt_content = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {schema_script}"
        },
        {
            "role": "assistant",
            "content": f"historia: {synopsis}"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": text_user
                }
            ]
        }
    ]

    response = generate_gpt4_(content_prompt=prompt_content,
                              type_text="script",
                              max_tokens=4096, )

    return json.loads(response)


def get_script_locations_chapter_v2(history: str, num: str,
                                    prompt_script: str,
                                    prompt_scene: str,
                                    # prompt_image_locations: str
                                    ):
    # star_time = time.time()

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

    # print("script_generated", time.time() - star_time)

    schema_characters_locations = {
        "characters": [
            {
                "id": "int (character id greater than 1) ",
                "name": "string (name of the character)",
                "description": "string (description of the character in detail that can be used to generate an image)",
                "type": "string (the character types are: leading role, other, enemy, antagonist."
                        "There can only be one antagonist, one leading role, one enemy and many others. ) ",
                "genre": "string (genre of the character is man or woman )"
            },
        ],
        "locations": [
            {
                "id": "int (location id greater than 1)",
                "name": "string (name of the location)",
                "description": "string (Generate a 5-line description of one wall of each of these scenarios, and a 5-line description of the floor attached to this wall of each of these enclosed and covered scenarios.)"
            }
        ],
        "summary": "string (summary of all characters and locations)"
    }

    content_prompt = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {schema_characters_locations}"
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
                            "lugares donde se desarrollan las primeras 4 escenas."
                }
            ]
        }
    ]

    response_characters_locations = generate_gpt4_(content_prompt=content_prompt,
                                                   type_text="script",
                                                   max_tokens=4096, )

    characters_locations_generated = json.loads(response_characters_locations)

    # print("characters_locations_generated", time.time() - star_time)

    # for location in characters_locations_generated["locations"]:
    #     content_prompt = f"{prompt_image_locations} {location['description']}"
    #
    #     response_image_location = generate_image_dalle(prompt=content_prompt)
    #
    #     location["image"] = response_image_location
    #
    # for character in characters_locations_generated["characters"]:
    #     content_prompt = f"{prompt_image_characters} genero :{character['description']} descripcion: {character['description']}"
    #
    #     response_image_character = generate_image_dalle(prompt=content_prompt)
    #
    #     character["image"] = response_image_character

    schema_scene = {
        "number": "int (number of the scene described by the user)",
        "title": "string (title of the scene)",
        "description": "string (description of the scene)",
        "content": "string (content of the scene)",
        "dynamic": "string (dynamics of the scene search, deliver, talk, questions, confront)",
        "dialogues": [
            {
                "id_character": "string (id of the character)",
                "content": "string (content of the dialogue)"
            },
        ],
        "objects": [
            {
                "name": "string (name of the object)",
            },
        ],
        "id_location": "int (id of the location)",
        "characters": [
            {
                "id": "int (id of the character)",
            },
        ],
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

        # print("scene_generated" + response_scene)

        # print("scene_generated" + str(i+1), time.time() - star_time)

    # print("scenes_generated", time.time() - star_time)

    return {
        "script": script_generated,
        "characters_locations": characters_locations_generated,
        "scenes": scenes_generated
    }
