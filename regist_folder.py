from deepface import DeepFace
import recognition as dfr
import os
import uuid
import time

FACEPATH = "KnownFaces"
NEWFACE = "NewFaces"

def regist(path):
    tic = time.time()
    i = 0
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    for imagePath in imagePaths:
        if(os.path.isdir(imagePath)):
            i = i + 1
            parent_directory, induk = os.path.split(imagePath)

            folder = FACEPATH+"/"+induk

            if os.path.isdir(folder):
                print("["+str(i)+"]Exists :"+folder)
            else:
                print("["+str(i)+"]New Folder: "+folder)
                os.mkdir(folder)

            images = [os.path.join(imagePath, f) for f in os.listdir(imagePath)]
            for image in images:
                if '.jpg' in image :
                    to_filename = str(uuid.uuid4())
                    to_location = folder+"/"+to_filename+".jpg"

                    os.replace(image, to_location)

                    representations = dfr.__find_bulk_embeddings(
                        employees=[to_location],
                        model_name="Facenet512",
                        detector_backend="ssd",
                        silent=True,
                        to_mysql=True,
                    )  # add new images

                    if(len(representations) > 0):
                        print("success: "+image+" -> "+to_location)
                    else :
                        print("fail: "+image+" -> "+to_location)
                else : 
                    print("not jpg: "+image)
    toc = time.time()
    print(f"regist duration {toc - tic} seconds")

regist(NEWFACE)
