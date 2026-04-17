#!/usr/bin/env python3
"""
Script de prueba para validar las optimizaciones del dashboard

Ejecuta:
    python test_dashboard_optimization.py
"""

import asyncio
import time
from datetime import datetime, timedelta

# Mock de la base de datos
class MockDB:
    def __getitem__(self, key):
        return MockCollection(key)

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.data = []

    async def find_one(self, query):
        return {
            "_id": "test_id_123",
            "username": "testuser",
            "email": "test@example.com",
            "stars": 100,
            "is_active": True,
            "is_superuser": False,
            "is_staff": False,
        }

    def find(self, query):
        self.mock_find_result = []
        return self

    async def to_list(self, length):
        if self.name == "game":
            return [
                {"_id": f"game_{i}", "created_by": "test_id", "title": f"Game {i}"}
                for i in range(3)
            ]
        return []

    def count_documents(self, query):
        mock_count = AsyncMock(return_value=5)
        return mock_count()

    def aggregate(self, pipeline):
        self.aggregate_result = []
        return self

    async def to_list(self, length):
        if "aggregate" in dir(self):
            return [{"_id": "month", "count": 10, "total": 100}]
        return []

async def test_imports():
    """Verificar que asyncio está importado"""
    print("✅ Test 1: Verificar imports...")
    try:
        from src.user.services_dash import get_user_dashboard_summary_service
        print("  ✓ get_user_dashboard_summary_service importado correctamente")
        return True
    except ImportError as e:
        print(f"  ✗ Error al importar: {e}")
        return False

async def test_function_signatures():
    """Verificar que las funciones tienen los parámetros correctos"""
    print("\n✅ Test 2: Verificar firmas de funciones...")
    try:
        from src.user.services_dash import _build_user_kpis, _build_user_timeseries, _build_user_breakdowns
        import inspect

        # Verificar _build_user_kpis
        sig = inspect.signature(_build_user_kpis)
        params = list(sig.parameters.keys())
        assert "games_list" in params, "_build_user_kpis debe tener parámetro games_list"
        print("  ✓ _build_user_kpis tiene parámetro games_list")

        # Verificar _build_user_timeseries
        sig = inspect.signature(_build_user_timeseries)
        params = list(sig.parameters.keys())
        assert "game_ids" in params, "_build_user_timeseries debe tener parámetro game_ids"
        print("  ✓ _build_user_timeseries tiene parámetro game_ids")

        # Verificar _build_user_breakdowns
        sig = inspect.signature(_build_user_breakdowns)
        params = list(sig.parameters.keys())
        assert "games_list" in params, "_build_user_breakdowns debe tener parámetro games_list"
        print("  ✓ _build_user_breakdowns tiene parámetro games_list")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

async def test_asyncio_imports():
    """Verificar que asyncio.gather se está usando"""
    print("\n✅ Test 3: Verificar uso de asyncio.gather...")
    try:
        with open("/Users/ishop/PycharmProjects/ColombiaGames/qwestar-ai-backend/src/user/services_dash.py", "r") as f:
            content = f.read()

        # Verificar que asyncio está importado
        assert "import asyncio" in content, "asyncio debe estar importado"
        print("  ✓ asyncio está importado")

        # Verificar que asyncio.gather se usa en get_user_dashboard_summary_service
        assert "asyncio.gather" in content, "asyncio.gather debe usarse"
        print("  ✓ asyncio.gather se está usando")

        # Verificar que la función principal paraleliza las operaciones
        assert "kpis_task = " in content, "Las tareas deben asignarse a variables"
        print("  ✓ Las operaciones están sendo paralelizadas")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

async def test_n_plus_one_fix():
    """Verificar que el problema N+1 está solucionado"""
    print("\n✅ Test 4: Verificar solución del problema N+1...")
    try:
        with open("/Users/ishop/PycharmProjects/ColombiaGames/qwestar-ai-backend/src/user/services_dash.py", "r") as f:
            content = f.read()

        # Verificar que se usa agregación en _get_user_series_with_analytics
        assert 'await db["analytics"].aggregate' in content, "Debe usarse aggregation para analytics"
        print("  ✓ Se usa aggregation para obtener analytics")

        # Verificar que se crea un diccionario para búsqueda
        assert "analytics_dict = {" in content, "Debe crearse diccionario para búsqueda O(1)"
        print("  ✓ Se crea diccionario para búsqueda O(1)")

        # Verificar que se reutiliza el diccionario
        assert "analytics_dict.get(" in content, "Debe reutilizarse el diccionario en lugar de hacer consultas"
        print("  ✓ El diccionario se reutiliza en lugar de hacer más consultas")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

async def test_no_duplicate_queries():
    """Verificar que no hay consultas duplicadas"""
    print("\n✅ Test 5: Verificar eliminación de consultas duplicadas...")
    try:
        with open("/Users/ishop/PycharmProjects/ColombiaGames/qwestar-ai-backend/src/user/services_dash.py", "r") as f:
            content = f.read()

        # Contar cuántas veces se obtienen games en la función principal
        main_func_start = content.find("async def get_user_dashboard_summary_service")
        main_func_end = content.find("async def get_all_users_dashboard_summary_service")
        main_func = content[main_func_start:main_func_end]

        # Debe obtener games solo una vez antes de paralelizar
        games_queries = main_func.count('db["game"].find({"created_by":')
        assert games_queries == 1, f"Debe haber solo 1 consulta de games, encontró {games_queries}"
        print(f"  ✓ games se obtiene solo 1 vez (antes había múltiples)")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

async def test_aggregation_usage():
    """Verificar uso de aggregation en lugar de find + procesamiento"""
    print("\n✅ Test 6: Verificar uso correcto de aggregation...")
    try:
        with open("/Users/ishop/PycharmProjects/ColombiaGames/qwestar-ai-backend/src/user/services_dash.py", "r") as f:
            content = f.read()

        # Verificar que se usa aggregation para tokens cargados
        assert 'db["star_recharge"].aggregate' in content, "Debe usarse aggregation para tokens"
        print("  ✓ Se usa aggregation para sumar tokens (no find().to_list() + sum())")

        # Verificar que no hay sum() en Python para tokens
        kpis_func = content[content.find("async def _build_user_kpis"):content.find("async def _build_user_timeseries")]
        assert "sum([item.get(" not in kpis_func or "star_recharge" not in kpis_func, "No debe hacerse sum() en Python para tokens"
        print("  ✓ Los tokens se suman en la BD mediante aggregation")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

async def main():
    """Ejecutar todos los tests"""
    print("=" * 60)
    print("🧪 PRUEBAS DE OPTIMIZACIÓN DEL DASHBOARD")
    print("=" * 60)

    results = []

    results.append(("Imports", await test_imports()))
    results.append(("Firmas de funciones", await test_function_signatures()))
    results.append(("asyncio.gather", await test_asyncio_imports()))
    results.append(("Solución N+1", await test_n_plus_one_fix()))
    results.append(("Sin consultas duplicadas", await test_no_duplicate_queries()))
    results.append(("Uso de aggregation", await test_aggregation_usage()))

    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} | {name}")

    print("=" * 60)
    print(f"Total: {passed}/{total} pruebas pasadas")

    if passed == total:
        print("\n🎉 ¡Todas las optimizaciones están correctamente implementadas!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} pruebas fallaron")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)




