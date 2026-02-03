#!/usr/bin/env python3
"""
Script para verificar que el audio se actualizó correctamente en MongoDB
después de hacer una petición PATCH a los endpoints de audio.

Uso:
    python3 verify_audio_update.py <state_glic_id> <audio_url> <interaction_index> <dialog_index>

Ejemplo:
    python3 verify_audio_update.py "69781923bd767a9af08a7496" "https://storage.googleapis.com/qwestar/..." 0 0
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from core.database import db
from bson import ObjectId
import asyncio
import json


async def verify_audio_update(state_glic_id: str, audio_url: str, interaction_index: int, dialog_index: int):
    """
    Verifica que el audio se actualizó correctamente en state_glic.
    Comprueba que la URL guardada en la BD coincide con la URL subida.

    Args:
        state_glic_id: ID del documento state_glic
        audio_url: URL de audio que se subió (para comparar)
        interaction_index: Índice de la interacción
        dialog_index: Índice del diálogo
    """

    try:
        # 1. Buscar el documento state_glic
        print(f"\n🔍 Buscando state_glic con ID: {state_glic_id}")
        state_glic = await db['state_glic'].find_one({
            '_id': ObjectId(state_glic_id)
        })

        if not state_glic:
            print("❌ No se encontró el documento state_glic")
            return False

        print("✅ Documento encontrado")

        # 2. Verificar que la interacción existe
        interactions = state_glic.get('data', {}).get('interaction', [])
        if interaction_index >= len(interactions):
            print(f"❌ Índice de interacción {interaction_index} fuera de rango (total: {len(interactions)})")
            return False

        interaction = interactions[interaction_index]
        print(f"✅ Interacción {interaction_index} encontrada")

        # 3. Verificar que el diálogo existe
        conversation = interaction.get('conversation', [])
        if dialog_index >= len(conversation):
            print(f"❌ Índice de diálogo {dialog_index} fuera de rango (total: {len(conversation)})")
            return False

        dialog = conversation[dialog_index]
        print(f"✅ Diálogo {dialog_index} encontrado")

        # 4. Verificar que los campos de audio existen y están actualizados
        print("\n📊 VERIFICACIÓN DE CAMPOS DE AUDIO:")
        print("=" * 70)

        audio = dialog.get('audio')
        audio_mp3 = dialog.get('audio_mp3')

        print(f"\n🔗 URL SUBIDA (esperada):")
        print(f"   {audio_url}")

        if not audio:
            print("\n❌ Campo 'audio' está vacío en BD")
            return False
        else:
            print(f"\n✅ Campo 'audio' en BD:")
            print(f"   {audio}")

        if not audio_mp3:
            print("\n❌ Campo 'audio_mp3' está vacío en BD")
            return False
        else:
            print(f"\n✅ Campo 'audio_mp3' en BD:")
            print(f"   {audio_mp3}")

        # 5. ⭐ VERIFICAR QUE LA URL GUARDADA COINCIDE CON LA URL SUBIDA
        print("\n" + "=" * 70)
        print("🔍 COMPARACIÓN DE URLs:")
        print("=" * 70)

        if audio == audio_url:
            print("✅ Campo 'audio' COINCIDE con URL subida")
        else:
            print("❌ Campo 'audio' NO coincide con URL subida")
            print(f"   Esperado: {audio_url}")
            print(f"   Obtenido: {audio}")
            return False

        if audio_mp3 == audio_url:
            print("✅ Campo 'audio_mp3' COINCIDE con URL subida")
        else:
            print("❌ Campo 'audio_mp3' NO coincide con URL subida")
            print(f"   Esperado: {audio_url}")
            print(f"   Obtenido: {audio_mp3}")
            return False

        # 6. Verificar que ambos campos tienen la misma URL
        if audio == audio_mp3:
            print("✅ Ambos campos tienen la misma URL (sincronizados)")
        else:
            print("⚠️  ADVERTENCIA: Los campos tienen URLs diferentes")
            return False

        # 7. Verificar que es una URL de Google Cloud Storage válida
        if "storage.googleapis.com/qwestar" in audio:
            print("✅ URL es de Google Cloud Storage (válida)")
        else:
            print("❌ URL no es de Google Cloud Storage")
            return False

        # 8. Verificar auditoría
        print("\n📋 AUDITORÍA:")
        print("=" * 70)
        updated_at = state_glic.get('updated_at')
        updated_by = state_glic.get('updated_by')

        if updated_at:
            print(f"✅ updated_at: {updated_at}")
        else:
            print("❌ Campo 'updated_at' no registrado")

        if updated_by:
            print(f"✅ updated_by: {updated_by}")
        else:
            print("❌ Campo 'updated_by' no registrado")

        # 9. Mostrar datos completos del diálogo
        print("\n📝 DATOS COMPLETOS DEL DIÁLOGO:")
        print("=" * 70)
        print(json.dumps(dialog, indent=2, default=str))

        print("\n" + "=" * 70)
        print("✅ VERIFICACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print("\n✨ El audio se actualizó correctamente en la base de datos")
        print("✨ La URL guardada coincide con la URL subida")
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("❌ Faltan argumentos")
        print("\nUso: python3 verify_audio_update.py <state_glic_id> <audio_url> <interaction_index> <dialog_index>")
        print("\nEjemplo:")
        print("  python3 verify_audio_update.py \\")
        print("    '69781923bd767a9af08a7496' \\")
        print("    'https://storage.googleapis.com/qwestar/characters/69781924bd767a9af08a7499/audios/abc123_dialog.mp3' \\")
        print("    0 0")
        sys.exit(1)

    state_glic_id = sys.argv[1]
    audio_url = sys.argv[2]
    interaction_index = int(sys.argv[3])
    dialog_index = int(sys.argv[4])

    success = asyncio.run(verify_audio_update(state_glic_id, audio_url, interaction_index, dialog_index))
    sys.exit(0 if success else 1)
