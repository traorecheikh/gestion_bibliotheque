#on importe lextension load_dotenv dans le modul dotenv
from dotenv import load_dotenv
import os
#charger dot env
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')