#
#Implementation of SSDP Server
#
import random
import socket
import threading
import time
from email.utils import formatdate

SSDP_PORT = 1900
SSDP_ADDR = '239.255.255.250'
SERVER_ID = 'Smart Camera Server'

class SSDPServerBase:
    """A class implementing a SSDP Server.
    """
    known = {}

    def __init__(self):
        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        addr = socket.inet_aton(SSDP_ADDR)
        interface = socket.inet_aton('0.0.0.0')
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, addr + interface)
        self.sock.bind(('0.0.0.0', SSDP_PORT))
        self.sock.settimeout(1)

        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.datagram_received(data, addr)
            except socket.timeout:
                continue
        self.shutdown()

    def shutdown(self):
        for st in self.known:
            if self.known[st]['MANIFESTATION'] == 'local':
                self.do_byebye(st)

    def datagram_received(self, data, host_port):
        """Handle a received multicast datagram.
        """
        (host, port) = host_port

        try:
            header, payload = data.decode().split('\r\n\r\n')[:2]
        except ValueError as error:
            return

        lines = header.split('\r\n')
        cmd = lines[0].split(' ')
        lines = map(lambda x: x.replace(': ',':', 1), lines[1:])
        lines = filter(lambda x: len(x) > 0, lines)

        headers = [x.split(':', 1) for x in lines]
        headers = dict(map(lambda x: (x[0].lower(), x[1]), headers))

        if cmd[0] == 'M-SEARCH' and cmd[1] == '*':
            #SSDP discovery
            self.discovery_request(headers, host, port)
        elif cmd[0] == 'NOTIFY' and cmd[1] == '*':
            # SSDP notify
            pass
        else:
            pass

    def register(self, manifestation, usn, st, location, server=SERVER_ID,
            cache_control='max-age=1800', silent=False, host=None):

        self.known[usn] = {}
        self.known[usn]['USN'] = usn
        self.known[usn]['LOCATION'] = location
        self.known[usn]['ST'] = st
        self.known[usn]['EXT'] = ''
        self.known[usn]['SERVER'] = server
        self.known[usn]['CACHE-CONTROL'] = cache_control
        self.known[usn]['MANIFESTATION'] = manifestation
        self.known[usn]['SILENT'] = silent
        self.known[usn]['HOST'] = host
        self.known[usn]['last-seen'] = time.time()
        
        if manifestation == 'local' and self.sock:
            self.do_notify(usn)

    def send_it(self, response, destination, delay, usn):
        try:
            self.sock.sendto(response.encode(), destination)
        except (AttributeError, socket.error) as error:
            pass

    def discovery_request(self, headers, host, port):
        """Process a discovery request
        """

        for i in self.known.values():
            if i['MANIFESTATION'] == 'remote':
                continue
            if headers['st'] == 'ssdp:all' and i['SILENT']:
                continue
            if i['ST'] == headers['st'] or headers['st'] == 'ssdp:all':
                response = ['HTTP/1.1 200 OK']

                usn = None
                for k, v in i.items():
                    if k == 'USN':
                        usn = v
                    if k not in ('MANIFESTATION', 'SILENT', 'HOST'):
                        response.append('{0}: {1}'.format(k, v))

                if usn:
                    response.append('DATE: {0}'.format(formatdate(timeval=None, localtime=False,usegmt=True)))

                    response.extend(('', ''))
                    delay = random.randint(0, int(headers['mx']))

                    self.send_it('\r\n'.join(response), (host, port), delay, usn)

    def do_notify(self, usn):

        if self.known[usn]['SILENT']:
            return
        
        resp = ['NOTIFY * http/1.1',
                'HOST: {1}:{2}'.format(SSDP_ADDR, SSDP_PORT),
                'NTS: ssdp:alive',]

        stcpy = dict(self.known[usn].items())
        stcpy['NT'] = stcopy['ST']
        del stcpy['ST']
        del stcpy['MANIFESTATION']
        del stcpy['SILENT']
        del stcpy['HOST']
        del stcpy['last-seen']

        resp.extend(map(lambda x: ': '.join(x), stcpy.items()))
        resp.extend(('', ''))

        try:
            self.sock.sendto('\r\n'.join(resp).encode(), (SSDP_ADDR, SSDP_PORT))
            self.sock.sendto('\r\n'.join(resp).encode(), (SSDP_ADDR, SSDP_PORT))
        except (AttributeError, socket.error) as error:
            pass


    def do_byebye(self, usn):

        resp = ['NOTIFY * http/1.1',
                'HOST: {1}:{2}'.format(SSDP_ADDR, SSDP_PORT),
                'NTS: ssdp:alive',]
        try:

            stcpy = dict(self.known[usn].items())
            stcpy['NT'] = stcopy['ST']
            del stcpy['ST']
            del stcpy['MANIFESTATION']
            del stcpy['SILENT']
            del stcpy['HOST']
            del stcpy['last-seen']
            resp.extend(map(lambda x: ': '.join(x), stcpy.items()))
            resp.extend(('', ''))
            if self.sock:
                try:
                    self.sock.sendoto('\r\n'.join(resp), (SSDP_ADDR, SSDP_PORT))
                except (AttributeError, socket.error) as error:
                    pass
        except KeyError as error:
            pass

class SSDPServer(threading.Thread):

    def __init__(self, device_uuid, local_ip, server_port):
        
        threading.Thread.__init__(self, daemon=True)
        self.server = SSDPServerBase()
        self.server.register('local',
                'uuid:{0}::upnp:rootdevice'.format(device_uuid),
                'urn:schemas-upnp-org:device:SmartCamera:1',
                'http://{0}:{1}/smartcam.xml'.format(local_ip, server_port))

    def run(self):
        try:
            self.server.run()
        except KeyboardInterrupt:
            pass
