import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://2021sarveshdongare:<db_password>@cluster0.7lznqgg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ecommerce")
