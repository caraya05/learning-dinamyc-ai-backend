import json
import traceback
from datetime import datetime
import pytz
from pathlib import Path

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

# Precios de modelos OpenAI (por 1K tokens)
MODEL_PRICING = {
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "text-embedding-3-small": {"input": 0.02, "output": 0},
    "text-embedding-3-large": {"input": 0.13, "output": 0},
    "dall-e-3": {"input": 20.0, "output": 0},  # Por imagen
    "dall-e-2": {"input": 10.0, "output": 0},  # Por imagen
}


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


def calculate_ai_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    """
    Calcula el costo de una llamada a IA basado en tokens consumidos.

    Args:
        model (str): Nombre del modelo usado
        input_tokens (int): Número de tokens de entrada
        output_tokens (int): Número de tokens de salida

    Returns:
        dict: Información del costo desglosado
    """
    if model not in MODEL_PRICING:
        return {"error": f"Modelo '{model}' no soportado"}

    pricing = MODEL_PRICING[model]
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "timestamp": datetime.now(pytz.timezone("America/Bogota")).isoformat()
    }


async def save_ai_cost_to_file(cost_info: dict, user_id: str = None, file_path: str = "logs/ai_usage_costs.txt"):
    """
    Guarda el costo de una llamada a IA en un archivo txt.

    Args:
        cost_info (dict): Información del costo calculado
        user_id (str): ID del usuario que hizo la llamada
        file_path (str): Ruta del archivo de salida
    """
    try:
        # Crear directorio si no existe
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Crear entrada de costo
        entry = f"""
{'─'*80}
Timestamp: {cost_info.get('timestamp', 'N/A')}
Modelo: {cost_info.get('model', 'N/A')}
Usuario ID: {user_id or 'No especificado'}
Tokens Entrada: {cost_info.get('input_tokens', 0):,}
Tokens Salida: {cost_info.get('output_tokens', 0):,}
Tokens Totales: {cost_info.get('total_tokens', 0):,}
Costo Entrada: ${cost_info.get('input_cost_usd', 0):.6f}
Costo Salida: ${cost_info.get('output_cost_usd', 0):.6f}
Costo Total: ${cost_info.get('total_cost_usd', 0):.6f} USD
"""

        # Agregar al archivo
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(entry)

        print(f"[IA COST] Modelo: {cost_info.get('model')}, Costo: ${cost_info.get('total_cost_usd'):.6f} USD")

    except Exception as e:
        print(f"[ERROR] No se pudo guardar el costo: {str(e)}")


from dataclasses import asdict


async def store_response(response, prompt, model, type_generation: str, user_id=None, input_tokens: int = 0, output_tokens: int = 0):
    """
    Almacena la respuesta y calcula el costo de la llamada a IA.

    Args:
        response: Respuesta de la API
        prompt: Prompt enviado
        model: Modelo utilizado
        type_generation: Tipo de generación
        user_id: ID del usuario
        input_tokens: Tokens de entrada
        output_tokens: Tokens de salida
    """
    # Convert response to dictionary
    if hasattr(response, 'dict'):
        response_dict = response.dict()
    elif hasattr(response, '__dict__'):
        response_dict = response.__dict__
    else:
        response_dict = json.loads(json.dumps(asdict(response)))

    utc_now = datetime.now(pytz.utc)
    colombia_now = utc_now.astimezone(pytz.timezone("America/Bogota"))

    # Calcular costo si se proporcionan tokens
    cost_info = None
    if input_tokens > 0 or output_tokens > 0:
        cost_info = calculate_ai_cost(model, input_tokens, output_tokens)
        if "error" not in cost_info:
            # Guardar en archivo txt
            await save_ai_cost_to_file(cost_info, user_id=user_id)
            # Agregar costo a la respuesta almacenada
            response_dict['cost_info'] = cost_info

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
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_info": cost_info,
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
            style: str | None = "vivid",
            background: str | None = None,
    ):
        try:
            # Ajustar size y quality a los valores permitidos por la API
            allowed_sizes = ["auto", "1024x1024", "1536x1024", "1024x1536", "256x256", "512x512", "1792x1024", "1024x1792"]
            allowed_qualities = ["low", "medium", "high"]
            if size not in allowed_sizes:
                size = "1024x1792"
            if quality not in allowed_qualities:
                quality = "high"
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=count,
                style=style if style is not None else NOT_GIVEN,
                background=background if background is not None else NOT_GIVEN,
            )
            # Calcular tokens aproximados para imágenes (por imagen generada)
            # DALL-E 3: ~100 tokens de entrada + ~1600 tokens por imagen (basado en size)
            image_tokens = 1600 if size in ["1792x1024", "1024x1792"] else 1024 if size == "1024x1024" else 512
            input_tokens = 100
            output_tokens = image_tokens * count

            await store_response(
                response=response,
                prompt=prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            # Retornar url o base64
            if hasattr(response.data[0], "url") and response.data[0].url:
                return response.data[0].url
            elif hasattr(response.data[0], "b64_json"):
                return response.data[0].b64_json
            else:
                return None
        except Exception as e:
            print(traceback.format_exc())
            print(f"Error in generate_image: {str(e)}")
            return await handle_exception(e, prompt, model, user_id)

    async def generate_gpt(
            self,
            content_prompt: list[dict],
            response_format: BaseModel = None,
            type_generation: str = "",
            max_tokens: int | None = None,
            max_completion_tokens: int | None = None,
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
                kwargs = {
                    "model": model,
                    "response_format": response_format,
                    "messages": content_prompt,
                }
                # Solo pasar max_tokens, no max_completion_tokens
                if max_tokens is not None:
                    kwargs["max_tokens"] = 2048
                if max_completion_tokens is not None:
                    kwargs["max_completion_tokens"] = 2048
                response = await self.client.beta.chat.completions.parse(**kwargs)
            await store_response(
                response=response,
                prompt=content_prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
            )

            if vision:
                if hasattr(response, "choices") and response.choices:
                    return response.choices[0].message.content
                print("[ERROR] vision response no tiene 'choices'")
                return None

            if image:
                image_generation_calls = [
                    output
                    for output in getattr(response, "output", [])
                    if getattr(output, "type", None) == "image_generation_call"
                ]
                image_data = [getattr(output, "result", None) for output in image_generation_calls]
                if image_data and image_data[0]:
                    return image_data[0]
                print("[ERROR] image response no tiene datos válidos")
                return None

            if hasattr(response, "choices") and response.choices:
                if hasattr(response.choices[0].message, "parsed"):
                    return response.choices[0].message.parsed
                elif hasattr(response.choices[0].message, "content"):
                    return response.choices[0].message.content
                else:
                    print("[ERROR] choices[0].message no tiene 'parsed' ni 'content'")
                    return None
            print("[ERROR] response no tiene 'choices'")
            return None
        except Exception as e:
            print(f"Error in generate_gpt: {str(e)}")
            print(traceback.format_exc())
            return await handle_exception(
                e=e,
                prompt=content_prompt,
                model=model,
                type_generation=type_generation,
                user_id=user_id,
            )

    async def moderation_text(self, text: str, user_id: str = None):
        try:
            content_prompt = [
                {"role": "system", "content": "En este prompt se infringe gravemente los derechos de autor de algún personaje? o se está pidiendo generar contenido sexual explícito?"},
                {"role": "user", "content": text},
            ]
            kwargs = {
                "content_prompt": content_prompt,
                "response_format": SchemaResponseModerator,
                "type_generation": "moderation_text",
                "user_id": user_id,
                "max_tokens": 4000,
            }
            response = await self.generate_gpt(**kwargs)

            # Extraer información de tokens si está disponible
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage"):
                input_tokens = getattr(response.usage, "prompt_tokens", 0)
                output_tokens = getattr(response.usage, "completion_tokens", 0)

            await store_response(
                response=response,
                prompt=text,
                model="gpt-4o",
                type_generation="moderation_text",
                user_id=user_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            return hasattr(response, "response") and response.response.lower() in ["sí", "si", "yes"]
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
            # No modificar file_array.name directamente
            response = await self.client.files.create(
                file=file_array,
                purpose="fine-tune",
            )
            await store_response(
                response=response,
                prompt=getattr(file_array, "name", "image.png"),
                model="file_upload",
                type_generation="file_upload",
                user_id=user_id,
                input_tokens=0,
                output_tokens=0
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
                input_tokens=0,
                output_tokens=0
            )

            return response

        except Exception as e:
            print(f"Error in delete_file: {str(e)}")
            return await handle_exception(
                e=e, prompt=file_id, model="file_delete", type_generation="file_delete", user_id=user_id
            )


openai_generator = OpenAIGenerator()
