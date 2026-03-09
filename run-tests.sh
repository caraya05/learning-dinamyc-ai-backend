#!/bin/bash
# Script para ejecutar tests del módulo analytics

set -e

PROJECT_ROOT="/Users/ishop/PycharmProjects/ColombiaGames/qwestar-ai-backend"
ANALYTICS_DIR="$PROJECT_ROOT/src/analytics"

echo "🚀 Ejecutando tests de Analytics..."
echo ""

# Opción por defecto: todos los tests con verbose
if [ $# -eq 0 ]; then
    echo "📊 Ejecutando todos los tests unitarios..."
    pytest "$ANALYTICS_DIR/tests_analytics.py" -v --tb=short

elif [ "$1" = "coverage" ]; then
    echo "📈 Ejecutando tests con coverage..."
    pytest "$ANALYTICS_DIR/tests_analytics.py" --cov=analytics --cov-report=html
    echo "✅ Coverage report generado en: htmlcov/index.html"

elif [ "$1" = "integration" ]; then
    echo "🔗 Ejecutando tests de integración..."
    pytest "$ANALYTICS_DIR/tests_integration.py" -v --tb=short

elif [ "$1" = "all" ]; then
    echo "📝 Ejecutando todos los tests (unitarios + integración)..."
    pytest "$ANALYTICS_DIR" -v --tb=short

elif [ "$1" = "watch" ]; then
    echo "👁️  Modo watch - Ejecutando tests al detectar cambios..."
    ptw "$ANALYTICS_DIR/tests_analytics.py" -- -v

elif [ "$1" = "quick" ]; then
    echo "⚡ Ejecución rápida sin verbose..."
    pytest "$ANALYTICS_DIR/tests_analytics.py" -q

elif [ "$1" = "schemas" ]; then
    echo "🔍 Ejecutando solo tests de schemas..."
    pytest "$ANALYTICS_DIR/tests_analytics.py::TestAnalyticCreateSchema" -v

elif [ "$1" = "exceptions" ]; then
    echo "❌ Ejecutando solo tests de excepciones..."
    pytest "$ANALYTICS_DIR/tests_analytics.py::TestExceptions" -v

elif [ "$1" = "services" ]; then
    echo "⚙️  Ejecutando solo tests de servicios..."
    pytest "$ANALYTICS_DIR/tests_analytics.py::TestCreateAnalyticService" -v
    pytest "$ANALYTICS_DIR/tests_analytics.py::TestGetAnalyticsByUserService" -v
    pytest "$ANALYTICS_DIR/tests_analytics.py::TestQueryAnalyticsService" -v
    pytest "$ANALYTICS_DIR/tests_analytics.py::TestUpdateSessionComplete" -v

else
    echo "Uso: $0 [opción]"
    echo ""
    echo "Opciones:"
    echo "  (sin opción)  - Ejecutar todos los tests unitarios"
    echo "  coverage      - Ejecutar tests con reporte de cobertura"
    echo "  integration   - Ejecutar tests de integración"
    echo "  all           - Ejecutar unitarios + integración"
    echo "  watch         - Modo watch (reejecutar al cambiar archivos)"
    echo "  quick         - Ejecución rápida sin output verboso"
    echo "  schemas       - Solo tests de schemas"
    echo "  exceptions    - Solo tests de excepciones"
    echo "  services      - Solo tests de servicios"
    echo ""
    echo "Ejemplos:"
    echo "  $0 coverage     - Ver cobertura"
    echo "  $0 watch        - Modo desarrollo (watch)"
    echo "  $0 all          - Todo los tests"
    exit 1
fi

echo ""
echo "✅ Tests completados!"

