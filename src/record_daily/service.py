from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from fastapi import status
from sqlalchemy import func

from record_daily.models import DailyRecord


def get_or_create_daily_record_service(db: Session,
                                       user: str,
                                       created_at: datetime,
                                       balance: int = 0,
                                       expenses: int = 0,
                                       games_created: int = 0,
                                       sets_with_errors: int = 0,
                                       attempts_to_create_without_balance: int = 0):
    """
    Get or create a daily record.
    """

    try:
        daily_record = db.query(DailyRecord).filter(DailyRecord.user == user,
                                                    func.date(DailyRecord.created_at) == created_at.date()).first()
        if not daily_record:
            daily_record = DailyRecord(user=user,
                                       balance=balance,
                                       expenses=expenses,
                                       games_created=games_created,
                                       sets_with_errors=sets_with_errors,
                                       attempts_to_create_without_balance=attempts_to_create_without_balance)
            db.add(daily_record)
            db.commit()
            db.refresh(daily_record)
        return daily_record
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Daily record not created {e}") from e


def register_daily_record_service(db: Session,
                                  user: str,
                                  created_at: datetime,
                                  balance: int = 0,
                                  expenses: int = 0,
                                  games_created: int = 0,
                                  sets_with_errors: int = 0,
                                  attempts_to_create_without_balance: int = 0):
    """
    Update a daily record.
    """

    try:
        daily_record = get_or_create_daily_record_service(db, user, created_at, balance, expenses, games_created,
                                                          sets_with_errors, attempts_to_create_without_balance)
        if daily_record:
            daily_record.balance = balance
            daily_record.expenses += expenses
            daily_record.games_created += games_created
            daily_record.sets_with_errors += sets_with_errors
            daily_record.attempts_to_create_without_balance += attempts_to_create_without_balance
            db.commit()
            db.refresh(daily_record)
        return daily_record
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Daily record not updated {e}") from e


def get_list_daily_record_service(db: Session, type_export: str):
    try:
        if type_export == "by_date":
            daily_records = (
                db.query(
                    func.date(DailyRecord.created_at).label("date"),
                    func.sum(DailyRecord.expenses).label("total_expenses"),
                    func.sum(DailyRecord.games_created).label("total_games_created"),
                    func.sum(DailyRecord.sets_with_errors).label("total_sets_with_errors"),
                )
                .group_by(func.date(DailyRecord.created_at))
                .all()
            )
            return daily_records
        elif type_export == "by_user":
            daily_records = (
                db.query(
                    DailyRecord.user,
                    # func.date(DailyRecord.user).label("date"),
                    func.sum(DailyRecord.balance).label("total_balance"),
                    func.sum(DailyRecord.expenses).label("total_expenses"),
                    func.sum(DailyRecord.games_created).label("total_games_created"),
                    func.sum(DailyRecord.sets_with_errors).label("total_sets_with_errors"),
                    func.sum(DailyRecord.attempts_to_create_without_balance).label("total_attempts_without_balance"),
                )
                .group_by(DailyRecord.user)
                .all()
            )
            return daily_records
        else:
            daily_records = db.query(DailyRecord).all()
            return daily_records
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Daily records not retrieved {e}") from e
