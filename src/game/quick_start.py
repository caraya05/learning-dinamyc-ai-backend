#!/usr/bin/env python3
"""
QUICK START - API de Actualización de Textos
=============================================

Este script proporciona ejemplos rápidos de cómo usar cada uno de los 9 endpoints.

Requiere:
  - requests library (pip install requests)
  - Token JWT válido
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
TOKEN = "tu_token_jwt_aqui"  # Reemplazar con token real

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def print_section(title):
    """Imprime un encabezado de sección"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_request(method, endpoint, data=None):
    """Imprime detalles de la request"""
    print(f"📤 {method} {endpoint}")
    if data:
        print(f"   Payload: {json.dumps(data, indent=2)}")


def print_response(response):
    """Imprime detalles de la response"""
    print(f"📥 Status: {response.status_code}")
    try:
        print(f"   Response: {json.dumps(response.json(), indent=2, default=str)}")
    except:
        print(f"   Response: {response.text}")


# ============================================================================
# 1. ACTUALIZAR TÍTULO DEL JUEGO
# ============================================================================

def example_1_update_game_title():
    """Ejemplo 1: Actualizar título del juego"""
    print_section("1. Actualizar Título del Juego")

    game_id = "507f1f77bcf86cd799439011"  # Reemplazar con ID real
    endpoint = f"{BASE_URL}/v1/api/game/{game_id}/title"
    data = {
        "title": "La Aventura Épica: Parte 2"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 2. ACTUALIZAR DATOS DE PERSONAJE
# ============================================================================

def example_2_update_character_data():
    """Ejemplo 2: Actualizar datos de personaje"""
    print_section("2. Actualizar Datos de Personaje")

    character_id = "507f1f77bcf86cd799439012"  # Reemplazar con ID real
    state_id = "state_001"
    endpoint = f"{BASE_URL}/v1/api/character/{character_id}/state/{state_id}"
    data = {
        "name": "Héroe Legendario",
        "description": "Un valiente guerrero con poderes mágicos extraordinarios"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 3. ACTUALIZAR DATOS DE LOCACIÓN
# ============================================================================

def example_3_update_location_data():
    """Ejemplo 3: Actualizar datos de locación"""
    print_section("3. Actualizar Datos de Locación")

    location_id = "507f1f77bcf86cd799439013"  # Reemplazar con ID real
    state_id = "state_001"
    endpoint = f"{BASE_URL}/v1/api/location/{location_id}/state/{state_id}"
    data = {
        "title": "La Caverna Mística",
        "description": "Una caverna antigua llena de cristales brillantes y magia ancestral"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 4. ACTUALIZAR DIÁLOGO DE INTERACCIÓN
# ============================================================================

def example_4_update_interaction_dialog():
    """Ejemplo 4: Actualizar diálogo de interacción"""
    print_section("4. Actualizar Diálogo de Interacción")

    character_id = "507f1f77bcf86cd799439012"  # Reemplazar con ID real
    state_id = "state_001"
    interaction_index = 0
    dialog_index = 0
    endpoint = f"{BASE_URL}/v1/api/character/{character_id}/state/{state_id}/interaction/{interaction_index}/dialog/{dialog_index}"
    data = {
        "dialog": "¡Bienvenido, aventurero! He estado esperando tu llegada."
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 5. ACTUALIZAR PREGUNTA DE OPCIÓN
# ============================================================================

def example_5_update_option_question():
    """Ejemplo 5: Actualizar pregunta de opción"""
    print_section("5. Actualizar Pregunta de Opción")

    character_id = "507f1f77bcf86cd799439012"  # Reemplazar con ID real
    state_id = "state_001"
    interaction_index = 0
    option_index = 0
    endpoint = f"{BASE_URL}/v1/api/character/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question"
    data = {
        "dialog": "¿Cuál será tu próximo movimiento?"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 6. ACTUALIZAR RESPUESTA DE OPCIÓN
# ============================================================================

def example_6_update_option_answer():
    """Ejemplo 6: Actualizar respuesta de opción"""
    print_section("6. Actualizar Respuesta de Opción")

    character_id = "507f1f77bcf86cd799439012"  # Reemplazar con ID real
    state_id = "state_001"
    interaction_index = 0
    option_index = 0
    endpoint = f"{BASE_URL}/v1/api/character/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer"
    data = {
        "dialog": "Entiendo, continuaré con cautela."
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 7. ACTUALIZAR GUÍA DE OPCIÓN
# ============================================================================

def example_7_update_option_guideline():
    """Ejemplo 7: Actualizar guía de opción"""
    print_section("7. Actualizar Guía de Opción")

    character_id = "507f1f77bcf86cd799439012"  # Reemplazar con ID real
    state_id = "state_001"
    interaction_index = 0
    option_index = 0
    endpoint = f"{BASE_URL}/v1/api/character/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/guideline"
    data = {
        "guideline": "El jugador debe demostrar que ha aprendido de los eventos anteriores"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 8. ACTUALIZAR DATOS DE EVENTO
# ============================================================================

def example_8_update_event():
    """Ejemplo 8: Actualizar datos de evento"""
    print_section("8. Actualizar Datos de Evento")

    event_id = "507f1f77bcf86cd799439014"  # Reemplazar con ID real
    endpoint = f"{BASE_URL}/v1/api/event/{event_id}"
    data = {
        "text_image": "El cielo se oscurece...",
        "description": "Una tormenta mágica se aproxima al horizonte",
        "prompt_user_text": "Prepárate para lo que viene"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# 9. ACTUALIZAR DIÁLOGO DE PREGUNTA ABIERTA
# ============================================================================

def example_9_update_open_question_dialog():
    """Ejemplo 9: Actualizar diálogo de pregunta abierta"""
    print_section("9. Actualizar Diálogo de Pregunta Abierta")

    character_id = "507f1f77bcf86cd799439012"  # Reemplazar con ID real
    state_id = "state_001"
    interaction_index = 0
    question_index = 0
    endpoint = f"{BASE_URL}/v1/api/character/{character_id}/state/{state_id}/interaction/{interaction_index}/question/{question_index}"
    data = {
        "dialog": "¿Cuáles son tus pensamientos más profundos sobre esta situación?"
    }

    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    return response


# ============================================================================
# PRUEBAS DE ERROR
# ============================================================================

def example_error_cases():
    """Ejemplos de casos de error"""
    print_section("Casos de Error")

    # 404 - Game not found
    print("\n--- Error 404: Game Not Found ---")
    endpoint = f"{BASE_URL}/v1/api/game/invalid_id/title"
    data = {"title": "Nuevo título"}
    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    # 400 - Validation error (empty string)
    print("\n--- Error 400: Validation Error (Empty String) ---")
    game_id = "507f1f77bcf86cd799439011"
    endpoint = f"{BASE_URL}/v1/api/game/{game_id}/title"
    data = {"title": ""}
    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data, headers=HEADERS)
    print_response(response)

    # 403 - Permission denied (no token)
    print("\n--- Error 403: Permission Denied (No Token) ---")
    endpoint = f"{BASE_URL}/v1/api/game/{game_id}/title"
    data = {"title": "Nuevo título"}
    print_request("PATCH", endpoint, data)
    response = requests.patch(endpoint, json=data)  # Sin headers
    print_response(response)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "="*70)
    print("  API DE ACTUALIZACIÓN DE TEXTOS - EJEMPLOS DE USO")
    print("="*70)
    print("\n⚠️  IMPORTANTE:")
    print("   1. Reemplaza los IDs con IDs reales de tu base de datos")
    print("   2. Reemplaza TOKEN con tu token JWT válido")
    print("   3. Asegúrate de que el servidor esté ejecutándose en localhost:8000")
    print("   4. Cada endpoint requiere que tengas permisos de edición")

    # Uncomment para ejecutar ejemplos individuales
    # example_1_update_game_title()
    # example_2_update_character_data()
    # example_3_update_location_data()
    # example_4_update_interaction_dialog()
    # example_5_update_option_question()
    # example_6_update_option_answer()
    # example_7_update_option_guideline()
    # example_8_update_event()
    # example_9_update_open_question_dialog()
    # example_error_cases()

    print("\n📝 Para ejecutar ejemplos:")
    print("   python3 src/game/quick_start.py")
    print("\n💡 Descomenta las líneas en main() para ejecutar ejemplos específicos")


if __name__ == "__main__":
    main()
