from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os.path
import pickle
import threading
import time
import urllib.request

_FILENAME = 'subscribers.sub'
MAGIC_NUMBER = 201705019
FILE_VERSION = 1

class UPNPHTTPServerHandler(BaseHTTPRequestHandler):
    """ A HTTP Handler that serves the UPNP XML files
    """

    def do_GET(self):
        if self.path == '/smartcam.xml':
            self.send_response(200)
            self.send_header('Content-type', 'text/xml')
            self.end_headers()
            self.wfile.write(self.get_device_xml().encode())
            return
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Not found,')
            return
    
    def do_POST(self):

        content_len = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_len).decode('utf-8'))

        if self.server.server_PSK == self.headers['X-Auth-PSK'] and body['method'] == 'getStatus':
            self.send_status()

    def do_SUBSCRIBE(self):

        subscriber = self.headers['CALLBACK'][1:-1]
        subscription_end = time.time() + int(self.headers['TIMEOUT'][7:])
        
        if self.server.server_PSK == self.headers['X-Auth-PSK']:
            self.server.subscribers[subscriber] = subscription_end

            with open(_FILENAME, 'w+b') as fh:
                pickle.dump(MAGIC_NUMBER, fh)
                pickle.dump(FILE_VERSION, fh)
                pickle.dump(len(self.server.subscribers), fh)
                pickle.dump(self.server.subscribers, fh)

    def send_status(self):

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(self.server.motion_status.encode())

    def get_device_xml(self):

        xml = """<?xml version="1.0"?>
<root>
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:SmartCamera:1</deviceType>
        <friendlyName>SmartCamera</friendlyName>
        <manufacturer>Sanfe75</manufacturer>
        <manufacturerURL>https://github.com/Sanfe75</manufacturerURL>
        <modelDescription>SmartCamera Computer Based Camera</modelDescription>
        <modelName>SmartCamera 01</modelName>
        <modelNumber>SC01</modelNumber>
        <modelURL>https://github.com/Sanfe75/SmartCamera</modelURL>
        <serialNumber>0.1</serialNumber>
        <UDN>uuid:{uuid}</UDN>
        <serviceList>
            <service>
               <serviceType>urn:schemas-upnp-org:service:PresenceSensor:1</serviceType> 
            </service>
        </serviceList>
        <presentationURL>{presentation_url}</presentationURL>
    </device>
</root> """
        return xml.format(uuid=self.server.uuid, presentation_url=self.server.presentation_url)


class UPNPHTTPServerBase(HTTPServer):
    """ A simple HTTPserver that knows the information about a UPNP device.
    """

    def __init__(self, server_address, request_handler_class):

        HTTPServer.__init__(self, server_address, request_handler_class)
        self.port = None
        self.uuid = None
        self.presentation_url = None
        self.subscribers = {}
        if os.path.isfile(_FILENAME):
            with open(_FILENAME, 'rb') as fh:
                magic = pickle.load(fh)
                if magic != MAGIC_NUMBER:
                    raise IOError('Unrecognized file type')
                version = pickle.load(fh)
                if version != FILE_VERSION:
                    raise IOError('Unrecognized file version')
                num_subscribers = pickle.load(fh)
                if num_subscribers > 0:
                    self.subscribers = pickle.load(fh)

        self.update_subscribers()
        self.motion_status = 'No motion'

    def update_status(self, status):

        self.motion_status = status
        self.update_subscribers()
        for addr, expr in self.subscribers.items():
            data = self.motion_status.encode('ascii')
            req = urllib.request.Request(addr, data)
            response = urllib.request.urlopen(req)

    def update_subscribers(self):

        now = time.time()
        subscribers = {key: expr for key, expr in self.subscribers.items() if expr >= now}

        if len(self.subscribers) != len(subscribers):
            self.subscribers = subscribers
            with open(_FILENAME, 'w+b') as fh:
                pickle.dump(MAGIC_NUMBER, fh)
                pickle.dump(FILE_VERSION, fh)
                pickle.dump(len(self.subscribers), fh)
                pickle.dump(self.subscribers, fh)
                

class UPNPHTTPServer(threading.Thread):
    """ A Thread that run UPNPHTTPServerBase
    """

    def __init__(self, port, uuid, presentation_url, server_PSK):

        threading.Thread.__init__(self, daemon=True)
        self.server = UPNPHTTPServerBase(('', port), UPNPHTTPServerHandler)
        self.server.port = port
        self.server.uuid = uuid
        self.server.presentation_url = presentation_url
        self.server.server_PSK = server_PSK

    def run(self):

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.kill()
        finally:
            self.server.server_close()
