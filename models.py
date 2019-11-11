import datetime
from peewee import *

db = SqliteDatabase('webpages.db')

class BaseModel(Model):
    class Meta:
        database = db

class WebPage(BaseModel):
    title = CharField(max_length=200)
    url = CharField(max_length=400, unique=True)

class WebPageMTM(BaseModel):
    parent = ForeignKeyField(WebPage)
    child = ForeignKeyField(WebPage)

class DeadLink(BaseModel):
    linklocation = ForeignKeyField(WebPage)
    responsecode = IntegerField()
    url = CharField(max_length=400, unique=False)