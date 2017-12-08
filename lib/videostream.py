from threading import Thread
import cv2

class WebcamVideoStream:

    def __init__(self, src=0, resolution=None, fps=None):

        self.stream = cv2.VideoCapture(src)
        if resolution is not None:
            self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        if fps is not None:
            self.stream.set(cv2.CAP_PROP_FPS, fps)
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False

    def start(self):

        Thread(target=self.update, args=()).start()
        return self

    def update(self):

        while True:
            if self.stopped:
                return
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):

        return self.frame

    def stop(self):

        self.stopped = True
