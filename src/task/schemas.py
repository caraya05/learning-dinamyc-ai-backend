from pydantic import BaseModel, Field


class TaskRevokeResponse(BaseModel):
    """Schema para la respuesta de revoke_task"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo del resultado de la operación")
    terminated: bool = Field(..., description="Indica si la tarea fue terminada forzosamente")
