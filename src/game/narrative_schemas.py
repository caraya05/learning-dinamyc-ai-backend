from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from game.narrative_templates import TemplateType, InteractionType


class SchemaCreateNarrativeTemplate(BaseModel):
    name: str = Field(..., example="Mi Template de Aprendizaje")
    template_type: TemplateType = Field(..., example=TemplateType.LEARN)
    description: Optional[str] = Field(None, example="Template para enseñar conceptos básicos")
    custom_rules: Optional[Dict[str, Any]] = Field(None, example={"difficulty": "beginner"})


class SchemaTemplateSceneConfig(BaseModel):
    scene_name: str = Field(..., example="Escena de Introducción")
    interaction_type: InteractionType = Field(..., example=InteractionType.TWO_WAY)
    character_name: Optional[str] = Field(None, example="Profesor Virtual")
    location_name: Optional[str] = Field(None, example="Aula Virtual")
    min_options: int = Field(default=2, example=2)
    max_options: int = Field(default=4, example=4)


class SchemaTemplateEventConfig(BaseModel):
    event_name: str = Field(..., example="Evento de Transición")
    condition_type: Optional[str] = Field("always", example="correct_answer")
    description: Optional[str] = Field(None, example="Evento que conecta escenas")


class SchemaGenerateFromScript(BaseModel):
    script: str = Field(..., description="Script base para generar el template")
    template_type: TemplateType = Field(..., description="Tipo de template a generar")
    title: str = Field(..., example="Mi Historia Interactiva")
    num_scenes: int = Field(default=3, example=3, description="Número de escenas (A, B, C)")
    category: str = Field(..., example="Learning", description="Categoría del contenido")


class SchemaExtractTemplateElements(BaseModel):
    template_id: str = Field(..., example="template_123")
    extract_characters: bool = Field(default=True)
    extract_locations: bool = Field(default=True)
    extract_events: bool = Field(default=True)
    extract_scenes: bool = Field(default=True)


class SchemaTemplateResponse(BaseModel):
    template_id: str
    name: str
    template_type: TemplateType
    structure: Dict[str, Any]
    rules: Dict[str, Any]
    created_at: str
    status: str = Field(default="created")


class SchemaTemplateExtractionResult(BaseModel):
    template_id: str
    characters: List[Dict[str, Any]] = Field(default_factory=list)
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    extraction_summary: Dict[str, Any]


class SchemaTemplateGenerationProgress(BaseModel):
    template_id: str
    status: str  # "processing", "completed", "error"
    progress: int  # 0-100
    progress_text: str
    current_step: str
    estimated_time_remaining: Optional[int] = None  # segundos
