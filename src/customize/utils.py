import json

from gpt_ai.utils import generate_gpt4_


def get_customize_by_character(
        list_customizes: list, character_description: str
):
    try:
        prompt_customize = (
            "according to the description of this character, choose from the list "
            "a hair type that corresponds best to him/her,"
            "if you don't find the right one, if male enter the following 'hair_Man_V4', if female enter the following 'Hair_Woman_V1'. ."
        )

        schema_customize = {
            "id": "string (id of the customize)",
            "reference_ui": "string (reference_ui of the customize)",
        }

        content = [
            {
                "role": "system",
                "content": f"responde con un JSON que contenga el esquema '{schema_customize}'",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt_customize}"},
                    {"type": "text", "text": f"> character: {character_description}"},
                    {"type": "text", "text": f"> list of customizes: {list_customizes}"},
                ],
            },
        ]

        customize_generated = generate_gpt4_(
            content_prompt=content,
            type_text="customize",
            max_tokens=4096,
        )

        return json.loads(customize_generated)

    except Exception as e:

        return f"Customize not generated: {str(e)}"
