from datetime import datetime
from typing import Optional, Dict, Any

from bson import ObjectId
from pydantic import BaseModel
from pydantic import Field

from character.enums import TypeCharacter
from character.enums import GenderCharacter
from core import PyObjectId


class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")

    class Config:
        json_encoders = {ObjectId: str}


class ResponseModelStr(BaseModel):
    id: str = Field(alias="_id")


class SchemaOption(BaseModel):
    prompt_user_option: str = Field(..., example="prompt_user_option")
    prompt_user_answer: str = Field(..., example="prompt_user_answer")



class SchemaOptionMultiple(BaseModel):
    prompt_user_question: str = Field(..., example="prompt_user_question")
    options: list[SchemaOption] = Field(..., example=[{"key": "value"}])


class SchemaOpenQuestion(BaseModel):
    prompt_user_guideline: str = Field(..., example="prompt_user_question")
    prompt_user_answer: str = Field(..., example="prompt_user_answer")


class SchemaOpenTalk(BaseModel):
    prompt_user_question: str = Field(..., example="prompt_user_dialog")
    prompt_user_guideline: str = Field(..., example="prompt_user_guideline")
    options: list[SchemaOpenQuestion] = Field(..., example=[{"key": "value"}])
    num_interaction: Optional[int] = Field(None, example=1)


class SchemaOpenAnswer(BaseModel):
    prompt_user_question: str = Field(..., example="prompt_user_question")
    options: list[SchemaOpenQuestion] = Field(..., example=[{"key": "value"}])


class SchemaStateData(BaseModel):
    title: str = Field(None, example="Location Title")
    description: Optional[str] = Field(None, example="This is a location description")
    prompt_user: str = Field(None, example="This is a prompt user")
    image: Optional[str] = Field(None, example="image.jpg")
    configuration: Optional[dict] = Field(None, example="")
    connections: Optional[dict] = Field(None, example="")
    sound: Optional[str] = Field(None, example="123")
    is_active: Optional[bool] = Field(None, example=True)
    personalization: Optional[list] = Field(None, example={"key": "value"})


class SchemaStateItem(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[SchemaStateData] = Field(None, example={})


class SchemaDataCharacter(BaseModel):
    name: str = Field(None, example="Character Name")
    description: Optional[str] = Field(None, example="This is a character")
    description_shoulder_up: Optional[str] = Field(None, example="This is a character")
    is_active: bool = Field(default=True, example=True)
    prompt_user: str = Field(None, example="prompt_user")
    body_type: Optional[str] = Field(None, example="body_type")
    genre: Optional[str] = Field(None, example=GenderCharacter.MAN)
    character_type: Optional[str] = Field(None, example="character_type")
    image: Optional[str] = Field(None, example="image.jpg")
    image_reference: Optional[str] = Field(None, example="reference_image.jpg")
    locations_id: Optional[list] = Field(None, example="location_id")
    extra_data: Optional[dict] = Field(None, example="Extra data")
    interaction: Optional[list[dict]] = Field([], example=[{"key": "value"}])
    type: Optional[str] = Field(None, example=TypeCharacter.NPC)
    characteristics: Optional[dict] = Field(None, example={"key": "value"})
    personalization: Optional[list] = Field(None, example={"key": "value"})


class SchemaStateLocation(BaseModel):
    order: Optional[int] = Field(None, example=1)
    state: Optional[str] = Field(None, example="state")
    data: Optional[SchemaDataCharacter] = Field(None, example={})

class ConversationsCharacter(BaseModel):
    id_character: str = Field(..., example="character_id")
    dialog: str = Field(..., example="dialog")
    audio: str = Field(None, example="audio")
    video_url: Optional[str] = Field(None, example="video_url")
    video: Optional[str] = Field(None, example="video")

class ConversationsOptionsCharacter(BaseModel):
    question: ConversationsCharacter = Field(..., example="question")
    answer: ConversationsCharacter = Field(..., example="answer")
    guideline: Optional[str] = Field(None, example="guideline")


class SchemaCreateCharacter(BaseModel):
    name: str = Field(..., max_length=100, example="Jhon Doe")
    prompt_user: str = Field(..., example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: Optional[str] = Field(None, example="conversation_type")
    options_dialog: Optional[SchemaOpenTalk | SchemaOpenAnswer | SchemaOptionMultiple] = Field(
        None, example={
            "prompt_user_question": None,
            "prompt_user_answer": None,
            "options": [
                {"prompt_user_guideline": None,
                "prompt_user_answer": None}
            ],
            "prompt_user_guideline": None,
            "num_interaction": None

        }

    )
    game_id: Optional[str] = Field(None, example="location_id")
    location_id: Optional[str] = Field(None, example="location_id")
    state_game: Optional[str] = Field(None, example="state_game")
    image_reference: Optional[str] = Field(None, example="reference_image.jpg")
    image: Optional[str] = Field(None, example="image.jpg")
    gender: Optional[str] = Field(None, example=GenderCharacter.MAN)
    voice_id: Optional[str] = Field(None, example="voice_id")
    conversation: Optional[list[ConversationsCharacter]] = Field(None, example="conversation")


class SchemaRetrieveCharacter(ResponseModel):
    game_id: Optional[str] = Field(None, example="game_id")
    task_id: Optional[str] = Field(None, example="task_db")
    status: Optional[str] = Field(1, example="status")
    state_game: Optional[list[SchemaStateLocation]] = Field(None, example=["state_game"])

    class Config:
        orm_mode = True


class SchemaRetrieveCharacterStr(ResponseModelStr):
    game_id: Optional[str] = Field(..., example="game_id")
    task_id: Optional[str] = Field(None, example="task_db")
    status: Optional[str] = Field(1, example="status")
    state_game: Optional[list[SchemaStateLocation]] = Field([], example=["state_game"])

    # weapon: Optional[SchemaRetrieveWeapon] = Field(None, example="weapon")


class SchemaCreateCharacterCollection(BaseModel):
    prompt_user: str = Field(..., example="prompt_user")
    name: str = Field(..., example="name")


class SchemaUpdateCharacterCollection(BaseModel):
    name: Optional[str] = Field(None, max_length=100, example="Jhon Doe")
    prompt_user: Optional[str] = Field(None, example="prompt_user")
    prompt_user_dialog: Optional[str] = Field(None, example="prompt_user_dialog")
    conversation_type: Optional[str] = Field(None, example="conversation_type")
    options_dialog: Optional[SchemaOpenAnswer | SchemaOptionMultiple | SchemaOpenTalk] = Field(
        None, example={"key": "value"}
    )
    image_reference: Optional[str] = Field(None, example="reference_image.jpg")
    location_id: Optional[str] = Field(None, example="location_id")
    game_id: Optional[str] = Field(None, example="game_id")
    state_game: Optional[str] = Field(None, example="state_game")


class SchemaPartialUpdateCharacter(BaseModel):
    image: Optional[str] = Field(None, example="image")


class SchemaListCharacter(BaseModel):
    results: list[SchemaRetrieveCharacterStr]
    count: int

    class Config:
        orm_mode = True


class SchemaUpdatePhotoCharacter(BaseModel):
    image: str = Field(..., example="image")


class SchemaAddCharacterLocation(BaseModel):
    location_id: str = Field(..., example="location_id")
    character_id: str = Field(..., example="character_id")


class SchemaNewInteraction(BaseModel):
    location_id: str = Field(..., example="location_id")
    game_id: str = Field(..., example="game_id")
    conversation_type: str = Field(..., example="conversation_type")
    conversation: list[ConversationsCharacter] = Field(None, example="conversation")
    options_dialog: dict = Field(
        None, example={"key": "value"}
    )
    state_game: Optional[str] = Field(None, example="state_game")


class CharacterLocationModel(BaseModel):
    character_id: str = Field(...)
    location_id: str = Field(...)
    game_id: str = Field(...)
    characteristics: Dict[str, str] = Field(...)
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    created_by: str = Field(...)
    updated_by: str = Field(...)

    class Config:
        json_encoders = {ObjectId: str}


class SchemaUpdatedCharacterLocation(BaseModel):
    character_id: str = Field(...)
    location_id: str = Field(...)
    game_id: str = Field(...)
    state_game: Optional[str] = Field(None)
    characteristics: Dict[str, str] = Field(...)


class SchemaDeactivateCharacter(BaseModel):
    """
    Schema for deactivating a location.

    Attributes:
    status (int): The status of the location.
    """

    is_active: bool = Field(False, example=False)
    state_game: str = Field(None, example="state_game")


class SchemaResponseQuestionOpen(BaseModel):
    prompt_user_answer: str = Field(..., example="prompt_user_answer")
    state_game: Optional[str] = Field(None, example="state_game")


class SchemaResponseTalkOpen(BaseModel):
    prompt_user_answer: str = Field(..., example="prompt_user_answer")
    state_game: Optional[str] = Field(None, example="state_game")
    id_conversation: Optional[str] = Field(None, example="id_conversation")
