from fastapi import FastAPI, File, UploadFile, Depends, Request, HTTPException
from tempfile import NamedTemporaryFile
from fastapi.responses import JSONResponse
from starlette.datastructures import FormData
from pydantic import BaseModel
from deepface import DeepFace
from PIL import Image
import os
import platform
import cv2
import base64
import glob
from uuid_extensions import uuid7, uuid7str
import time
import json
import numpy as np
import urllib.parse
import datetime
import recognition as dfr
import facemaskdetector as fmd

from sqlalchemy import create_engine, text
from sqlalchemy.orm import create_session
import pymysql

app = FastAPI()

FACEPATH = "KnownFaces"
# Create an engine to connect to your MySQL database
#DBENGINE = create_engine("mysql+pymysql://root:aelhFYMqOHHcXdXbtopUNmGsnrGqxZty@roundhouse.proxy.rlwy.net:26410/railway", pool_recycle=3600)
DBENGINE = create_engine("mysql+pymysql://root@localhost:3306/FR_API", pool_recycle=3600)

# Establish a connection
DBCONN = DBENGINE.connect()
DBSESSION = create_session(bind=DBENGINE)


class VerifyFile(BaseModel):
    file : str
    rotation : str = ''
    filter_by : str = 'ALL'
    filter_q : str = 'ALL'

class EnrollFile(BaseModel):
    induk : str
    file : str

class AbsensiModel(BaseModel): 
    uuid : str
    nik : str
    in_out: str
    mac_address: str

class TurnstileModel(BaseModel): 
    uuid : str
    in_out: str
    mac_address: str

def base64_to_image(base64_string):
    # Remove the data URI prefix if present
    if "data:image" in base64_string:
        base64_string = base64_string.split(",")[1]

    # Decode the Base64 string into bytes
    image_bytes = base64.b64decode(base64_string)
    return image_bytes

def cari_nama_by_induk(induk: str):
    result = DBSESSION.execute(text("""SELECT NAMA FROM PS_PEGMAS WHERE NO_INDUK='"""+induk+"""' LIMIT 1"""))
    DBSESSION.close()
    nama = ''
    for row in result:
        nama = row[0] 
    return nama

def cari_rfid_by_induk(induk: str):
    result = DBSESSION.execute(text("""SELECT NO_CHIP FROM PS_PEGMAS WHERE NO_INDUK='"""+induk+"""' LIMIT 1"""))
    DBSESSION.close()
    rfid = ''
    for row in result:
        rfid = row[0] 
    return rfid


def insert_verify_history(find_image:str, found_image:str, found_nik:str, distance:str, raw_data:str):
    with DBSESSION as connection :
        connection.execute(text("""INSERT INTO verify_history (`find_image`, `found_image`, `found_induk`, `distance`, `raw_data`) VALUES ('"""+find_image+"""', '"""+found_image+"""', '"""+found_nik+"""', '"""+distance+"""', '"""+raw_data+"""')"""))
        connection.commit()
        connection.close()

@app.get("/")
def read_root():
    return {"Hello": cari_nama_by_induk('014349'), "uuid7": uuid7str() }

@app.post("/verify64")
async def verify64(jsonFile : VerifyFile):
    tic = time.time()
    try:
        imagefile = base64_to_image(jsonFile.file)
        nparr = np.fromstring(imagefile, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        temp_filename = uuid7str()
        temp_location = "temp/"+temp_filename+".jpg"

        if(jsonFile.rotation=='left'):
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif (jsonFile.rotation=='right'):
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


        cv2.imwrite(temp_location, image) 

        is_facemask = fmd.inference(image_path=temp_location, target_shape=(260, 260))

        if(is_facemask):

            return {
                "success" : False,
                "uuid" : temp_filename,
                "induk" : "",
                "nama" : "",
                "rfid" : "",
                "conf" : "",
                "duration" : "",
                "message" : "Harap melepaskan masker."
            }

        dfs = dfr.find(img_path = temp_location, 
            db_path = FACEPATH, 
            model_name="Facenet512",
            detector_backend="ssd",
            silent=True,
            refresh_database=False,
            to_mysql=False,
            filter_by=jsonFile.filter_by,
            filter_q=jsonFile.filter_q,
        )

        # print(type(dfs))

        if(len(dfs) > 0):
            parent_directory, identity1 = os.path.split(os.path.dirname(dfs[0]['identity'][0]))
            basename = os.path.basename(dfs[0]['identity'][0])
            basedir = parent_directory+"/"+identity1
            distance1 = dfs[0]['distance'][0]
            nama1 = cari_nama_by_induk(identity1)
            rfid1 = cari_rfid_by_induk(identity1)
            
            if(len(dfs[0]) > 1):
                parent_directory, identity2 = os.path.split(os.path.dirname(dfs[0]['identity'][1]))
                distance2 = dfs[0]['distance'][1]

                if(identity1 == identity2) : 
                    insert_verify_history(
                        str(temp_location),
                        str(basedir+"/"+basename),
                        str(identity1),
                        str(distance1),
                        ''
                    )
                    print("#++Identity1: "+str(identity1)+" | Nama: "+nama1+" | Distance: "+str(distance1))
                    
                    toc = time.time()
                    return {
                        "success" : True,
                        "uuid" : temp_filename,
                        "induk" : str(identity1),
                        "nama" : str(nama1),
                        "rfid" : str(rfid1),
                        "conf" : str(distance1),
                        "duration" : str(toc - tic),
                        "message" : ""
                    }
                else :
                    if((distance2-distance1) > 0.02):
                        insert_verify_history(
                            str(temp_location),
                            str(basedir+"/"+basename),
                            str(identity1),
                            str(distance1),
                            ''
                        )
                        print("#+-Identity1: "+str(identity1)+" | Nama: "+nama1+" | Distance: "+str(distance1)+" | Identity2: "+str(identity2)+" | Distance: "+str(distance2))
                        toc = time.time()
                        return {
                            "success" : True,
                            "uuid" : temp_filename,
                            "induk" : str(identity1),
                            "nama" : str(nama1),
                            "rfid" : str(rfid1),
                            "conf" : str(distance1),
                            "duration" : str(toc - tic),
                            "message" : ""
                        }
                    else :
                        insert_verify_history(
                            str(temp_location),
                            'ambiguous',
                            str(identity1),
                            str(distance1),
                            json.dumps(str(dfs))
                        )

                        return {
                            "success" : False,
                            "uuid" : temp_filename,
                            "induk" : "",
                            "nama" : "",
                            "rfid" : "",
                            "conf" : "",
                            "duration" : "",
                            "message" : "Coba Lagi."
                        }
            else :
                insert_verify_history(
                    str(temp_location),
                    str(basedir+"/"+basename),
                    str(identity1),
                    str(distance1),
                    ''
                )

                print("#--Identity1: "+str(identity1)+" | Nama: "+nama1)
                toc = time.time()    
                return {
                    "success" : True,
                    "uuid" : temp_filename,
                    "induk" : str(identity1),
                    "nama" : str(nama1),
                    "rfid" : str(rfid1),
                    "conf" : str(distance1),
                    "duration" : str(toc - tic),
                    "message" : ""
                }
        else :
            print("#--Identity1: Not Found.")

            insert_verify_history(
                str(temp_location),
                'notfound',
                '',
                '',
                json.dumps(str(dfs))
            )

            return {
                "success" : False,
                "uuid" : temp_filename,
                "induk" : "",
                "nama" : "",
                "rfid" : "",
                "conf" : "",
                "duration" : "",
                "message" : "Coba Lagi."
            }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to process image: {e}"})         
    return False

@app.post("/absensi64")
async def absensi64(json : AbsensiModel):
    try:
        uuid = json.uuid
        nik = json.nik
        in_out = json.in_out
        mac_address = json.mac_address
        ts = '' 

        with DBSESSION as connection :
            connection.execute(text("""INSERT INTO absensi (`uuid`, `nik`, `in_out`, `mac_address`) VALUES ('"""+str(uuid)+"""', '"""+str(nik)+"""', '"""+str(in_out)+"""', '"""+str(mac_address)+"""')"""))
            connection.commit()
            connection.close()

        result = DBSESSION.execute(text("""SELECT * FROM absensi WHERE UUID='"""+uuid+"""' ORDER BY ID DESC LIMIT 1"""))
        DBSESSION.close()

        # print(result)
        for row in result:
            ts = row[4]

        return {
            "success" : True,
            "uuid" : uuid,
            "in_out" : in_out,
            "timestamp" : ts,
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to process image: {e}"})         
    return False

@app.post("/get_port")
def get_port():
    port = []
    result = DBSESSION.execute(text("""SELECT * FROM DEVICESS"""))
    DBSESSION.close()

    for row in result:
        port.append({
            "NAME":row[0],
            "PORT":row[1]
        })

    return {
        "success" : True,
        "port" : port
    }