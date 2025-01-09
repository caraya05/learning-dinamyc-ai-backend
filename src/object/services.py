from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from core.database import db

from object.models import Object
from object.models import ObjectGLIC

from object.schemas import SchemaCreateObject
from object.schemas import ObjectLocationModel
from object.schemas import SchemaCreateItem

from state_game.services import get_state_game_by_game_id
from state_game.services import get_state_game_by_id
from state_glic.services import create_state_glic

from task.services import create_task_service
from task.services import update_task_service
from user.services import validate_star_user_service, disable_user_service

# from object.schemas import SchemaPartialUpdateObject

from gpt_ai.utils import openai_generator

from celery_worker import generate_item_task
from celery_worker import updated_item_task
from celery_worker import generate_new_interaction_item_task


async def get_objects_service(game: str = None,
                              location: str = None,
                              user: str = None,
                              skip: int = 0,
                              limit: int = 100):
    """
    Get a list of objects.
    """
    objects_db = []

    try:
        if location:
            item_locations_db = await db["state_glic"].find(
                {"type_element": "item", "data.location_id": {"$in": [location]}}).skip(
                (skip - 1) * limit).limit(limit).to_list(None)
            if not item_locations_db:
                return [], 0
            for item_location_db in item_locations_db:
                objects_db_ = (
                    await db["item"].find_one({"_id": ObjectId(item_location_db["element_id"])}))
                if objects_db_:
                    objects_db_["_id"] = str(objects_db_["_id"])
                    # array_state_game = await db["state_glic"].find(
                    #     {"element_id": objects_db_["_id"]}).to_list(None)
                    # if array_state_game:
                    #     for a in array_state_game:
                    #         a["_id"] = str(a["_id"])
                    #
                    #     objects_db_["state_game"] = array_state_game
                    # else:
                    #     objects_db_["state_game"] = []
                    # print("llego aca")
                    objects_db.append(objects_db_)
            count_objects = (
                await db["state_glic"].count_documents(
                    {"type_element": "item", "data.location_id": {"$in": [location]}})
            )
        elif game:
            objects_db = (
                await db["item"]
                .find({"games_id": {"$in": [game]}})
                .skip((skip - 1) * limit)
                .limit(limit)
                .to_list(None)
            )
            count_objects = (
                await db["item"]
                .count_documents({"games_id": {"$in": [game]}})
            )
        else:
            objects_db = (
                await db["item"]
                .find({"created_by": user})
                .skip(skip)
                .limit(limit)
                .to_list(None)
            )
            count_objects = (
                await db["item"]
                .count_documents({"created_by": user})
            )
        if objects_db:
            for object_db in objects_db:
                object_db["_id"] = str(object_db["_id"])
                elements_state_db = await db["state_glic"].find(
                    {"element_id": object_db["_id"]}
                ).to_list(None)
                if elements_state_db:
                    for element_state_db in elements_state_db:
                        element_state_db["_id"] = str(element_state_db["_id"])

                object_db["state_game"] = elements_state_db
                # item_characteristics = await db["object_location"].find(
                #     {"item_id": object_db["_id"]}).to_list(None)
                # if item_characteristics:
                #     for item_characteristic in item_characteristics:
                #         del item_characteristic["_id"]
                #         del item_characteristic["item_id"]
                #         del item_characteristic["updated_at"]
                #         del item_characteristic["updated_by"]
                #         del item_characteristic["created_at"]
                #         del item_characteristic["created_by"]
                #     object_db["characteristics"] = item_characteristics

        print(objects_db)
        return objects_db, count_objects
    except Exception as e:
        print(f"Error in get objects service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )


async def retrieve_object_service(object_id: str):
    """
    Retrieve a object.
    """
    try:
        if object_db := (await db["item"].find_one({"_id": ObjectId(object_id)})):
            object_db["characteristics"] = await db["object_location"].find_one(
                {"item_id": object_id}
            )
            if object_db:
                element_state_db = await db["state_glic"].find_one(
                    {"element_id": object_id}
                )
                element_state_db["_id"] = str(element_state_db["_id"])
                object_db["state_game"] = [element_state_db]
                # item_characteristics = await db["object_location"].find(
                #     {"item_id": object_id}).to_list(None)
                # if item_characteristics:
                #     for i in range(len(item_characteristics)):
                #         del item_characteristics[i]["_id"]
                #         del item_characteristics[i]["item_id"]
                #         del item_characteristics[i]["updated_at"]
                #         del item_characteristics[i]["updated_by"]
                #         del item_characteristics[i]["created_at"]
                #         del item_characteristics[i]["created_by"]
                #     object_db["characteristics"] = item_characteristics
            return object_db
    except Exception as e:
        print(f"Error in retrieve object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )


async def delete_object_service(object_id: str):
    """
    Delete a object.
    """
    try:
        item_db = await db["item"].find_one({"_id": ObjectId(object_id)})
        # if item_db['image']:
        #     delete_image(item_db['image'])
        object_deleted = await db["object"].delete_one({"_id": ObjectId(object_id)})
        if object_deleted.deleted_count:
            return True
    except Exception as e:
        print(f"Error in delete object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )


async def create_item_service(schema: SchemaCreateObject, user_id: str):
    """
    Create a new object.
    """
    if schema.prompt_user:
        moderation_prompt_user = await openai_generator.moderation_text(
            text=schema.prompt_user,
            user_id=user_id,
        )
        if moderation_prompt_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt user not allowed",
            )
    if schema.prompt_user_dialog:
        moderation_prompt_user_dialog = await openai_generator.moderation_text(
            text=schema.prompt_user_dialog,
            user_id=user_id,
        )
        if moderation_prompt_user_dialog:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt user dialog not allowed",
            )

    await validate_star_user_service(user_id=user_id)
    await  disable_user_service(user_id=user_id, section="item")

    try:
        schema_object = Object(**schema.dict())
        schema_object.created_by = user_id
        schema_object.updated_by = user_id

        object_state = ObjectGLIC(**schema.dict())

        object_created = await db["item"].insert_one(schema_object.dict())

        if schema.state_game:
            state_game = await get_state_game_by_id(schema.state_game)
        else:
            state_game = await get_state_game_by_game_id(schema.game_id)

        if state_game:
            await create_state_glic(
                element_id=str(object_created.inserted_id),
                type_element="item",
                state=state_game['_id'],
                order=1,
                created_by=user_id,
                data=object_state.dict(),
            )

        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=str(object_created.inserted_id),
            _element_type="item",
            _process="generate image item",
        )

        task_celery = generate_item_task.delay(
            _item_id=str(object_created.inserted_id),
            _user_id=user_id,
            _task_id=str(task_db["_id"]),
            _location_id=schema.location_id,
            _state_game_id=state_game['_id'],
            _game_id=schema.game_id,
        )
        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )
        await db["item"].update_one({"_id": object_created.inserted_id},
                                    {"$set": {"tasks_request": [str(task_db["_id"])]}})
        object_db = await db["item"].find_one({"_id": object_created.inserted_id})
        object_db["task_id"] = str(task_db["_id"])
        return object_db

    except Exception as e:
        print(f"Error in create object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not created",
        )


async def update_item_service(object_id: str, schema: SchemaCreateItem):
    """
    Update a object.
    """
    try:
        updated_prompt_user = False
        updated_dialog = False

        if schema.state_game:
            state_game = await get_state_game_by_id(schema.state_game)
        else:
            state_game = await get_state_game_by_game_id(schema.game_id)

        item_db = await db["item"].find_one({"_id": ObjectId(object_id)})
        if schema.name:
            item_db["name"] = schema.name
        if schema.prompt_user:
            if item_db["prompt_user"] != schema.prompt_user:
                updated_prompt_user = True
            item_db["prompt_user"] = schema.prompt_user
        if schema.prompt_user_dialog:
            if item_db["prompt_user_dialog"] != schema.prompt_user_dialog:
                updated_dialog = True
            item_db["prompt_user_dialog"] = schema.prompt_user_dialog

        item_db["updated_at"] = datetime.utcnow()
        await db["item"].update_one({"_id": ObjectId(object_id)}, {"$set": item_db})
        if updated_dialog or updated_prompt_user:
            task_db = await create_task_service(
                _task_id="",
                _user_id=item_db["created_by"],
                _task_data={},
                _element_id=object_id,
                _element_type="item",
                _process="generate image item",
            )
            task_celery = updated_item_task.delay(
                _item_id=object_id,
                _user_id=item_db["created_by"],
                _task_id=str(task_db["_id"]),
                _updated_prompt_user=updated_prompt_user,
                _updated_dialog=updated_dialog,
                _state_game_id=state_game['_id'],
                _location_id=schema.location_id,
            )
            await update_task_service(
                _id=str(task_db["_id"]),
                _task_id=task_celery.id,
            )
            await db["item"].update_one({"_id": ObjectId(object_id)},
                                        {"$set": {"tasks_request": [str(task_db["_id"])]}})

            object_db = await db["item"].find_one({"_id": ObjectId(object_id)})
            object_db["task_id"] = str(task_db["_id"])
            return object_db

        return await db["item"].find_one({"_id": ObjectId(object_id)})

    except Exception as e:
        print(f"Error in update object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not updated",
        )


async def add_item_location_service(item_id: str, location_id: str):
    """
    Add a object to a location.
    """

    item_db = await db["item"].find_one({"_id": ObjectId(item_id)})
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})

    if not item_db or not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item or location not found",
        )
    if "locations_id" in item_db and item_db.get("locations_id"):
        if location_id not in item_db.get("locations_id", []):
            item_db["locations_id"].append(location_id)
    else:
        item_db["locations_id"] = [location_id]

    await db["item"].update_one({"_id": ObjectId(item_id)}, {"$set": {"locations_id": item_db["locations_id"]}})

    existing_entry = await db["object_location"].find_one(
        {"item_id": item_id, "location_id": location_id}
    )
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Object already in location",
        )

    object_location = ObjectLocationModel(
        item_id=item_id,
        location_id=location_id,
        characteristics={},
        created_by=item_db["created_by"],
        updated_by=item_db["updated_by"],
    )
    try:
        await db["object_location"].insert_one(object_location.dict())

        return "item added to location"

    except Exception as e:
        print(f"Error in add item location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not added to location",
        )


async def add_or_edit_item_characteristic_service(
        item_id: str, location_id: str, characteristics: dict, user_id: str, game_id: str = None, state_game: str = None
):
    """
    Add or edit a characteristic to a object in a location.
    """
    # existing_entry = await db["object_location"].find_one(
    #     {"item_id": item_id, "location_id": location_id}
    # )
    # if existing_entry:
    #     await db["object_location"].update_one(
    #         {"_id": existing_entry["_id"]},
    #         {
    #             "$set": {
    #                 "characteristics": characteristics,
    #                 "updated_at": datetime.utcnow(),
    #                 "updated_by": user_id,
    #             }
    #         },
    #     )

    if state_game:
        state_game_id = await get_state_game_by_id(state_game)
    else:
        state_game_id = await get_state_game_by_game_id(game_id)

    element_state_db = await db["state_glic"].find_one(
        {"element_id": item_id, "state": state_game_id["_id"]}
    )

    element_state_db["data"]["characteristics"] = characteristics

    await db["state_glic"].update_one(
        {"_id": element_state_db["_id"]},
        {"$set": {"data": element_state_db["data"]}}
    )

    return "Item characteristic updated"
    # else:
    #     object_location = ObjectLocationModel(
    #         item_id=item_id,
    #         location_id=location_id,
    #         characteristics=characteristics,
    #         created_by=user_id,
    #         updated_by=user_id,
    #     )
    #
    #     await db["object_location"].insert_one(object_location.dict())
    #
    #     return "Item characteristic added"


async def get_item_by_location_service(location_id: str):
    """
    Get a list of objects in a location.
    """
    location_db = await db["location"].find_one({"_id": ObjectId(location_id)})
    if not location_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )
    try:
        if (
                object_locations_db := await db["object_location"]
                        .find({"location_id": location_id})
                        .to_list(None)
        ):
            objects_db = []
            for object_location in object_locations_db:
                object_db = await db["item"].find_one(
                    {"_id": ObjectId(object_location["object_id"])}
                )
                object_db["characteristics"] = object_location["characteristics"]
                object_db["_id"] = str(object_db["_id"])
                objects_db.append(object_db)
            return objects_db
    except Exception as e:
        print(f"Error in get item by location service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )


async def get_all_object_service(user_id: str, skip: int = 1, limit: int = 10):
    """
    Get all objects.
    """
    try:
        objects_db = await (
            db["object"]
            .find({"created_by": user_id})
            .sort("created_at", -1)
            .skip((skip - 1) * limit)
            .limit(limit)
            .to_list(None)
        )
        return objects_db
    except Exception as e:
        print(f"Error in get all object service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objects not found",
        )


async def new_interaction_item_service(location_id: str, game_id: str, item_id: str, prompt_user_dialog: str,
                                       user_id: str, state_game: str = None):
    """
    Generate a interaction for a object.
    """

    item_db = await db["item"].find_one({"_id": ObjectId(item_id)})
    if not item_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item or location not found",
        )

    if state_game:
        state_game = await get_state_game_by_id(state_game)
    else:
        state_game = await get_state_game_by_game_id(game_id)

    try:
        task_db = await create_task_service(
            _task_id="",
            _user_id=user_id,
            _task_data={},
            _element_id=item_id,
            _element_type="item",
            _process="new_interaction_item",
        )
        task_celery = generate_new_interaction_item_task.delay(
            _task_id=str(task_db['_id']),
            _item_id=item_db,
            _location_id=location_id,
            _user_id=user_id,
            _state_game_id=state_game['_id'],
            _prompt_user_dialog=prompt_user_dialog
        )

        await update_task_service(
            _id=str(task_db["_id"]),
            _task_id=task_celery.id,
        )

        item_db["tasks_request"].append(str(task_db["_id"]))
        await db["character"].update_one(
            {"_id": item_db["_id"]},
            {"$set": {"tasks_request": item_db["tasks_request"]}},
        )

        item_db["task_id"] = str(task_db["_id"])
        return item_db
    except Exception as e:
        print(f"Error in new interaction item service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction not created",
        )


async def deactivate_item_service(item_id: str,state_game:str, active: bool):
    """
    Deactivate a object.
    """
    try:
        item_db = await db["item"].find_one({"_id": ObjectId(item_id)})
        if not item_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found",
            )

        state_game_db = await db["state_glic"].find_one(
            {"element_id": item_id, "state": state_game}
        )
        if not state_game_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="State game not found",
            )

        state_game_db["data"]["active"] = active
        await db["state_glic"].update_one(
            {"_id": state_game_db["_id"]},
            {"$set": {"data": state_game_db["data"]}}
        )

        return "Item deactivated"
    except Exception as e:
        print(f"Error in deactivate item service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not deactivated",
        )