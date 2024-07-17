import os
import platform

from sqlalchemy import create_engine, text
from sqlalchemy.orm import create_session
import pymysql

# Create an engine to connect to your MySQL database
DBENGINE = create_engine("mysql+pymysql://root:raspberry@localhost:3306/FR_API", pool_recycle=3600)

# Establish a connection
DBCONN = DBENGINE.connect()
DBSESSION = create_session(bind=DBENGINE)

def extract():
    result = DBSESSION.execute(text("""SELECT * FROM verify_history WHERE found_image='ambiguous'"""))
    for row in result:
        image = row[1]
        if(os.path.isfile(image)):
            location = image.split("/")
            to_location = "AmbiguousFaces/"+location[1]
            os.replace(image, to_location)

extract()