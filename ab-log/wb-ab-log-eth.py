#!/usr/bin/python

from rocket import Rocket
from urlparse import urlparse, parse_qs
from urllib2 import urlopen
import logging
import logging.handlers
import mosquitto
import time

PREFIX = '/devices/ab-log/controls/'
CHECK_RELAY_STATE = False

mqttc = mosquitto.Mosquitto()

def ab_log_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'text/plain')]

    start_response(status, headers)

    controller = environ.get('REMOTE_ADDR', 'unknown')
    query = parse_qs(environ.get('QUERY_STRING', ''))
    port = query.get('pt')
    if port == None:
        return ['']
    mode = query.get('m')
    if mode == None:
        mode = '1'
    else:
        mode = '0'
    # mqttc.reconnect()
    mqttc.publish(PREFIX + '{}_Input_{}'.format(controller, port[0]), mode)
    cnt = query.get('cnt')
    if cnt != None:
        mqttc.publish(PREFIX + '{}_Input_{}/count'.format(controller, port[0]), cnt[0])
    
    return ['']

def on_connect(client, userdata, rc):
    log.info('MQTT Connected with RC {}'.format(rc))
    client.subscribe(PREFIX + '+/on')
    
def on_message(client, userdata, msg):
    log.info('Receive: {} {}'.format(msg.topic, msg.payload))
    data = msg.topic.split('/')[4].split('_')
    controller = data[0]
    relay = data[2]
    log.info('Receive: Controller {} Relay {}'.format(controller, relay))
    r = urlopen('http://{}/sec/?cmd={}:{}'.format(controller, relay, msg.payload))
    if r != None:
        if CHECK_RELAY_STATE:
            r = urlopen('http://{}/sec/?cmd=get&pt={}'.format(controller, relay))
            if r != None:
                response = r.read()
                if response == 'ON':
                    state = '1'
                else:
                    state = '0'
        else:
            state = msg.payload
        client.publish(PREFIX + '{}_Relay_{}'.format(controller, relay), state)

if __name__ == '__main__':
    log = logging.getLogger('Rocket')
    log.setLevel(logging.INFO)
    fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    h = logging.FileHandler('/var/log/wb-ab-log-eth.log')
    h.setFormatter(fmt)
    log.addHandler(h)

    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
                    
    mqttc.connect("localhost", 1883)
    
    server = Rocket(interfaces=('0.0.0.0', 9999),
                    method='wsgi', 
                    app_info={"wsgi_app":ab_log_app})
                    
    mqttc.loop_start()
    server.start()
    mqttc.loop_stop()
    mqttc.disconnect()
