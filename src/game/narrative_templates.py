from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TemplateType(str, Enum):
    LEARN = "learn"
    EVALUATION = " "
    TRIVIA = "trivia"
    SURVEY = "survey"


class InteractionType(str, Enum):
    TWO_WAY = "2way"
    OPEN_ANSWER = "open_answer"
    MULTIPLE_CHOICE = "multiple"
    OPEN_TALK = "open_talk"


class SceneInteraction(BaseModel):
    interaction_type: InteractionType
    min_options: int = Field(default=2)
    max_options: int = Field(default=4)
    allows_error: bool = Field(default=True)
    error_handling: str = Field(default="continue")  # "continue", "retry", "block"
    response_varies: bool = Field(default=True)  # Si la respuesta del personaje varía según la entrada


class NarrativeScene(BaseModel):
    scene_id: str
    scene_name: str
    interaction: SceneInteraction
    character_id: Optional[str] = None
    location_id: Optional[str] = None
    requires_correct_answer: bool = Field(default=False)


class NarrativeEvent(BaseModel):
    event_id: str
    event_name: str
    from_scene: Optional[str] = None
    to_scene: Optional[str] = None
    is_intro: bool = Field(default=False)
    is_final: bool = Field(default=False)
    condition_type: Optional[str] = None  # "correct_answer", "always", "custom"


class NarrativeTemplate(BaseModel):
    template_id: str
    name: str
    template_type: TemplateType
    description: Optional[str] = None

    # Estructura base
    intro_event: NarrativeEvent
    scenes: List[NarrativeScene]
    transition_events: List[NarrativeEvent]
    final_event: NarrativeEvent

    # Reglas específicas del template
    rules: Dict[str, Any]

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system")


class LearnTemplate(NarrativeTemplate):
    """Template para aprendizaje con interacciones 2-way de 4-6 opciones"""

    def __init__(self, **data):
        if 'template_type' not in data:
            data['template_type'] = TemplateType.LEARN

        if 'rules' not in data:
            data['rules'] = {
                "interaction_range": {"min": 4, "max": 6},
                "interaction_type": "2way",
                "scenes_count": 3,
                "allows_errors": True
            }

        super().__init__(**data)


class EvaluationTemplate(NarrativeTemplate):
    """Template para evaluación con 2-way + OpenAnswer, sin errores"""

    def __init__(self, **data):
        if 'template_type' not in data:
            data['template_type'] = TemplateType.EVALUATION

        if 'rules' not in data:
            data['rules'] = {
                "interaction_range": {"min": 2, "max": 4},
                "interaction_types": ["2way", "open_answer"],
                "scenes_count": 3,
                "allows_errors": False,
                "consistent_response": True  # La respuesta del personaje es siempre igual
            }

        super().__init__(**data)


class TriviaTemplate(NarrativeTemplate):
    """Template para trivia con progresión condicionada a respuestas correctas"""

    def __init__(self, **data):
        if 'template_type' not in data:
            data['template_type'] = TemplateType.TRIVIA

        if 'rules' not in data:
            data['rules'] = {
                "interaction_range": {"min": 2, "max": 4},
                "interaction_types": ["2way", "multiple"],
                "scenes_count": 3,
                "requires_correct_answers": True,
                "blocks_on_error": True,
                "variable_response": True  # Respuesta cambia según acierto/error
            }

        super().__init__(**data)


class SolveTemplate(NarrativeTemplate):
    """Template para resolución de problemas con acceso condicionado al final"""

    def __init__(self, **data):
        if 'template_type' not in data:
            data['template_type'] = TemplateType.SOLVE

        if 'rules' not in data:
            data['rules'] = {
                "interaction_range": {"min": 2, "max": 4},
                "scene_a_interaction": "2way",
                "scene_b_interaction": "2way",
                "scene_c_interaction": ["2way", "open_answer"],
                "scenes_count": 3,
                "requires_solution": True,
                "variable_response": True,
                "conditional_final_access": True
            }

        super().__init__(**data)


class ExpertTemplate(NarrativeTemplate):
    """Template para expertos con conversación abierta"""

    def __init__(self, **data):
        if 'template_type' not in data:
            data['template_type'] = TemplateType.EXPERT

        if 'rules' not in data:
            data['rules'] = {
                "interaction_type": "open_talk",
                "scenes_count": 3,
                "allows_free_conversation": True,
                "consistent_final_response": True  # Respuesta final siempre igual
            }

        super().__init__(**data)
