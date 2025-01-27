import traceback

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from celery_worker import generate_location_task
from celery_worker import generate_image_location_task
from core.database import db

from character.services import get_characters_by_location_service

from location.models import Location
from location.models import LocationGLIC
from location.schemas import SchemaCreateLocation
from location.schemas import SchemaPartialUpdateLocation

from state_game.services import get_state_game_by_game_id
from state_game.services import get_state_game_by_id

from state_glic.services import create_state_glic

from task.services import create_task_service
from task.services import update_task_service

from gpt_ai.utils import openai_generator
from user.services import validate_star_user_service, disable_user_service


async def get_locations_service(*, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:
        locations = (
            await db['location'].find({"game_id": game_id}).skip(skip).limit(limit).to_list(None)
        )
        count_locations = await db['location'].count_documents({"game_id": game_id})
        return locations, count_locations
    except Exception as e:
        print(f"Error in get locations service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found.")


async def get_location_service(*, location_id: str, user_id: str) -> dict:
    """
    Get a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            element_state_db = await db['state_glic'].find({"element_id": location_id}).to_list(None)

            for i in range(len(element_state_db)):
                element_state_db[i]["_id"] = str(element_state_db[i]["_id"])

                if element_state_db[i]["data"].get("sound", None):
                    try:
                        sound_db = await db['sound'].find_one(
                            {"_id": ObjectId(element_state_db[i]["data"]["sound"])}
                        )
                        if sound_db:
                            element_state_db[i]["data"]["sound"] = sound_db["file"]
                    except Exception as e:
                        print(f"Error in get sound service: {e}")
                        pass
                # if location_db["config"]:
                #     user_config_found = False
                #     for config in location_db["config"]:
                #         if config["user"] == user_id:
                #             location_db["configuration"] = config["config"]
                #             user_config_found = True
                #             break
                #     if not user_config_found and location_db["config"]:
                #         location_db["configuration"] = location_db["config"][0]["config"]
                #
                # if location_db.get("connect", None):
                #     user_connect_found = False
                #     for connect in location_db["connect"]:
                #         if connect["user"] == user_id:
                #             location_db["connections"] = connect["connect"]
                #             user_connect_found = True
                #             break
                #     if not user_connect_found and location_db["connect"]:
                #         location_db["connections"] = location_db["connect"][0]["connect"]
                # element_state_db = SchemaStateLocation(**element_state_db["data"])
            location_db["state_game"] = element_state_db

            if characters_db := await get_characters_by_location_service(
                    skip=1, limit=100, location_id=location_id
            ):
                location_db["characters"] = characters_db

            return location_db
    except Exception as e:
        print(f"Error in get location service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")


async def get_locations_v2_service(*, game_id: str, skip: int = 0, limit: int = 100):
    """
    Get a list of locations.
    """
    try:

        game_db = await db['game'].find_one({"_id": ObjectId(game_id)})
        locations = await (
            db['location']
            .find({"game_id": game_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(None)
        )

        for i in range(len(locations)):
            locations[i]["_id"] = str(locations[i]["_id"])
            element_state_db = await db['state_glic'].find(
                {"element_id": locations[i]["_id"]}
            ).to_list(None)
            if element_state_db:
                for j in range(len(element_state_db)):
                    element_state_db[j]["_id"] = str(element_state_db[j]["_id"])
                    if element_state_db[j]["data"].get("sound", None):
                        try:
                            sound_db = await db['sound'].find_one(
                                {"_id": ObjectId(element_state_db[j]["data"]["sound"])}
                            )
                            if sound_db:
                                element_state_db[j]["data"]["sound"] = sound_db["file"]
                        except Exception as e:
                            print(e)
                            pass
                locations[i]["state_game"] = element_state_db

        count_locations = await db['location'].count_documents(
            {"game_id": game_id}
        )

        return locations, count_locations
    except Exception as e:
        print(traceback.print_exc())
        print(f"Error in get locations service: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locations not found.")


async def create_location_service(location: SchemaCreateLocation, user_id: str):
    """
    Create a location.
    """

    moderation_prompt_user = await openai_generator.moderation_text(
        text=location.prompt_user,
        user_id=user_id,
    )
    if moderation_prompt_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt user not allowed",
        )

    await validate_star_user_service(user_id=user_id)
    await  disable_user_service(user_id=user_id, section="location")

    try:
        location_schema = Location(**location.dict())
        location_schema.created_by = user_id
        location_schema.updated_by = user_id
        location_created = await db['location'].insert_one(location_schema.dict())

        game_db = await db['game'].find_one({'_id': ObjectId(location.game_id)})
        if game_db:
            if game_db.get('locations_id'):
                game_db["locations_id"].append(str(location_created.inserted_id))
            else:
                game_db["locations_id"] = [str(location_created.inserted_id)]
            await db['game'].update_one(
                {'_id': ObjectId(location.game_id)}, {'$set': game_db}
            )

        location_db_state = LocationGLIC(**location.dict())

        if location.state_game:
            state_game = await get_state_game_by_id(location.state_game)
        else:
            state_game = await get_state_game_by_game_id(location.game_id)

        if state_game:
            await create_state_glic(
                element_id=str(location_created.inserted_id),
                type_element="location",
                state=state_game["_id"],
                order=state_game["order"],
                created_by=user_id,
                data=location_db_state.dict(),
            )

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(location_created.inserted_id),
            _element_type="location",
            _process="generate_location",
        )

        task_celery = generate_location_task.delay(
            _location_id=str(location_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db["_id"]),
            _state_game_id=state_game["_id"],
        )

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        await db['location'].update_one(
            {"_id": location_created.inserted_id},
            {"$set": {"tasks_request": [str(task_celery.id)]}},
        )
        if location_db := await db['location'].find_one({"_id": location_created.inserted_id}):
            location_db["task_id"] = str(task_db["_id"])
            return location_db
    except Exception as e:
        print(f"Error in create location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not created")


async def partial_update_location_service(
        *, location_id: str, location: SchemaPartialUpdateLocation, user_id: str,
):
    """
    Partially update a location.
    """
    if location.prompt_user:
        moderation_prompt_user = await openai_generator.moderation_text(
            text=location.prompt_user,
            user_id=user_id,
        )
        if moderation_prompt_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt user not allowed",
            )

        await validate_star_user_service(user_id=user_id)
        await  disable_user_service(user_id=user_id, section="location")

    title_or_prompt_user_changed = False
    config_edited = False
    connect_edited = False

    location_db = await db['location'].find_one({"_id": ObjectId(location_id)})

    if location.state_game:
        state_game_db = await get_state_game_by_id(location.state_game)
    else:
        state_game_db = await get_state_game_by_game_id(location.game_id)

    element_state_db = await db['state_glic'].find_one(
        {"element_id": location_id, "state": state_game_db["_id"]}
    )

    if location.title and location.title != element_state_db["data"]["title"]:
        title_or_prompt_user_changed = True
    if location.prompt_user and location.prompt_user != element_state_db["data"]["prompt_user"]:
        title_or_prompt_user_changed = True

    if location.configuration and location.configuration != element_state_db["data"]["configuration"]:
        config_edited = True
    if location.connections and location.connections != element_state_db["data"]["connections"]:
        connect_edited = True
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            location_db["updated_by"] = user_id
            if location.title:
                element_state_db["data"]["title"] = location.title
            if location.prompt_user:
                element_state_db["data"]["prompt_user"] = location.prompt_user
            if location.configuration:
                element_state_db["data"]["configuration"] = location.configuration
                # if not location_db["config"]:
                #     location_db["config"] = []
                #     json_config = {
                #         "config": location.configuration,
                #         "user": user_id,
                #     }
                #     location_db["config"].append(json_config)
                # else:
                #     for i in range(len(location_db["config"])):
                #         if location_db["config"][i]["user"] == user_id:
                #             location_db["config"][i]["config"] = location.configuration
            if location.connections:
                # if not location_db.get("connect", None):
                #     location_db["connect"] = []
                #     json_connect = {
                #         "connect": location.connections,
                #         "user": user_id,
                #     }
                #     location_db["connect"].append(json_connect)
                # else:
                #     for i in range(len(location_db["connect"])):
                #         if location_db["connect"][i]["user"] == user_id:
                #             location_db["connect"][i]["connect"] = location.connections
                element_state_db["data"]["connections"] = location.connections
            # await db['location'].update_one({"_id": ObjectId(location_id)}, {"$set": location_db})

            await db['state_glic'].update_one(
                {"_id": element_state_db["_id"]},
                {"$set": {"data": element_state_db["data"]}}
            )

            location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
            if title_or_prompt_user_changed or (
                    not config_edited and not connect_edited and title_or_prompt_user_changed):
                task_db = await create_task_service(
                    _task_id="",
                    _user_id=user_id,
                    _task_data={},
                    _element_id=str(location_id),
                    _element_type="location",
                    _process="update_location",
                )
                task_celery = generate_location_task.delay(
                    _location_id=location_id, _user_id=user_id, _task_id=str(task_db["_id"]),
                    _sate_game_id=state_game_db["_id"]
                )
                await update_task_service(
                    _id=str(task_db["_id"]),
                    _task_id=task_celery.id,
                )
                location_db["tasks_request"] = location_db["tasks_request"].append(str(task_db["_id"]))
                await db['location'].update_one(
                    {"_id": ObjectId(location_id)},
                    {"$set": {"tasks_request": location_db["tasks_request"]}},
                )
                location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
                location_db["task_id"] = str(task_db["_id"])
            return location_db
    except Exception as e:
        print(f"Error in partial update location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not updated.")


async def generate_image_location_service(location_id: str, user_id: str):
    """
    Generate an image for a location.
    """
    try:
        location_db = await db['location'].find_one({"_id": ObjectId(location_id)})
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=location_id,
            _element_type="location",
            _process="generate_image_location",
        )
        task_celery = generate_image_location_task.delay(
            _location_id=location_id, _user_id=user_id, _task_id=str(task_db["_id"])
        )

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        if not isinstance(location_db["tasks_request"], list):
            location_db["tasks_request"] = []
        location_db["tasks_request"].append(str(task_db["_id"]))

        await db['location'].update_one(
            {"_id": ObjectId(location_id)},
            {"$set": {"tasks_request": location_db["tasks_request"]}},
        )

        location_db["task_id"] = str(task_db["_id"])
        return location_db
    except Exception as e:
        print(f"Error in generate image location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image not generated.")


async def get_all_location_service(user_id: str, skip: int = 1, limit: int = 10):
    try:
        locations = await (db["location"]
                           .find({"created_by": user_id})
                           .sort("created_at", -1)
                           .skip((skip - 1) * limit)
                           .limit(limit)
                           .to_list(None))
        if not locations:
            return locations, 0
        for i in range(len(locations)):
            print(locations[i])
            locations[i]["_id"] = str(locations[i]["_id"])
            element_state_db = await db['state_glic'].find_one(
                {"element_id": locations[i]["_id"], "type_element": "location"}
            )
            if element_state_db:
                element_state_db["_id"] = str(element_state_db["_id"])
                if element_state_db["data"].get("sound", None):
                    try:
                        sound_db = await db['sound'].find_one(
                            {"_id": ObjectId(element_state_db["data"]["sound"])}
                        )
                        if sound_db:
                            element_state_db["data"]["sound"] = sound_db["file"]
                    except Exception as e:
                        print(f"Error in get sound service: {e}")
                        element_state_db["data"]["sound"] = None
                        pass
                locations[i]["state_game"] = [element_state_db]

        count_characters = await db["location"].count_documents({"created_by": user_id})
        return locations, count_characters
    except Exception as e:
        print(f"Error in get all character service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characters not found",
        )


async def delete_location_service(location_id: str):
    """
    Delete a location.
    """
    try:
        if location_deleted := await db['location'].delete_one({"_id": ObjectId(location_id)}):
            if location_deleted.deleted_count:
                return True
    except Exception as e:
        print(f"Error in delete location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not deleted.")


async def deactivate_location_service(location_id: str, state_game: str, active: bool):
    """
    Deactivate a location.
    """
    try:
        if location_db := await db['location'].find_one({"_id": ObjectId(location_id)}):
            state_element_db = await db['state_glic'].find_one(
                {"element_id": location_id, "type_element": "location", "state": state_game}
            )

            if not state_element_db:
                state_game_db = await db["state_game"].find_one({"_id": ObjectId(state_game)})

                print("state_game_db", state_game_db)

                order = state_game_db["order"] - 1
                state_element_db = None

                while order >= 1:
                    state_element_db = await db["state_glic"].find_one(
                        {"element_id": location_id, "type_element": "location", "order": order}
                    )
                    if state_element_db:
                        break
                    order -= 1

                if not state_element_db:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="State element not found"
                    )

                print(state_element_db)

                if not state_element_db:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="State element not found",
                    )

                state_element_db['data']['is_active'] = active

                state_element_db["data"]["config"] = None
                state_element_db["data"]["connections"] = None

                state_element_db = await create_state_glic(
                    element_id=str(location_id),
                    type_element="location",
                    state=str(state_game_db['_id']),
                    order=state_game_db['order'],
                    created_by=state_game_db['created_by'],
                    data=state_element_db['data'])

                return "Location deactivated / activate successfully"

            state_element_db["data"]["is_active"] = active
            await db['state_glic'].update_one(
                {"_id": state_element_db["_id"]},
                {"$set": {"data": state_element_db["data"]}}
            )

            return "Location deactivated / activate successfully"
    except Exception as e:
        print(traceback.print_exc())
        print(f"Error in diactive location service: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location not diactive.")
