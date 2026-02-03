"""
Schemas para los endpoints de actualización de textos.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============ Game Text Update Schemas ============
class SchemaUpdateGameTitle(BaseModel):
    """Schema para actualizar el título del juego"""
    title: str = Field(..., min_length=1, max_length=200, example="Nuevo título del episodio")


class SchemaGameTitleResponse(BaseModel):
    """Response schema para actualización de título del juego"""
    _id: str
    title: str
    updated_at: datetime


# ============ Character Data Update Schemas ============
class SchemaUpdateCharacterData(BaseModel):
    """Schema para actualizar datos de personaje"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, example="Nuevo nombre del personaje")
    description: Optional[str] = Field(None, min_length=1, example="Nueva descripción del personaje")


class SchemaCharacterStateDataResponse(BaseModel):
    """Response schema para actualización de datos de personaje"""
    _id: str
    updated_at: datetime


# ============ Location Data Update Schemas ============
class SchemaUpdateLocationData(BaseModel):
    """Schema para actualizar datos de locación"""
    title: Optional[str] = Field(None, min_length=1, max_length=100, example="Nuevo nombre de la locación")
    description: Optional[str] = Field(None, min_length=1, example="Nueva descripción de la locación")


class SchemaLocationStateDataResponse(BaseModel):
    """Response schema para actualización de datos de locación"""
    _id: str
    updated_at: datetime


# ============ Dialog Update Schemas ============
class SchemaUpdateDialog(BaseModel):
    """Schema para actualizar un diálogo"""
    dialog: str = Field(..., min_length=1, example="Nuevo texto del diálogo")


class SchemaDialogResponse(BaseModel):
    """Response schema para actualización de diálogo"""
    success: bool
    dialog: dict
    updated_at: datetime


# ============ Option Question Update Schemas ============
class SchemaUpdateOptionQuestion(BaseModel):
    """Schema para actualizar pregunta de opción"""
    dialog: str = Field(..., min_length=1, example="Nueva pregunta de opción")


class SchemaOptionQuestionResponse(BaseModel):
    """Response schema para actualización de pregunta de opción"""
    success: bool
    option: dict
    updated_at: datetime


# ============ Option Answer Update Schemas ============
class SchemaUpdateOptionAnswer(BaseModel):
    """Schema para actualizar respuesta de opción"""
    dialog: str = Field(..., min_length=1, example="Nueva respuesta de opción")


class SchemaOptionAnswerResponse(BaseModel):
    """Response schema para actualización de respuesta de opción"""
    success: bool
    option: dict
    updated_at: datetime


# ============ Option Guideline Update Schemas ============
class SchemaUpdateOptionGuideline(BaseModel):
    """Schema para actualizar guía de opción"""
    guideline: str = Field(..., min_length=1, example="Nueva guía para la respuesta abierta")


class SchemaOptionGuidelineResponse(BaseModel):
    """Response schema para actualización de guía de opción"""
    success: bool
    guideline: str
    updated_at: datetime


# ============ Event Update Schemas ============
class SchemaUpdateEvent(BaseModel):
    """Schema para actualizar datos de evento"""
    text_image: Optional[str] = Field(None, min_length=1, example="Texto que aparece en la imagen del evento")
    description: Optional[str] = Field(None, min_length=1, example="Descripción del evento")
    prompt_user_text: Optional[str] = Field(None, min_length=1, example="Texto adicional para el usuario")


class SchemaEventResponse(BaseModel):
    """Response schema para actualización de evento"""
    _id: str
    text_image: Optional[str]
    description: Optional[str]
    prompt_user_text: Optional[str]
    updated_at: datetime


# ============ Open Question Dialog Update Schemas ============
class SchemaUpdateOpenQuestionDialog(BaseModel):
    """Schema para actualizar diálogo de pregunta abierta"""
    dialog: str = Field(..., min_length=1, example="Nuevo texto de la pregunta")


class SchemaOpenQuestionDialogResponse(BaseModel):
    """Response schema para actualización de diálogo de pregunta abierta"""
    success: bool
    question: dict
    updated_at: datetime


# ============ Error Response Schemas ============
class SchemaErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    error: str
    message: str
    code: str


class SchemaNotFoundError(SchemaErrorResponse):
    """Schema para error 404 - Not Found"""
    error: str = "Not Found"
    code: str = "RESOURCE_NOT_FOUND"


class SchemaValidationError(SchemaErrorResponse):
    """Schema para error 400 - Validation Error"""
    error: str = "Validation Error"
    code: str = "VALIDATION_ERROR"


class SchemaForbiddenError(SchemaErrorResponse):
    """Schema para error 403 - Forbidden"""
    error: str = "Forbidden"
    code: str = "PERMISSION_DENIED"


class SchemaInternalServerError(SchemaErrorResponse):
    """Schema para error 500 - Internal Server Error"""
    error: str = "Internal Server Error"
    code: str = "INTERNAL_ERROR"
