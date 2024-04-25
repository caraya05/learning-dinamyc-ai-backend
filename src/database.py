#
# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
#
# # SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# # SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"
#
# SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URI", "")
#
# engine = create_engine(
#     # SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
#     "mongodb://mongo_user:mongo@localhost:27017/qwestar__db?retryWrites=true&w=majority&authSource=admin"
# )
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# Base = declarative_base()
import os


from mongoengine import connect


from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

DATABASE_URL = os.getenv("DATABASE_URI", "")
client = MongoClient(DATABASE_URL, server_api=ServerApi('1'))
db = client.get_database("QwestarLocal")

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

from motor.motor_asyncio import AsyncIOMotorClient
from odmantic.engine import AIOEngine

engine = AIOEngine(
    client=AsyncIOMotorClient(DATABASE_URL), database="QwestarLocal"
)

connection = connect(host=DATABASE_URL)
