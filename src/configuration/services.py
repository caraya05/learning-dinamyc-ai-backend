from fastapi import HTTPException
from fastapi import status

from core.database import db

from configuration.models import Configuration

from configuration.schemas import SchemaUpdateConfiguration


async def create_configuration_service(configuration: Configuration):
    try:
        new_configuration = await db['configuration'].insert_one(configuration.dict())
        return await db['configuration'].find_one({"_id": new_configuration.inserted_id})
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error creating configuration"
        ) from ex


async def get_configurations_service():
    try:
        configurations = await db['configuration'].find({}).to_list(None)
        return configurations[0] if configurations else None
    except Exception as ex:
        print(f"Error getting configurations: {str(ex)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error getting configurations"
        )


async def get_configuration_by_id_service(configuration_id: str):
    try:
        if configuration := await db['configuration'].find_one({"_id": configuration_id}):
            return configuration
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error getting configuration"
        ) from ex


async def update_configuration_service(configuration_id: str, configuration: SchemaUpdateConfiguration):
    try:
        updated_configuration = await db['configuration'].update_one({"_id": configuration_id},
                                                                     {"$set": configuration.dict()})
        if updated_configuration.modified_count:
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error updating configuration"
        ) from ex


async def delete_configuration_service(configuration_id: str):
    try:
        deleted_configuration = await db['configuration'].delete_one({"_id": configuration_id})
        if deleted_configuration.deleted_count:
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
            )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error deleting configuration"
        ) from ex
