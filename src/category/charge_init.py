import sys
import os
import csv
from core.database import db
from category.models import Category

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('Category.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        category_csv = Category(name=row['name'],
                                description=row['description'],
                                is_active=True,
                                )
        db["category"].insert_one(category_csv.dict())
