import sys
import os
import csv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import db
from prompt.models import Prompt

with open('Prompt.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        prompt_csv = Prompt(title=row['title'],
                            description=row['description'],
                            prompt_system=row['prompt_system'],
                            category=row['category'],
                            is_active=True,
                            )
        db["prompt"].insert_one(prompt_csv.dict())
