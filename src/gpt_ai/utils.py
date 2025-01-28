from datetime import datetime
import pytz

from fastapi import HTTPException

from openai import AsyncClient as OpenAI
from openai import BaseModel
import openai
from openai import APIConnectionError
from openai import RateLimitError
from openai import APIStatusError
from openai import UnprocessableEntityError
from openai import PermissionDeniedError
from openai import NotFoundError
from openai import InternalServerError
from openai import ConflictError
from openai import BadRequestError
from openai import AuthenticationError
from openai import APITimeoutError
from pydantic import Field
from pydantic import BaseModel as PydanticBaseModel

from config import settings

from core.database import db


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
        error_message = "The request was well-formed but was unable to be followed due to semantic errors."
        status_code = 422
    elif isinstance(e, openai.PermissionDeniedError):
        error_message = "The request was understood but it has been refused or access is not allowed."
        status_code = 403
    elif isinstance(e, openai.NotFoundError):
        error_message = "The requested resource could not be found."
        status_code = 404
    elif isinstance(e, openai.InternalServerError):
        error_message = "The server encountered an internal error and was unable to complete your request."
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

    print("llego aca 1")

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

    print("llego aca 2")
    return HTTPException(status_code=status_code, detail=error_message)


from dataclasses import asdict


async def store_response(response, prompt, model, type_generation: str, user_id=None):
    # Convert response to dictionary
    if hasattr(response, 'dict'):
        response_dict = response.dict()
    elif hasattr(response, '__dict__'):
        response_dict = response.__dict__
    else:
        response_dict = asdict(response)

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
            quality: str = "standard",
            user_id: str = None,
            type_generation: str = None,
    ):
        try:
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=count,
                style="vivid",
            )

            await store_response(
                response=response,
                prompt=prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
            )

            return response.data[0].url

        except Exception as e:
            print(f"Error in generate_image: {str(e)}")

            return await handle_exception(e, prompt, model, user_id)

    async def generate_gpt(
            self,
            content_prompt: list[dict],
            response_format: BaseModel,
            type_generation: str = "",
            max_tokens: int = 1000,
            model: str = "gpt-4o",
            user_id: str = None,
    ):
        try:
            response = await self.client.beta.chat.completions.parse(
                model=model,
                response_format=response_format,
                messages=content_prompt,
                max_tokens=max_tokens,
                stop=None,
                temperature=0.6,
                top_p=0.8,
                frequency_penalty=0.6,
                presence_penalty=0.7,

            )

            await store_response(
                response=response,
                prompt=content_prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
            )

            return response.choices[0].message.parsed

        except Exception as e:
            print(f"Error in generate_gpt: {str(e)}")
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
                    "content": "En este prompt se infringe gravemente los derechos de autor de algún personaje? o se está pidiendo generar contenido sexual explícito?"
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = await self.generate_gpt(
                content_prompt=content_prompt,
                response_format=SchemaResponseModerator,
                type_generation="moderation_text",
                max_tokens=100,
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


openai_generator = OpenAIGenerator()
