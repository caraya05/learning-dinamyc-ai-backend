import io

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import status

# from fastapi.responses import StreamingResponse
#
# from openpyxl.workbook import Workbook
#
#
# from record_daily.service import get_list_daily_record_service

router = APIRouter(prefix="/daily-record", tags=["Daily Record"])




# @router.get("/export/by_date", status_code=status.HTTP_200_OK)
# def export_by_date(request: Request, db: Session = Depends(get_db)):
#     """
#     This endpoint exports daily records by date.
#     """
#
#     print("request.state.db", request.cookies.get("session"))
#
#     daily_records = get_list_daily_record_service(db, type_export="by_date")
#
#     wb = Workbook()
#     ws = wb.active
#
#     # Add headers
#     headers = ["Date", "Total Expenses", "Total Games Created", "Total Sets With Errors"]
#     ws.append(headers)
#
#     # Add data
#     for record in daily_records:
#         row = [
#             record.date,
#             record.total_expenses,
#             record.total_games_created,
#             record.total_sets_with_errors,
#         ]
#         ws.append(row)
#
#     # Save to BytesIO stream
#     stream = io.BytesIO()
#     wb.save(stream)
#     stream.seek(0)
#
#     # Return the file as a response
#     return StreamingResponse(
#         stream,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={'Content-Disposition': 'attachment; filename=daily_records_by_user.xlsx'},
#     )
#
#
# @router.get("/export/by_user", status_code=status.HTTP_200_OK)
# def export_by_user(
#     db: Session = Depends(get_db),
# ):
#     """
#     This endpoint exports daily records by date.
#     """
#
#     daily_records = get_list_daily_record_service(db, type_export="by_user")
#
#     wb = Workbook()
#     ws = wb.active
#
#     # Add headers
#     headers = [
#         "User",
#         "Total Balance",
#         "Total Expenses",
#         "Total Games Created",
#         "Total Sets With Errors",
#         "Total Attempts Without Balance",
#     ]
#     ws.append(headers)
#
#     # Add data
#     for record in daily_records:
#         row = [
#             record.user,
#             record.total_balance,
#             record.total_expenses,
#             record.total_games_created,
#             record.total_sets_with_errors,
#             record.total_attempts_without_balance,
#         ]
#         ws.append(row)
#
#     # Save to BytesIO stream
#     stream = io.BytesIO()
#     wb.save(stream)
#     stream.seek(0)
#
#     # Return the file as a response
#     return StreamingResponse(
#         stream,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={'Content-Disposition': 'attachment; filename=daily_records_by_user.xlsx'},
#     )
