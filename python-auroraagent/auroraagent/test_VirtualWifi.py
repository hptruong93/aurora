import VirtualWifi
import psutil
import sys
import Database
import pprint
import time
import subprocess

db_config = {
	'last_known_config': {
		'init_user_id_database': {
			'1': [], 
			'default_user': ['default_slice']
		},
		'region': 'mcgill', 
		'init_database': {
			'default_slice': {
				'VirtualInterfaces': [], 
				'RadioInterfaces': [],
				'VirtualBridges': []
			}
		}, 
		'init_hardware_database': {
			'wifi_radio': {
				'number_radio_free': 40, 
				'max_bss_per_radio': '1',
				'radio_list': [
					{
						'disabled': 1,
						'macaddr': '', 
						'name': 'radio0', 
						'bss_list': [], 
						'country': 'CA', 
						'if_name': 'wlan0', 
						'txpower': '20',
						'hwmode': 'abg', 
						'bss_limit': '4', 
						'channel': '2'
					}, 
					{
						'macaddr': '00:80:48:75:1e:4c', 
						'name': 'radio1', 
						'bss_list': [], 
						'if_name': 'wlan1', 
						'disabled': 1, 
						'hwmode': '11g',
						'bss_limit': '4', 
						'channel': '11'
					}
				], 
				'number_radio': 2
			}, 
			'aurora_version': '0.2', 
			'firmware': 'OpenWRT',
			'memory_mb': 248, 
			'free_disk': 166, 
			'firmware_version': 'r39154'
		}
	}, 
	'default_config': {
		'init_hardware_database': {
			'wifi_radio': {
				'number_radio_free': '0', 
				'max_bss_per_radio': '4', 
				'radio_list': [], 
				'number_radio': '0'
			},
			'aurora_version': '0.2', 
			'firmware': 'OpenWRT', 
			'memory_mb': '256', 
			'free_disk': '256', 
			'firmware_version': 
			'r39154'
		},
 		'default_active_slice': 'default_slice', 
 		'init_database': {
 			'default_slice': {
 				'VirtualInterfaces': [],
 				'RadioInterfaces': [], 
 				'VirtualBridges': []
 			}
 		}, 
 		'init_user_id_database': {
 			'default_user': ['default_slice']
 		}
 	}
}

database = Database.Database(db_config)

# database = {"last_known_config": {
#         "init_user_id_database": {
#             "1": [], 
#             "default_user": [
#                 "default_slice"
#             ]
#         }, 
#         "region": "mcgill", 
#         "init_database": {
#             "default_slice": {
#                 "VirtualInterfaces": [], 
#                 "RadioInterfaces": [], 
#                 "VirtualBridges": []
#             }
#         }, 
#         "init_hardware_database": {
#             "wifi_radio": {
#                 "number_radio_free": 1, 
#                 "max_bss_per_radio": "4", 
#                 "radio_list": [
#                     {
#                         "disabled": 1, 
#                         "macaddr": "00:80:48:7a:b3:70", 
#                         "name": "radio0", 
#                         "bss_list": [], 
#                         "country": "CA", 
#                         "if_name": "wlan0", 
#                         "txpower": "20", 
#                         "hwmode": "abg", 
#                         "bss_limit": "4", 
#                         "channel": "2"
#                     }
#                 ], 
#                 "number_radio": 1
#             }, 
#             "aurora_version": "0.2", 
#             "firmware": "OpenWRT", 
#             "memory_mb": 248, 
#             "free_disk": 194, 
#             "firmware_version": "r39154"
#         }
#     }, 
#     "rabbitmq_password": "let_me_in", 
#     "rabbitmq_username": "access_point", 
#     "rabbitmq_host": "10.5.8.3", 
#     "region": "mcgill", 
#     "queue": "openflow1", 
#     "rabbitmq_reply_queue": "AuroraManager", 
#     "default_config": {
#         "init_hardware_database": {
#             "wifi_radio": {
#                 "number_radio_free": "0", 
#                 "max_bss_per_radio": "4", 
#                 "radio_list": [], 
#                 "number_radio": "0"
#             }, 
#             "aurora_version": "0.2", 
#             "firmware": "OpenWRT", 
#             "memory_mb": "256", 
#             "free_disk": "256", 
#             "firmware_version": "r39154"
#         }, 
#         "default_active_slice": "default_slice", 
#         "init_database": {
#             "default_slice": {
#                 "VirtualInterfaces": [], 
#                 "RadioInterfaces": [], 
#                 "VirtualBridges": []
#             }
#         }, 
#         "init_user_id_database": {
#             "default_user": [
#                 "default_slice"
#             ]
#         }
#     }
# }

configuration  = [{'attributes': {'txpower': '20', 'name': 'radio0', 'country': 'CA', 'disabled': '0', 'hwmode': 'abg', 'channel': '2'}, 'flavor': 'wifi_radio'}, \
{'attributes': {'encryption_type': 'wep-open', 'radio': 'radio0', 'key': '23456', 'if_name': 'wlan0', 'name': 'test0'}, 'flavor': 'wifi_bss'}]

configuration2  = [{'attributes': {'txpower': '20', 'name': 'radio1', 'country': 'CA', 'disabled': '0', 'hwmode': 'abg', 'channel': '2'}, 'flavor': 'wifi_radio'}, \
{'attributes': {'encryption_type': 'wep-open', 'radio': 'radio1', 'key': '23456', 'if_name': 'wlan1', 'name': 'test1'}, 'flavor': 'wifi_bss'}]

pprint.pprint(database.hw_database)


test_VW = VirtualWifi.VirtualWifi(database)


print "------------------------finished setting up-----------------------------------"

print
print "__________------___---__---creating slice 1"

test_VW.create_slice(configuration)

time.sleep(2)

print
print "__________------___---__---creating slice 2"

test_VW.create_slice(configuration2)

time.sleep(1)

print "______-------------___-----_----_---__---__-checking for running hostapd processes: "

num_hostapd = 0
for process in psutil.process_iter():
    if process.name() == "hostapd":
        num_hostapd = num_hostapd + 1

print num_hostapd

time.sleep(5)

print
print "__________------___---__---deleting slice 1"

test_VW.delete_slice(configuration2)

time.sleep(2)

print
print "__________------___---__---deleting slice 2"

test_VW.delete_slice(configuration)

test_VW = None

print "______-------------___-----_----_---__---__-checking for running hostapd processes: "

num_hostapd = 0
for process in psutil.process_iter():
    if process.name() == "hostapd":
        num_hostapd = num_hostapd + 1

print num_hostapd

print "finished testing VirtualWifi - -------------------------------------"