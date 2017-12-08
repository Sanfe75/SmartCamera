from lib.ssdp import SSDPServer
from lib.upnp_http_server import UPNPHTTPServer
from lib.videostream import WebcamVideoStream as VideoStream
import argparse
import cv2
import datetime
import imutils
import json
import numpy as np
import socket
import time
import uuid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--conf', type=str, default="conf.json",
            help='Path to the JSON configuration file, default is conf.json in the program folder')
    arg = vars(ap.parse_args())
    try:
        conf = json.load(open(arg['conf']))
    except FileNotFoundError as error:
        print(error)
        return
    server_port = conf['upnp_port']
    device_uuid = uuid.uuid4()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(('239.255.255.250', 1900))
    local_ip = sock.getsockname()[0]
    sock.close()

    http_server = UPNPHTTPServer(server_port, uuid=device_uuid, presentation_url='http://{}/'.format(local_ip), server_PSK=conf['server_PSK'])
    http_server.start()

    ssdp = SSDPServer(device_uuid, local_ip, server_port)
    ssdp.start()

    stream = VideoStream(conf['source'], conf['resolution'], conf['fps']).start()
    time.sleep(conf['camera_warmup_time'])

    background = None
    motion_counter = 0
    kernel = np.ones((3,3), np.uint8)
    prev_status = "No motion"

    while True:
        
        frame = stream.read()
        timestamp = datetime.datetime.now()
        status = "No motion"
        motion = False

        frame = imutils.resize(frame, width=500)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if background is None:
            background = np.float32(gray)
            continue

        cv2.accumulateWeighted(gray, background, 0.5)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(background))
        thresh = cv2.threshold(frame_delta, conf['delta_thresh'], 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, kernel, iterations=2)
        contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if imutils.is_cv2() else contours[1]

        for c in contours:
            if cv2.contourArea(c) < conf['min_area']:
                continue

            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            motion = True

        ts = timestamp.strftime('%A %d %B %Y %I:%M:%S%p')
        cv2.putText(frame, '{} detected'.format(status), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        if motion:
            motion_counter += 1

            if motion_counter >= conf['min_motion_frames']:
                status = "Motion"
        else:
            motion_counter = 0

        if status != prev_status:
            http_server.server.update_status(status)
            prev_status = status

main()
