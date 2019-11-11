from peewee import *
from models import *
import os

def clean_db_install():
    try:
        os.remove("webpages.db")
    except:
        pass

    db = SqliteDatabase('webpages.db')
    db.connect()
    db.create_tables([WebPage, WebPageMTM, DeadLink])

if __name__ == '__main__':
    clean_db_install()