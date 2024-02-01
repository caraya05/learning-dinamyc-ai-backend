import json

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from character.schemas import SchemaCreateCharacter
from game.schemas import SchemaCreateGame
from game.schemas import SchemaPartialUpdateGame

from game.models import Game
from game.utils import get_history
from game.utils import get_synopsis
from game.utils import get_characters_principals

from gpt_ai.utils import generate_gpt4_vision_
from gpt_ai.utils import generate_gpt4_
from gpt_ai.utils import generate_image_dalle

from character.services import create_character_service
from location.schemas import SchemaCreateLocation
from location.services import create_location_service
from prompt.services import get_prompt_by_field
from utils import upload_image


def get_game_by_field(db: Session, field: str, value: str):
    return db.query(Game).filter(getattr(Game, field) == value).first()


def get_game_service(db: Session, game_id: str, user_id: str):
    game_db = get_game_by_field(db, 'id', game_id)
    if not game_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
    # if game_db.user_id != user_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Unauthorized",
    #     )
    return game_db


def get_games_service(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Game).offset(skip).limit(limit).all()


def create_game_service(db: Session, game: SchemaCreateGame, user_id: str):
    history = get_history(db=db, story_line=game.story_line)
    print("history", history)
    synopsys = get_synopsis(db=db, history=history)
    print("synopsys", synopsys)
    characters_principals = get_characters_principals(db=db, history=history)
    print("characters_principals", characters_principals)

    try:
        db_game = Game(story_line=game.story_line,
                       history=history,
                       synopsis=synopsys['synopsis_generate'],
                       title=synopsys['title'],
                       prompt_image=synopsys['prompt_image'],
                       user_id=user_id,
                       updated_by=user_id,
                       created_by=user_id,
                       image="",
                       image_background="",
                       )
        db.add(db_game)
        db.commit()
        db.refresh(db_game)

        for i in characters_principals['characters_generate']:
            create_character_service(db=db,
                                     character=SchemaCreateCharacter(name=i['name'],
                                                                     genre=i['genre'],
                                                                     type=i['type'].lower(),
                                                                     description=i['description']),
                                     game_id=db_game.id,
                                     user_id=user_id)

        return db_game

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not created",
        )


def update_partial_game_service(db: Session,
                                game_id: str,
                                game_update: SchemaPartialUpdateGame,
                                user_id: str):
    game_db = get_game_by_field(db, 'id', game_id)

    # prompt_db_c = get_prompt_by_field(db, 'category', 'character')
    # prompt_db_ci = get_prompt_by_field(db, 'category', 'character_image')
    # prompt_db_l = get_prompt_by_field(db, 'category', 'location')
    # prompt_db_li = get_prompt_by_field(db, 'category', 'location_image')
    #
    # if game_db:
    #     json_schema = {
    #         "characters": [
    #             {
    #                 "name": "string name character",
    #                 "type": "string (leading role, enemy, other) in minuscule",
    #                 "description": "string (description of the character)",
    #             }
    #         ]
    #     }
    #
    #     content_prompt = [
    #         {
    #             "role": "system",
    #             "content": f"Eres un gran escritor capaz de desarrollar una historia para cada personaje del juego,"
    #                        f"utilizando una imagen de portada y una historia existente, crea cada personaje a detalle"
    #                        f"con nombre, descripción detallada para ser utilizada como prompt para la generacion "
    #                        f"de una imagen y tipo de personaje  entre los tipos (leading role, enemy, other), "
    #         },
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "image_url",
    #                     "image_url": {
    #                         "url": game_update.image
    #                     }
    #                 },
    #                 {
    #                     "type": "text",
    #                     "text": f"descripccion: {game_db.summary}"
    #                 },
    #                 {
    #                     "type": "text",
    #                     "text": prompt_db_c.description
    #                 }
    #             ]
    #         }
    #     ]
    #
    #     characters_generated = generate_gpt4_vision_(content_prompt=content_prompt)
    #
    #     content_prompt_2 = [
    #         {
    #             "role": "system",
    #             "content": f"Eres un convertidor de respuesta de la IA a JSON, "
    #                        f"capaz de convertir la respuesta de la IA a un JSON que contenga el esquema '{json_schema}'"
    #         },
    #         {
    #             "role": "user",
    #             "content": [
    #                 {
    #                     "type": "text",
    #                     "text": prompt_db_l.description
    #                 },
    #
    #                 {
    #                     "type": "text",
    #                     "text": characters_generated
    #                 }
    #             ]
    #         }
    #     ]
    #
    #     characters_list_generated = json.loads(generate_gpt4_(content_prompt=content_prompt_2))
    #
    #     for ch in characters_list_generated['characters']:
    #         content_prompt_3 = (
    #             f"{prompt_db_ci.description} :{ch['description']}")
    #
    #         image_character_generated = generate_image_dalle(prompt=content_prompt_3)
    #
    #         ch['image'] = image_character_generated
    #
    #         create_character_service(db=db,
    #                                  character=SchemaCreateCharacter(**ch),
    #                                  game_id=game_id,
    #                                  user_id=user_id)
    #
    #         json_schema_location = {
    #             "title": "string title location",
    #             "description": "string (description of the location)",
    #         }
    #
    #         content_prompt_3 = [
    #             {
    #                 "role": "system",
    #                 "content": f"Eres un gran escritor capaz de desarrollar una historia para cada locacion del juego,"
    #                            f"en base a la descripcion de un personaje, crea cada locacion a detalle con el nombre y la desripcion"
    #                            f"detallada para ser utilizada como prompt para la generacion de una imagen, la respuesta de la IA"
    #                            f"debe ser un JSON que contenga el esquema '{json_schema_location}'"
    #             },
    #             {
    #                 "role": "user",
    #                 "content": [
    #
    #                     {
    #                         "type": "text",
    #                         "text": characters_generated
    #                     }
    #                 ]
    #             }
    #         ]
    #
    #         location_generated = generate_gpt4_(content_prompt=content_prompt_3)
    #
    #         location_generated = json.loads(location_generated)
    #
    #         create_location_service(db=db,
    #                                 schema=SchemaCreateLocation(**location_generated),
    #                                 game_id=game_id,
    #                                 user_id=user_id)

    try:
        game_db.photo = upload_image(url_image=game_update.image, file_name=f"covers/{game_id}-cover.jpg")

        db.commit()
        db.refresh(game_db)
        return game_db
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game not updated",
        )
