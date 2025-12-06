import json
from typing import List, Dict, Literal

from gpt_ai.utils import openai_generator
from pydantic import BaseModel, Field


class CategorizedImage(BaseModel):
    """Schema para una imagen categorizada individual"""
    index: int = Field(..., description="Índice de la imagen en la lista original")
    category: Literal["character", "object", "scenario", "logo", "uncategorized"] = Field(
        ..., description="Categoría asignada a la imagen"
    )
    name: str = Field(..., max_length=50, description="Nombre descriptivo corto")
    description: str = Field(..., max_length=200, description="Descripción detallada")


class CategorizeImagesResponse(BaseModel):
    """Schema para la respuesta completa de categorización"""
    images: List[CategorizedImage] = Field(..., description="Lista de imágenes categorizadas")

    class Config:
        json_schema_extra = {
            "example": [
                {
                    "index": 0,
                    "category": "character",
                    "name": "Guerrero medieval",
                    "description": "Personaje con armadura plateada y espada"
                },
                {
                    "index": 1,
                    "category": "scenario",
                    "name": "Castillo antiguo",
                    "description": "Castillo de piedra en montaña"
                }
            ]
        }



async def categorize_reference_images(
    image_urls: List[str],
    prompt_user: str
) -> Dict[str, List[Dict]]:
    """
    Categoriza imágenes de referencia según el prompt usando visión de GPT-4.

    Args:
        image_urls: Lista de URLs de imágenes cargadas en storage
        prompt_user: Prompt del usuario para el juego

    Returns:
        Diccionario con imágenes categorizadas:
        {
            "characters": [{"url": "...", "name": "...", "description": "..."}],
            "objects": [{"url": "...", "name": "...", "description": "..."}],
            "scenarios": [{"url": "...", "name": "...", "description": "..."}],
            "logos": [{"url": "...", "name": "...", "description": "..."}],
            "uncategorized": [{"url": "...", "description": "..."}]
        }
    """

    if not image_urls:
        return {
            "characters": [],
            "objects": [],
            "scenarios": [],
            "logos": [],
            "uncategorized": []
        }


    # Construir el mensaje con las imágenes
    content = [
        {
            "type": "text",
            "text": f"""Analiza las siguientes imágenes de referencia para un juego interactivo.

Contexto del juego:
- Prompt del usuario: {prompt_user}

Categoriza CADA imagen en una de estas categorías y devuelve un JSON válido:
1. "character": Un personaje del juego (personas, criaturas, seres)
2. "object": Objetos pequeños o medianos (armas, herramientas, items, decoraciones)
3. "scenario": Escenarios, locaciones, fondos, ambientes completos
4. "logo": Logos, iconos, símbolos, diseños de UI
5. "uncategorized": Si no se puede categorizar claramente

Para cada imagen, proporciona:
- category: La categoría asignada
- name: Un nombre descriptivo corto (máx 50 caracteres)
- description: Descripción detallada de qué se ve (máx 200 caracteres)

Devuelve SOLO un JSON válido sin markdown ni explicaciones adicionales:
[
  {{
    "index": 0,
    "category": "character|object|scenario|logo|uncategorized",
    "name": "nombre",
    "description": "descripción"
  }}
]"""
        }
    ]

    # Agregar URLs de imágenes
    for url in image_urls:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": url,
                "detail": "low"
            }
        })

    try:
        response = await openai_generator.generate_gpt(
            content_prompt=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            model="gpt-4.1",
            response_format=None,
            type_generation="categorize_images",
            user_id=None,
            max_tokens=2000,
            vision=True,
        )

        # La respuesta viene como string JSON, necesitamos parsearlo
        if isinstance(response, str):
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError as parse_error:
                print(f"Error parsing JSON response: {parse_error}")
                print(f"Response content: {response}")
                return {
                    "characters": [],
                    "objects": [],
                    "scenarios": [],
                    "logos": [],
                    "uncategorized": [
                        {"url": url, "description": "No categorizado - error de parseo JSON"}
                        for url in image_urls
                    ]
                }
        else:
            response_data = response

        # Si la respuesta es una lista directa de objetos, convertirla a la estructura esperada
        categorized_data = []

        if isinstance(response_data, list):
            print(f"Response es lista con {len(response_data)} items")
            for idx, item in enumerate(response_data):
                try:
                    print(f"Procesando item {idx}: {item}")
                    cat_image = CategorizedImage(**item)
                    categorized_data.append(cat_image)
                    print(f"Item {idx} validado exitosamente: {cat_image}")
                except Exception as e:
                    print(f"Error validando item {idx}: {str(e)}")
                    print(f"Datos del item: {item}")
        elif isinstance(response_data, dict) and "images" in response_data:
            print(f"Response es dict con 'images', {len(response_data['images'])} items")
            for idx, item in enumerate(response_data["images"]):
                try:
                    print(f"Procesando item {idx}: {item}")
                    cat_image = CategorizedImage(**item)
                    categorized_data.append(cat_image)
                    print(f"Item {idx} validado exitosamente: {cat_image}")
                except Exception as e:
                    print(f"Error validando item {idx}: {str(e)}")
                    print(f"Datos del item: {item}")
        else:
            print(f"Estructura de respuesta inesperada: {response_data}")
            return {
                "characters": [],
                "objects": [],
                "scenarios": [],
                "logos": [],
                "uncategorized": [
                    {"url": url, "description": "No categorizado"}
                    for url in image_urls
                ]
            }

        print(f"Total de imágenes categorizadas: {len(categorized_data)}")


        # Organizar resultados por categoría
        result = {
            "characters": [],
            "objects": [],
            "scenarios": [],
            "logos": [],
            "uncategorized": []
        }

        print(f"Iniciando organización de {len(categorized_data)} imágenes")
        for item in categorized_data:
            print(f"Procesando: category={item.category}, index={item.index}, name={item.name}")
            category = item.category.lower()
            image_url = image_urls[item.index] if item.index < len(image_urls) else None

            if not image_url:
                print(f"⚠️ No se encontró URL para índice {item.index}")
                continue

            entry = {
                "url": image_url,
                "name": item.name,
                "description": item.description
            }

            if category == "character":
                result["characters"].append(entry)
                print(f"✅ Agregado a characters: {item.name}")
            elif category == "object":
                result["objects"].append(entry)
                print(f"✅ Agregado a objects: {item.name}")
            elif category == "scenario":
                result["scenarios"].append(entry)
                print(f"✅ Agregado a scenarios: {item.name}")
            elif category == "logo":
                result["logos"].append(entry)
                print(f"✅ Agregado a logos: {item.name}")
            else:
                result["uncategorized"].append(entry)
                print(f"✅ Agregado a uncategorized: {item.name}")

        print(f"📊 Resultado final - characters: {len(result['characters'])}, objects: {len(result['objects'])}, scenarios: {len(result['scenarios'])}, logos: {len(result['logos'])}, uncategorized: {len(result['uncategorized'])}")
        return result

    except json.JSONDecodeError as e:
        print(f"Error parsing GPT response: {e}")
        # Si falla el parsing, devolver todas como uncategorized
        return {
            "characters": [],
            "objects": [],
            "scenarios": [],
            "logos": [],
            "uncategorized": [
                {"url": url, "description": "No categorizado - error de parseo"}
                for url in image_urls
            ]
        }
    except Exception as e:
        print(f"Error categorizing images: {str(e)}")
        import traceback
        traceback.print_exc()
        # En lugar de lanzar excepción, devolver uncategorized
        return {
            "characters": [],
            "objects": [],
            "scenarios": [],
            "logos": [],
            "uncategorized": [
                {"url": url, "description": "No categorizado - error en procesamiento"}
                for url in image_urls
            ]
        }

