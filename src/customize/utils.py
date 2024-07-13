import json

from gpt_ai.utils import generate_gpt4_, generate_gpt4o


def get_customize_by_character(
        list_customizes: list, character_description: str
):
    try:
        prompt_customize = (
            "according to the description of this character, choose from the list "
            "a type of hair that corresponds best to him/her,"
            "if you don't find the right one enter 'hair_Man_V4' if the character is male and 'Hair_Woman_V1' if the character is female "
        )

        schema_customize = {
            "id": "string (id of the customize)",
            "reference_ui": "string (reference_ui of the customize)",
        }

        content = [
            {
                "role": "system",
                "content": f"'{prompt_customize}'",
            },
            {
                "role": "system",
                "content": f"responde con un JSON que contenga el esquema '{schema_customize}'",
            },
            {
                "role": "user",
                "content": [
                    # {"type": "text", "text": f"{prompt_customize}"},
                    {"type": "text", "text": f"Descripcion del personaje: {character_description}"},
                    {"type": "text", "text": f"Listado de peinados : {list_customizes}"},
                ],
            },
        ]

        customize_generated = generate_gpt4o(
            content_prompt=content,
            type_text="customize",
            max_tokens=4096,
        )

        return json.loads(customize_generated)

    except Exception as e:

        return f"Customize not generated: {str(e)}"
