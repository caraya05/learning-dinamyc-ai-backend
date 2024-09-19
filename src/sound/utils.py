import json

from fastapi import HTTPException
from fastapi import status

from gpt_ai.utils import generate_gpt4o
from sound.services import get_sounds_service


async def identify_by_location_service(description: str):
    try:
        sounds_db = await get_sounds_service()

        json_response = {
            "id": "id del sonido que mas se asemeja",
        }

        response = generate_gpt4o(
            content_prompt=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "con la siquiente image y descripcion de una locacion, escoje uno de los sonidos de la lista que se"
                               f"escucharia en este lugar, responde con el siquiente formato JSON {json_response}"
                        },
                        {
                            "type": "text",
                            "text": f"Listado de sonidos: {sounds_db}"
                        },
                        {
                            "type": "text",
                            "text": f"descripcion de la locacion : {description}"
                        },
                        # {
                        #     "type": "image_url",
                        #     "image_url": {
                        #         "url": image,
                        #     },
                        # },
                    ],
                }
            ],
            max_tokens=4096,
            type_text="identify_by_location"
        )

        return json.loads(response)

    except Exception as e:
        print(f"error in identify_by_location_service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Error in identify by location service")
