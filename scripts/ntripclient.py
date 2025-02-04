#!/usr/bin/python

import rospy
from datetime import datetime

#from nmea_msgs.msg import Sentence
from rtcm_msgs.msg import Message

from base64 import b64encode
from threading import Thread

from httplib import HTTPConnection
from httplib import IncompleteRead

''' This is to fix the IncompleteRead error
    http://bobrochel.blogspot.com/2010/11/bad-servers-chunked-encoding-and.html'''
import httplib
def patch_http_response_read(func):
    def inner(*args):
        try:
            return func(*args)
        except httplib.IncompleteRead, e:
            return e.partial
    return inner
httplib.HTTPResponse.read = patch_http_response_read(httplib.HTTPResponse.read)

class ntripconnect(Thread):
    def __init__(self, ntc):
        super(ntripconnect, self).__init__()
        self.ntc = ntc
        self.stop = False
        self.time_of_last_recv_msg = rospy.get_rostime()

    def run(self):

        headers = {
            'Ntrip-Version': 'Ntrip/2.0',
            'User-Agent': 'NTRIP ntrip_ros',
            'Connection': 'close',
            'Authorization': 'Basic ' + b64encode(self.ntc.ntrip_user + ':' + str(self.ntc.ntrip_pass))
        }
        try:
            connection = HTTPConnection(self.ntc.ntrip_server) #, timeout=5.0)
            connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
            response = connection.getresponse()
        except:
            rospy.logerr("NTRIP-client - ERROR: Not able to connect to NTRIP-server!")
            return

        rospy.loginfo("NTRIP-client - Connection to NTRIP-server established.")

        if response.status != 200: raise Exception("blah")
        buf = ""
        rmsg = Message()
        restart_count = 0
        while not self.stop:
            '''
            data = response.read(100)
            pos = data.find('\r\n')
            if pos != -1:
                rmsg.message = buf + data[:pos]
                rmsg.header.seq += 1
                rmsg.header.stamp = rospy.get_rostime()
                buf = data[pos+2:]
                self.ntc.pub.publish(rmsg)
            else: buf += data
            '''

            ''' This now separates individual RTCM messages and publishes each one on the same topic '''
            data = response.read(1)

            self.time_of_last_recv_msg = rospy.get_rostime()

            if len(data) != 0:
                if ord(data[0]) == 211:
                    buf += data
                    data = response.read(2)
                    buf += data
                    cnt = ord(data[0]) * 256 + ord(data[1])
                    data = response.read(2)
                    buf += data
                    typ = (ord(data[0]) * 256 + ord(data[1])) / 16
                    #print (str(datetime.now()), cnt, typ)
                    cnt = cnt + 1
                    for x in range(cnt):
                        data = response.read(1)
                        buf += data
                    rmsg.message = buf
                    rmsg.header.seq += 1
                    rmsg.header.stamp = rospy.get_rostime()
                    self.ntc.pub.publish(rmsg)
                    buf = ""
                #else: rospy.loginfo(data)
            else:
                ''' If zero length data, close connection and reopen it '''
                restart_count = restart_count + 1
                #rospy.loginfo("NTRIP-client - Zero length ", restart_count)
                connection.close()
                connection = HTTPConnection(self.ntc.ntrip_server)
                connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, headers)
                response = connection.getresponse()
                if response.status != 200: raise Exception("blah")
                buf = ""

        connection.close()
        rospy.logerr("NTRIP-client - ERROR: Connection-thread stopped!")


class ntripclient:
    def __init__(self):
        rospy.init_node('ntripclient', anonymous=True)

        self.rtcm_topic = rospy.get_param('~rtcm_topic', 'rtcm')
        self.nmea_topic = rospy.get_param('~nmea_topic', 'nmea')

        self.ntrip_server = rospy.get_param('~ntrip_server')
        self.ntrip_user = rospy.get_param('~ntrip_user')
        self.ntrip_pass = rospy.get_param('~ntrip_pass')
        self.ntrip_stream = rospy.get_param('~ntrip_stream')
        self.nmea_gga = rospy.get_param('~nmea_gga')

        self.pub = rospy.Publisher(self.rtcm_topic, Message, queue_size=10)
        self.timer = rospy.Timer(rospy.Duration(1), self.timeout_checker_callback)

        self.connection = None
        self.connection = ntripconnect(self)
        self.connection.start()

    def run(self):
        rospy.spin()
        if self.connection is not None:
            self.connection.stop = True

    def timeout_checker_callback(self, timer):
        time_diff = rospy.get_rostime() - self.connection.time_of_last_recv_msg
        if time_diff > rospy.Duration(6):
            rospy.logerr("NTRIP-client - Timeout detected! Try to reconnect to NTRIP-server!")
            self.connection.stop = True
            self.connection = None
            self.connection = ntripconnect(self)
            self.connection.start()


if __name__ == '__main__':
    c = ntripclient()
    c.run()

