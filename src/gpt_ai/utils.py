import json
import traceback
from datetime import datetime
import pytz

from typing import IO
from fastapi import HTTPException

from openai import AsyncClient as OpenAI, NotGiven
from openai import BaseModel
import openai
from openai import BadRequestError
from pydantic import Field
from pydantic import BaseModel as PydanticBaseModel

from config import settings

from core.database import db

NOT_GIVEN = NotGiven()


class SchemaResponseModerator(PydanticBaseModel):
    response: str = Field(..., example="response", description="response of the moderator")


async def handle_exception(e, prompt, model, type_generation: str, user_id=None):
    error_message = str(e)
    status_code = 500

    print(f"Error 123: {type(e)}")
    print(f"Error 123: {type(BadRequestError)}")

    if isinstance(e, openai.APIConnectionError):
        error_message = f"The server could not be reached: {str(e.__cause__)}"
        status_code = 500
    elif isinstance(e, openai.RateLimitError):
        error_message = "A 429 status code was received; we should back off a bit."
        status_code = 429
    # elif isinstance(e, openai.APIStatusError):
    #     error_message = f"Another non-200-range status code was received: {str(e.status_code)}"
    #     status_code = e.status_code
    elif isinstance(e, openai.UnprocessableEntityError):
        error_message = (
            "The request was well-formed but was unable to be followed due to semantic errors."
        )
        status_code = 422
    elif isinstance(e, openai.PermissionDeniedError):
        error_message = (
            "The request was understood but it has been refused or access is not allowed."
        )
        status_code = 403
    elif isinstance(e, openai.NotFoundError):
        error_message = "The requested resource could not be found."
        status_code = 404
    elif isinstance(e, openai.InternalServerError):
        error_message = (
            "The server encountered an internal error and was unable to complete your request."
        )
        status_code = 500
    elif isinstance(e, openai.ConflictError):
        error_message = "The request could not be completed due to a conflict with the current state of the resource."
        status_code = 409
    elif isinstance(e, openai.BadRequestError):
        error_message = "The server could not understand the request due to invalid syntax."
        status_code = 400
    elif isinstance(e, openai.AuthenticationError):
        error_message = "Authentication failed; the request has not been applied because it lacks valid authentication credentials."
        status_code = 401
    elif isinstance(e, openai.APITimeoutError):
        error_message = "The request timed out."
        status_code = 504

    utc_now = datetime.now(pytz.utc)
    colombia_now = utc_now.astimezone(pytz.timezone("America/Bogota"))

    await db["logs"].insert_one(
        {
            "status": status_code,
            "is_error": True,
            "message": error_message,
            "response": str(e),  # Asegúrate de convertir la excepción a cadena
            "prompt": prompt,
            "model": model,
            "type_generation": type_generation,
            "user_id": user_id,
            "created_at": colombia_now,
        }
    )

    return HTTPException(status_code=status_code, detail=error_message)


from dataclasses import asdict


async def store_response(response, prompt, model, type_generation: str, user_id=None):
    # Convert response to dictionary
    if hasattr(response, 'dict'):
        response_dict = response.dict()
    elif hasattr(response, '__dict__'):
        response_dict = response.__dict__
    else:
        response_dict = json.loads(json.dumps(asdict(response)))

    utc_now = datetime.now(pytz.utc)
    colombia_now = utc_now.astimezone(pytz.timezone("America/Bogota"))

    await db["logs"].insert_one(
        {
            "status": 200,
            "is_error": False,
            "message": "Response stored successfully",
            "response": response_dict,
            "prompt": prompt,
            "model": model,
            "type_generation": type_generation,
            "user_id": user_id,
            "created_at": colombia_now,
        }
    )


class OpenAIGenerator:
    def __init__(self):
        self.client = OpenAI(
            organization=settings.OPENAI_API_ORG_ID, api_key=settings.OPENAI_API_KEY
        )

    async def generate_image(
            self,
            prompt: str,
            model: str = "dall-e-3",
            count: int = 1,
            size: str = "1024x1792",
            quality: str = "high",
            user_id: str = None,
            type_generation: str = None,
            style: str | None = "vivid",  # Assuming style is optional and can be NotGiven
    ):
        try:
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=count,
                style=style if style is not None else NOT_GIVEN,
            )

            await store_response(
                response=response,
                prompt=prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
            )

            return response.data[0].url if response.data[0].url else response.data[0].b64_json

        except Exception as e:
            print(traceback.format_exc())
            print(f"Error in generate_image: {str(e)}")

            return await handle_exception(e, prompt, model, user_id)

    async def generate_gpt(
            self,
            content_prompt: list[dict],
            response_format: BaseModel = None,
            type_generation: str = "",
            max_tokens: int = 4096,
            model: str = "gpt-4o",
            user_id: str = None,
            vision: bool = False,
            image: bool = False,
            tools: list[str] | None = None,

    ):
        try:
            if vision:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=content_prompt,
                    max_tokens=max_tokens,
                )
            elif image:
                response = await self.client.responses.create(
                    model=model,
                    input=content_prompt,
                    tools=[{"type": "image_generation"}],
                )
            else:
                response = await self.client.beta.chat.completions.parse(
                    model=model,
                    response_format=response_format,
                    messages=content_prompt,
                    max_tokens=max_tokens,
                )

            await store_response(
                response=response,
                prompt=content_prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
            )

            if vision:
                return response.choices[0].message.content

            if image:
                image_generation_calls = [
                    output
                    for output in response.output
                    if output.type == "image_generation_call"
                ]

                image_data = [output.result for output in image_generation_calls]

                if image_data:
                    image_base64 = image_data[0]
                    return image_base64

            return response.choices[0].message.parsed

        except Exception as e:
            print(f"Error in generate_gpt: {str(e)}")
            print(traceback.format_exc())
            return await handle_exception(
                e=e,
                prompt=content_prompt,
                model=model,
                type_generation=type_generation,
                user_id=None,
            )

    async def moderation_text(self, text: str, user_id: str = None):
        try:
            content_prompt = [
                {
                    "role": "system",
                    "content": "En este prompt se infringe gravemente los derechos de autor de algún personaje? o se está pidiendo generar contenido sexual explícito?",
                },
                {"role": "user", "content": text},
            ]

            response = await self.generate_gpt(
                content_prompt=content_prompt,
                response_format=SchemaResponseModerator,
                type_generation="moderation_text",
                max_tokens=4000,
                user_id=user_id,
            )

            await store_response(
                response=response,
                prompt=text,
                model="gpt-4o",
                type_generation="moderation_text",
                user_id=user_id,
            )

            return response.response.lower() in ["sí", "si", "yes"]

        except Exception as e:
            print(f"Error in moderation_text: {str(e)}")
            await handle_exception(
                e=e,
                prompt=text,
                model="gpt-4o",
                type_generation="moderation_text",
                user_id=user_id,
            )

            return None

    async def create_file(
            self,
            file_array: IO[bytes],
            purpose: str = "fine-tune",
            user_id: str = None,
    ):
        try:
            # Asegúrate de que el archivo tenga un nombre con una extensión válida
            if not hasattr(file_array, 'name') or not file_array.name:
                file_array.name = "image.png"  # Usa una extensión soportada como .png

            response = await self.client.files.create(
                file=file_array,
                purpose=purpose,
            )

            await store_response(
                response=response,
                prompt=file_array.name,
                model="file_upload",
                type_generation="file_upload",
                user_id=user_id,
            )

            return response

        except Exception as e:
            print(f"Error in create_file: {str(e)}")
            return await handle_exception(
                e=e, prompt="", model="file_upload", type_generation="file_upload", user_id=user_id
            )
    async def delete_file(
            self,
            file_id: str,
            user_id: str = None,
    ):
        try:
            response = await self.client.files.delete(file_id=file_id)

            await store_response(
                response=response,
                prompt=file_id,
                model="file_delete",
                type_generation="file_delete",
                user_id=user_id,
            )

            return response

        except Exception as e:
            print(f"Error in delete_file: {str(e)}")
            return await handle_exception(
                e=e, prompt=file_id, model="file_delete", type_generation="file_delete", user_id=user_id
            )


openai_generator = OpenAIGenerator()
