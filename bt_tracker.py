#!/usr/bin/python3
#
#   Bluetooth Device Tracking MQTT Client for Raspberry Pi (or others)
#
#   Version:    3.0
#   Status:     Working
#   Github:     https://github.com/robmarkoski/bt-mqtt-tracker
#

import os
import time
import logging
import socket

import bluetooth
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

# Add the name and Mac address of the each device. The name will be used as part of the state topic.
devices = [
    {"name": "Device1", "mac": "aa:bb:cc:dd:ee:ff"},
    {"name": "Device2", "mac": "aa:bb:cc:dd:ee:f2"}
    ]

# Provide name of the location where device is (this will form part of the state topic)
LOCATION = "Location"

# Update the follow MQTT Settings for your system.
MQTT_USER = "mqtt"              # MQTT Username
MQTT_PASS = "mqtt_password"     # MQTT Password
MQTT_CLIENT_ID = "bt_mqtt_tracker_%s" % (LOCATION,) # MQTT Client Id
MQTT_HOST_IP = "127.0.0.1"      # MQTT HOST
MQTT_PORT = 1883                # MQTT PORT (DEFAULT 1883)

# Bluetooth and interval settings
USE_BLE = True  # Use Bluetooth LE to discover devices
SCAN_TIME = 30  # Interval Between Scans
BLU_TIMEOUT = 3 # How long during scan before there is a timeout.

# Set up logging.
LOG_NAME = "bt_tracker.log"      # Name of log file
LOG_LEVEL = logging.NOTSET       # Change to DEBUG for debugging. INFO For basic Logging or NOTSET to turn off

MQTT_AUTH = {
    'username': MQTT_USER,
    'password': MQTT_PASS
}

# SHOULDNT NEED TO CHANGE BELOW
VERSION = "3.0"
LOG_FORMAT = "%(asctime)-15s %(message)s"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__)) + "/"
LOG_FILE = SCRIPT_DIR + LOG_NAME
logging.basicConfig(filename=LOG_FILE,
                    level=LOG_LEVEL,
                    format=LOG_FORMAT,
                    datefmt='%Y-%m-%d %H:%M:%S')

if USE_BLE:
    from bluetooth.ble import DiscoveryService
    ble_service = DiscoveryService()

logging.info("Announce devices to HomeAssistant")
for device in devices:
    mac_short = device['mac'].replace(':','').lower()
    publish.single("homeassistant/binary_sensor/bt_tracker_%s_%s/config" % (LOCATION, device['name']),
        payload=    '{"stat_t":"bt_mqtt_tracker/presence/%s/%s", "avty_t": "bt_mqtt_tracker/available/%s", "name": "%s", "dev":{"ids":"%s","cns": [["mac", "%s"]], "name": "%s", "mf": "BT MQTT Tracker", "mdl": "%s", "sw": "%s"}, "uniq_id": "%s_%s", "dev_cla": "presence"}' % (LOCATION, device['name'], LOCATION, device['name'], mac_short, device['mac'], device['name'], socket.gethostname(), VERSION, LOCATION, mac_short),
        retain=True,
        hostname=MQTT_HOST_IP,
        client_id=MQTT_CLIENT_ID,
        auth=MQTT_AUTH,
        port=MQTT_PORT,
        protocol=mqtt.MQTTv311)

logging.info("Set Tracker as available")
publish.single("bt_mqtt_tracker/available/%s" % (LOCATION,),
    payload="online",
    retain=True,
    hostname=MQTT_HOST_IP,
    client_id=MQTT_CLIENT_ID,
    auth=MQTT_AUTH,
    port=MQTT_PORT,
    protocol=mqtt.MQTTv311)

try:
    logging.info("Starting BLE Tracker Server")
    while True:
        if USE_BLE:
            ble_devices = ble_service.discover(2)
        for device in devices:
            mac = device['mac'].upper()
            logging.debug("Checking for {}".format(mac))
            result = False
            if USE_BLE:
                for address, name in ble_devices.items():
                    result = address.upper() == mac
                    if result:
                        break
            else:
                result = bluetooth.lookup_name(mac, timeout=BLU_TIMEOUT)
            if result:
                device['state'] = "ON"
                logging.debug("Device Found!")
            else:
                device['state'] = "OFF"
                logging.debug("Device Not Found!")
            try:
                publish.single("bt_mqtt_tracker/presence/%s/%s", (LOCATION, device['name']),
                    payload=device['state'],
                    hostname=MQTT_HOST_IP,
                    client_id=MQTT_CLIENT_ID,
                    auth=MQTT_AUTH,
                    port=MQTT_PORT,
                    protocol=mqtt.MQTTv311
                )
            except:
                logging.exception("MQTT Publish Error")
        time.sleep(SCAN_TIME)
except KeyboardInterrupt:
    logging.info("KEY INTERRUPT - STOPPING SERVER")
except:
    logging.exception("BLUETOOTH SERVER ERROR")

publish.single("bt_mqtt_tracker/available/%s" % (LOCATION,),
    payload="offline",
    retain=True,
    hostname=MQTT_HOST_IP,
    client_id=MQTT_CLIENT_ID,
    auth=MQTT_AUTH,
    port=MQTT_PORT,
    protocol=mqtt.MQTTv311)
