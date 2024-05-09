import sys
import os
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import db
from customize.models import Customize

with open('Customize.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        prompt_csv = Customize(type_character="human",
                               reference_ui=row['reference_ui'],
                               gender=row["gender"],
                               description=row["description"],
                               type_customize=row["type_customize"],
                               created_by="",
                               updated_by="",
                               )
        db["customize"].insert_one(prompt_csv.dict())
