import json

from gpt_ai.utils import generate_gpt4_vision_
from gpt_ai.utils import generate_gpt4_


def get_extra_data_character_ai(prompt: list):
    extra_data_text = generate_gpt4_vision_(content_prompt=prompt, max_tokens=4096)

    print("extra_data_text", extra_data_text)

    json_schema = {
        "extra_data": {
            "skin_color": "string (skin color of the character in format hexadecimal)",
            "hair_color": "string (hair color of the character in format hexadecimal)",
            "eye_color": "string (eye color of the character in format hexadecimal)",
            "lips_color": "string (lips color of the character in format hexadecimal)",
            "shoes_color": "string (shoes color of the character in format hexadecimal)",
            "pants_color": "string (pants color of the character in format hexadecimal)",
            "shirt_color": "string (shirt color of the character in format hexadecimal)",
            "type_combing": "string (type of combing of the character)",
            "type_mini_enemy": "string (classify the character between these options GOBLIN, SPECTRUM, SNAKE, BIRD, WOLF if not classified between none place none)",
        }
    }

    prompt_content_json = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {json_schema}",
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"convertir a json la siquiente descripcion del personaje: {extra_data_text},"
                    f"en dado que no se puedan determinar los colores colocar un color adorde a los demas colores.",
                }
            ],
        },
    ]

    extra_data_generated = generate_gpt4_(content_prompt=prompt_content_json, max_tokens=4096)

    return json.loads(extra_data_generated)
