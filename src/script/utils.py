import json

from gpt_ai.utils import generate_gpt4_


def get_script_locations_chapter(synopsis: str, num: str, prompt_script: str):
    schema_script = {
        "number": "string (number of the chapter)",
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
                "number": "string (number of the scene)",
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
