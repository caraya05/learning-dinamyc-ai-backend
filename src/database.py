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
import time

from pymongo import MongoClient
import pymongo

DATABASE_URL = os.getenv("DATABASE_URI", "")
INITIAL_DATABASE = os.getenv("MONGO_INITDB_DATABASE", "")

client = MongoClient(DATABASE_URL)
print('Connected to MongoDB...')

# db = client[INITIAL_DATABASE]


# User = db.create_collection("users")
# Post = db.posts
#
# print(db.name)
# print(db.list_collection_names())
# from pymongo.errors import ServerSelectionTimeoutError
#
#
# def create_index(collection, index, unique=False):
#     try:
#         collection.create_index(index, unique=unique)
#     except ServerSelectionTimeoutError:
#         print(str(ServerSelectionTimeoutError.errors))
#         print("MongoDB no está listo. Esperando 10 segundos antes de volver a intentarlo...")
#         time.sleep(10)
#         create_index(collection, index, unique)
#
#
# # Luego puedes llamar a esta función para crear tus índices:
# create_index(User, [("email", pymongo.ASCENDING)], unique=True)
# create_index(Post, [("title", pymongo.ASCENDING)], unique=True)
