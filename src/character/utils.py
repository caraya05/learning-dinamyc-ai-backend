import json

from gpt_ai.utils import generate_gpt4_vision_
from gpt_ai.utils import generate_gpt4_


def get_extra_data_character_ai(prompt: list):
    extra_data_text = generate_gpt4_vision_(content_prompt=prompt,
                                            max_tokens=4096)

    json_schema = {
        "extra_data": {
            "skin_color": "string or None (skin color of the character in format hexadecimal)",
            "hair_color": "string or None (hair color of the character in format hexadecimal)",
            "eye_color": "string or None (eye color of the character in format hexadecimal)",
            "lips_color": "string or None (lips color of the character in format hexadecimal)",
            "shoes_color": "string or None (shoes color of the character in format hexadecimal)",
            "pants_color": "string or None (pants color of the character in format hexadecimal)",
            "shirt_color": "string or None (shirt color of the character in format hexadecimal)",
            "type_combing": "string or None (type of combing of the character)",
        }
    }

    prompt_content_json = [
        {
            "role": "system",
            "content": f"responde el prompt con la siguiente estructura JSON: {json_schema}"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"convertir a json la siquiente descripcion del personaje: {extra_data_text},"
                            f"en dado que no se puedan determinar los colores colocar un color adorde a los demas colores."
                }
            ]
        }
    ]

    extra_data_generated = generate_gpt4_(content_prompt=prompt_content_json,
                                          max_tokens=4096)

    return json.loads(extra_data_generated)
