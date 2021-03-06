# Import Libraries
import time
import datetime
from picamera import PiCamera
from picamera.array import PiRGBArray
from threading import Thread
import numpy as np
from PIL import Image
import requests
import cv2

filename = "motion.jpg"

# Camera Settings
CAMERA_WIDTH = 800
CAMERA_HEIGHT = 600
CAMERA_HFLIP = False
CAMERA_VFLIP = True
CAMERA_FRAMERATE = 15

# Motion Settings
threshold = 10   # How Much a pixel has to change (1 - 254)
sensitivity = 350000  # How Many pixels need to change for motion detection
delaytime = 5  # delay time when motion detect (Second)

# Line Notify Settings
url = "https://notify-api.line.me/api/notify"
token = ''  # Line Notify Token
headers = {'Authorization': 'Bearer ' + token}
alertMSG = "ตรวจพบการเคลื่อนไหว"  # Alert Message

# opencv setting
coordinates = (30, 50)
font = cv2.FONT_HERSHEY_SIMPLEX
fontscale = 0.8
color = (255, 255, 255)
thickness = 2
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
face_color = (0, 255, 0)


class PiVideoStream:
    def __init__(self, resolution=(CAMERA_WIDTH, CAMERA_HEIGHT), framerate=CAMERA_FRAMERATE, rotation=0, hflip=False, vflip=False):
        # initialize the camera and stream
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.rotation = rotation
        self.camera.framerate = framerate
        self.camera.hflip = hflip
        self.camera.vflip = vflip
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(
            self.rawCapture, format="rgb", use_video_port=True)

        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.stopped = False

    def start(self):
        # start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        for f in self.stream:
            # grab the frame from the stream and clear the stream in
            # preparation for the next frame
            self.frame = f.array
            self.rawCapture.truncate(0)

            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True


def showMessage(functionName, messageStr):
    print("%s - %s " % (functionName, messageStr))


def checkForMotion(data1, data2):
    # Find motion between two data streams based on sensitivity and threshold
    motionDetected = False
    pixColor = 3  # red=0 green=1 blue=2 all=3  default=1
    if pixColor == 3:
        pixChanges = (np.absolute(data1-data2) > threshold).sum()/3
    else:
        pixChanges = (np.absolute(
            data1[..., pixColor]-data2[..., pixColor]) > threshold).sum()
    showMessage("Debug", pixChanges)
    if pixChanges > sensitivity:
        motionDetected = True
        msgStr = ("Found Motion sensitivity=%s changes=%s" %
                  (sensitivity, pixChanges))
        showMessage("Detected", msgStr)
    return motionDetected


def sendNotify():
    data = {'message': alertMSG}
    lineImage = {'imageFile': open(filename, 'rb')}
    session = requests.Session()
    session_post = session.post(
        url, headers=headers, files=lineImage, data=data)
    showMessage("Notify", session_post.text)


def getTime():
    now = datetime.datetime.now()
    now = now.strftime("%Y-%m-%d %H:%M:%S %p")
    return now


def saveArrayToImage(data):
    im = Image.fromarray(data)
    im.save(filename)


def addTextAndFaceDetection():
    # load image
    img = cv2.imread(filename)
    # face detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray)
    # Draw rectangle around the faces
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), face_color, thickness)
    # add text to image
    cv2.putText(img, getTime(), coordinates,
                font, fontscale, color, thickness)
    # save image
    cv2.imwrite(filename, img)


def Main():
    msgStr = "Checking for Motion"
    showMessage("Main", msgStr)
    frame_1 = vs.read()
    time.sleep(0.25)
    while True:
        frame_2 = vs.read()
        if checkForMotion(frame_1, frame_2):
            # array to image
            saveArrayToImage(frame_1)
            addTextAndFaceDetection()
            sendNotify()
            time.sleep(delaytime)  # sleep when detected
            frame_1 = vs.read()  # reset image when detected
        else:
            frame_1 = frame_2
            time.sleep(0.2)
    return


if __name__ == '__main__':
    try:
        msgStr = "Loading..."
        showMessage("Init", msgStr)
        vs = PiVideoStream().start()  # Initialize video stream
        vs.camera.hflip = CAMERA_HFLIP
        vs.camera.vflip = CAMERA_VFLIP
        time.sleep(2.0)  # Let camera warm up
        Main()

    except KeyboardInterrupt:
        print("\nExiting Program")
