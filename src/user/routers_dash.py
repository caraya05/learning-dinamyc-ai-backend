"""
Router para Dashboard de Usuarios (_dash)

Proporciona endpoints agregados que devuelven toda la información necesaria
para construir un dashboard en una sola petición.

Endpoints:
- GET /user/dashboard/summary - Resumen del dashboard del usuario autenticado
- GET /user/dashboard/global/summary - Listado detallado de todos los usuarios (admin)
- GET /user/dashboard/{user_id}/summary - Resumen del dashboard de un usuario específico
- POST /user/dashboard/batch - Resumen personalizado con widgets específicos

IMPORTANTE: Las rutas más específicas deben ir antes que las genéricas.
            /global/summary debe ir antes de /{user_id}/summary
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.security import HTTPAuthorizationCredentials

from auth.auth import auth
from auth.utils import auth_schema

from user.services_dash import (
    get_all_users_detailed_service,
    get_global_kpis_service,
    get_user_dashboard_summary_service,
    get_waitlist_users_export_service,
    activate_user_service,
    change_user_plan_type_service,
)




router = APIRouter(prefix="/user/dashboard", tags=["User Dashboard"])



# ============================================================================
# 2. GET /global/summary - Listado de todos los usuarios (DEBE IR ANTES DE /{user_id})
# ============================================================================

@router.get(
    "/global/summary",
    status_code=status.HTTP_200_OK,
    summary="Obtener listado detallado de todos los usuarios",
    description="""
    Obtiene un listado detallado de TODOS los usuarios del sistema con sus KPIs individuales.
    
    Ideal para una vista de administración con tabla/grid de usuarios.
    
    **Parámetros de búsqueda y filtrado:**
    - `search`: Buscar por nombre de usuario o email (búsqueda parcial)
    - `is_preview`: Filtrar solo usuarios en preview (True) o solo en waitlist (False)
    
    Incluye por usuario:
    - Información básica (id, username, email, foto, estado)
    - Plan: Plan del usuario (individual o team)
    - Rol en team: Rol del usuario en el team (owner, admin, creator, viewer)
    - Es dueño del team: Si el usuario es dueño del team
    - KPIs: estrellas, juegos creados, intentos de creación
    - Fechas: creación y última actualización
    - Roles: superuser, staff
    - Estado de preview (is_preview)
    """,
)
async def get_global_users_list(
    skip: int = Query(0, ge=0, description="Número de usuarios a saltar (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Límite de usuarios por página (1-100)"),
    search: Optional[str] = Query(None, description="Buscar por nombre de usuario o email"),
    is_preview: Optional[bool] = Query(None, description="Filtrar por is_preview (True/False)"),
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para obtener listado detallado de TODOS los usuarios.

    Requiere autenticación. Idealmente, solo administradores deben acceder.

    Parámetros de paginación:
    - skip: número de usuarios a saltar (default: 0)
    - limit: usuarios por página (default: 10, máximo: 100)

    Parámetros de búsqueda y filtrado:
    - search: Busca por nombre de usuario o email (búsqueda parcial, case-insensitive)
    - is_preview: Filtra por estado de preview (True = usuarios en preview, False = usuarios en waitlist)
    """
    try:
        # Verificar que el usuario sea administrador
        if not user_db.get("is_superuser") and not user_db.get("is_staff"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden acceder a este endpoint"
            )

        result = await get_all_users_detailed_service(
            skip=skip,
            limit=limit,
            search=search,
            is_preview=is_preview,
        )

        return {"data": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener listado de usuarios: {str(e)}"
        )


# ============================================================================
# 3. GET /global/kpis - KPIs globales agregados del sistema
# ============================================================================

@router.get(
    "/global/kpis",
    status_code=status.HTTP_200_OK,
    summary="Obtener KPIs globales agregados del sistema",
    description="""
    Obtiene los KPIs globales agregados de todo el sistema.
    
    Devuelve:
    - Total de estrellas en el sistema
    - Cantidad de usuarios activos
    - Total de usuarios registrados
    - Series creadas en el período
    - Analíticas registradas en el período
    - Usuarios únicos que crearon series
    
    Series de tiempo mensual:
    - Series creadas por mes
    - Usuarios creadores por mes
    - Analíticas registradas por mes
    """,
)
async def get_global_kpis(
    from_date: Optional[str] = Query(
        None,
        example="2026-01-01",
        description="Fecha de inicio (YYYY-MM-DD). Por defecto: últimos 30 días"
    ),
    to_date: Optional[str] = Query(
        None,
        example="2026-02-01",
        description="Fecha de fin (YYYY-MM-DD). Por defecto: hoy"
    ),
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para obtener KPIs globales del sistema.

    Requiere autenticación JWT.

    **KPIs Devueltos:**
    - `total_stars`: Total de estrellas en el sistema
    - `active_users`: Cantidad de usuarios activos
    - `total_users`: Total de usuarios registrados
    - `users_percentage`: Porcentaje de usuarios activos
    - `series_created`: Series creadas en el período
    - `analytics_registered`: Analíticas registradas en el período
    - `unique_creators`: Usuarios únicos que crearon series en el período

    **Series de Tiempo (por mes):**
    - Series creadas por mes
    - Usuarios creadores por mes
    - Analíticas registradas por mes
    """
    try:
        result = await get_global_kpis_service(from_date=from_date, to_date=to_date)
        return {"data": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener KPIs globales: {str(e)}"
        )



# ============================================================================
# 4. GET /{user_id}/summary - Dashboard de usuario específico (DEBE IR DESPUÉS DE /global)
# ============================================================================

@router.get(
    "/{user_id}/summary",
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen del dashboard de un usuario específico",
    description="""
    Obtiene el resumen agregado del dashboard para un usuario específico.
    
    **Información del usuario:**
    - ID, username, email, estado activo
    - Plan: individual o team
    - Rol en el team (si aplica): owner, admin, creator, viewer
    - Si es dueño del team
    - Lista de miembros del team (si aplica)
    
    **Métricas devueltas:**
    - Cantidad de historias creadas (series)
    - Cantidad de vistas (analíticas)
    - Cantidad de analíticas completadas
    - Stars utilizadas (series * 10)
    
    **Series de tiempo por mes:**
    - Vistas por mes
    - Historias creadas por mes
    - Stars consumidas por mes
    
    **Normalmente utilizado por:**
    - Administradores que necesitan ver el dashboard de otros usuarios
    - Análisis de datos de usuarios específicos
    """,
)
async def get_user_dashboard_summary_by_id(
    user_id: str,
    from_date: Optional[str] = Query(
        None,
        example="2026-01-01",
        description="Fecha de inicio (YYYY-MM-DD)"
    ),
    to_date: Optional[str] = Query(
        None,
        example="2026-02-01",
        description="Fecha de fin (YYYY-MM-DD)"
    ),
    timezone: str = Query(
        "UTC",
        example="America/Bogota",
        description="Zona horaria para cortes de fecha"
    ),
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para obtener el dashboard de un usuario específico.

    Requiere autenticación JWT. Idealmente, el usuario autenticado debe ser
    administrador o ser el propietario del user_id.
    """
    try:
        dashboard = await get_user_dashboard_summary_service(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            timezone=timezone,
        )

        return {"data": dashboard}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al obtener el dashboard: {str(e)}"
        )



# ============================================================================
# 6. GET /export/waitlist - Descargar Excel con usuarios en lista de espera
# ============================================================================

@router.get(
    "/export/waitlist",
    status_code=status.HTTP_200_OK,
    summary="Descargar Excel con usuarios en lista de espera",
    description="""
    Descarga un archivo Excel con todos los usuarios en lista de espera (is_preview = False).
    
    El Excel incluye:
    - Username: Nombre de usuario
    - Email: Correo electrónico
    - Plan: Plan del usuario (individual o team)
    - Rol en team: Rol del usuario en el team (si aplica)
    - Es dueño del team: Si el usuario es dueño del team
    - Created At: Fecha de creación de la cuenta
    
    Solo administradores pueden acceder a este endpoint.
    """,
)
async def export_waitlist_users_excel(
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para descargar Excel con usuarios en lista de espera.

    Requiere autenticación JWT. Solo administradores pueden acceder.
    """
    try:
        # Verificar que el usuario sea administrador
        if not user_db.get("is_superuser") and not user_db.get("is_staff"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden acceder a este endpoint"
            )

        # Obtener datos de usuarios en lista de espera
        users_data = await get_waitlist_users_export_service()

        # Generar Excel
        from io import BytesIO
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        # Crear workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Waitlist Users"

        # Encabezados
        headers = ["Username", "Email", "Plan", "Team Role", "Is Team Owner", "Created At"]
        ws.append(headers)

        # Formato de encabezados
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Agregar datos
        for user in users_data:
            created_at_str = user["created_at"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(user["created_at"], "strftime") else str(user["created_at"])
            ws.append([
                user["username"],
                user["email"],
                user.get("plan_type", "individual"),
                user.get("team_role", ""),
                str(user.get("is_team_owner", False)),
                created_at_str,
            ])

        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 20

        # Guardar en BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        # Retornar como archivo descargable
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([excel_file.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=waitlist_users.xlsx"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in export_waitlist_users_excel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al descargar Excel: {str(e)}"
        )


# ============================================================================
# 7. POST /recharge - Recargar estrellas a un usuario
# ============================================================================

@router.post(
    "/recharge",
    status_code=status.HTTP_200_OK,
    summary="Recargar estrellas a un usuario",
    description="""
    Recarga estrellas a un usuario específico.
    
    Proceso:
    1. Valida que el usuario exista
    2. Crea un registro en colección 'star_recharge' con:
       - user_id
       - username
       - email
       - stars_recharged (cantidad)
       - stars_before (saldo anterior)
       - stars_after (saldo actualizado)
       - created_at (fecha de la recarga)
       - status (completed)
    3. Actualiza el saldo de estrellas del usuario
    4. Devuelve registro de recarga e información del usuario actualizado
    
    Solo administradores pueden recargar estrellas.
    """,
)
async def recharge_user_stars(
    user_id: str = Query(..., example="507f1f77bcf86cd799439011", description="ID del usuario"),
    stars_amount: float = Query(..., gt=0, example=100.0, description="Cantidad de estrellas a recargar (debe ser > 0)"),
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para recargar estrellas a un usuario.

    Requiere autenticación JWT. Solo administradores pueden acceder.

    Parámetros Query:
    - user_id: ID del usuario al que recargar estrellas
    - stars_amount: Cantidad de estrellas a recargar (debe ser > 0)
    """
    try:
        # Verificar que el usuario sea administrador
        if not user_db.get("is_superuser") and not user_db.get("is_staff"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden recargar estrellas"
            )

        from user.services_dash import recharge_user_stars_service
        result = await recharge_user_stars_service(
            user_id=user_id,
            stars_amount=stars_amount,
        )

        return {
            "data": result,
            "message": "Estrellas recargadas exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al recargar estrellas: {str(e)}"
        )


# ============================================================================
# 8. POST /activate/{user_id} - Activar usuario (cambiar is_preview a True)
# ============================================================================

@router.post(
    "/activate/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Activar usuario",
    description="""
    Activa un usuario cambiando su estado de `is_preview` a `True`.
    
    Esto permite que usuarios que estaban en waitlist pasen a tener acceso al sistema.
    
    Requiere:
    - Autenticación (JWT)
    - Permiso de administrador (is_superuser=True o is_staff=True)
    - ID de usuario válido (formato MongoDB ObjectId)
    """,
)
async def activate_user(
    user_id: str = Path(..., description="ID del usuario a activar"),
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para activar un usuario.

    Cambia el estado de `is_preview` a `True`, permitiendo que el usuario acceda al sistema.

    **Respuesta exitosa:**
    ```json
    {
        "data": {
            "user_id": "507f1f77bcf86cd799439011",
            "username": "juan_perez",
            "email": "juan@example.com",
            "is_preview": true,
            "created_at": "2025-12-01T10:30:00",
            "activated_at": "2026-03-12T15:45:30",
            "message": "Usuario activado exitosamente"
        },
        "message": "Usuario activado exitosamente"
    }
    ```
    """
    try:
        # Verificar que el usuario sea administrador
        if not user_db.get("is_superuser") and not user_db.get("is_staff"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden activar usuarios"
            )

        result = await activate_user_service(user_id=user_id)

        return {
            "data": result,
            "message": "Usuario activado exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al activar usuario: {str(e)}"
        )


# ============================================================================
# Cambiar tipo de plan del usuario (individual ↔ team)
# ============================================================================

@router.patch(
    "/{user_id}/plan-type",
    status_code=status.HTTP_200_OK,
    summary="Cambiar tipo de plan del usuario",
    description="""
    Cambia el tipo de plan del usuario entre 'individual' y 'team'.
    
    **Cambio de individual a team:**
    - Crea un nuevo team con el nombre del usuario
    - El usuario se asigna como dueño y único miembro del team
    - El team se crea con is_active = true
    
    **Cambio de team a individual:**
    - Desactiva el team actual del usuario (is_active = false)
    - Se eliminan los datos de team del usuario
    
    **Solo administradores pueden realizar este cambio.**
    """,
)
async def change_user_plan_type(
    user_id: str = Path(..., description="ID del usuario"),
    new_plan_type: str = Query(..., description="Nuevo tipo de plan: 'individual' o 'team'"),
    user_db: dict = Depends(auth),
    token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    Endpoint para cambiar el tipo de plan de un usuario.

    Requiere autenticación y permisos de administrador.

    Parámetros:
    - user_id: ID del usuario cuyo plan se desea cambiar
    - new_plan_type: Tipo de plan destino ('individual' o 'team')
    """
    try:
        # Verificar que el usuario sea administrador
        if not user_db.get("is_superuser") and not user_db.get("is_staff"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden cambiar el tipo de plan"
            )

        result = await change_user_plan_type_service(
            user_id=user_id,
            new_plan_type=new_plan_type
        )

        return {
            "data": result,
            "message": f"Plan cambiado a '{new_plan_type}' exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al cambiar el tipo de plan: {str(e)}"
        )


