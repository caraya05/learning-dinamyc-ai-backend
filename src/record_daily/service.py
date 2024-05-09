from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from record_daily.models import DailyRecord

from core.database import db


async def get_or_create_daily_record_service(*,
                                             user_id: str,
                                             created_at: datetime,
                                             balance: int = 0,
                                             expenses: int = 0,
                                             games_created: int = 0,
                                             sets_with_errors: int = 0,
                                             attempts_to_create_without_balance: int = 0,
                                             ):
    """
    Get or create a daily record.
    """

    try:
        if daily_record := await db['daily_record'].find_one({"user_id": user_id,
                                                              "created_at": {
                                                                  "$gte": created_at.replace(hour=0, minute=0, second=0,
                                                                                             microsecond=0),
                                                                  "$lt": created_at.replace(hour=23, minute=59,
                                                                                            second=59,
                                                                                            microsecond=999999)
                                                              }}):
            return daily_record
        else:
            daily_record = DailyRecord(
                user_id=user_id,
                balance=balance,
                expenses=expenses,
                games_created=games_created,
                sets_with_errors=sets_with_errors,
                attempts_to_create_without_balance=attempts_to_create_without_balance,
            )
            daily_record = await db['daily_record'].insert_one(daily_record.dict())
            if daily_record:
                return await db['daily_record'].find_one({"_id": daily_record.inserted_id})

    except Exception as e:
        print(f"Daily record not created {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Daily record not created {str(e)}"
        )


async def register_daily_record_service(*,
                                        user_id: str,
                                        created_at: datetime,
                                        balance: int = 0,
                                        expenses: int = 0,
                                        games_created: int = 0,
                                        sets_with_errors: int = 0,
                                        attempts_to_create_without_balance: int = 0,
                                        ):
    """
    Update a daily record.
    """

    try:
        daily_record_db = await get_or_create_daily_record_service(
            user_id=user_id,
            created_at=created_at,
            balance=balance,
            expenses=expenses,
            games_created=games_created,
            sets_with_errors=sets_with_errors,
            attempts_to_create_without_balance=attempts_to_create_without_balance,
        )
        if daily_record_db:
            daily_record_db['balance'] = balance
            daily_record_db['expenses'] += expenses
            daily_record_db['games_created'] += games_created
            daily_record_db['sets_with_errors'] += sets_with_errors
            daily_record_db['attempts_to_create_without_balance'] += attempts_to_create_without_balance
            await db['daily_record'].update_one({"_id": ObjectId(daily_record_db['_id'])}, {"$set": daily_record_db})
        return await db['daily_record'].find_one({"_id": ObjectId(daily_record_db['_id'])})
    except Exception as e:
        print(f"Daily record not updated {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Daily record not updated"
        )


async def get_list_daily_record_service(*, type_export: str):
    """
    Get a list of daily records.
    """

    try:
        if type_export == "by_date":
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "year": {"$year": "$created_at"},
                            "month": {"$month": "$created_at"},
                            "day": {"$dayOfMonth": "$created_at"},
                        },
                        "total_expenses": {"$sum": "$expenses"},
                        "total_games_created": {"$sum": "$games_created"},
                        "total_sets_with_errors": {"$sum": "$sets_with_errors"},
                    }
                }
            ]
            daily_records = await db['daily_record'].aggregate(pipeline).to_list(None)
            return daily_records
        elif type_export == "by_user":
            pipeline = [
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_balance": {"$sum": "$balance"},
                        "total_expenses": {"$sum": "$expenses"},
                        "total_games_created": {"$sum": "$games_created"},
                        "total_sets_with_errors": {"$sum": "$sets_with_errors"},
                        "total_attempts_without_balance": {"$sum": "$attempts_to_create_without_balance"},
                    }
                }
            ]
            daily_records = await db['daily_record'].aggregate(pipeline).to_list(None)
            return daily_records
        else:
            daily_records = await db['daily_record'].find().to_list(None)
            return daily_records
    except Exception as e:
        print(f"Daily records not retrieved {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Daily records not retrieved "
        )
