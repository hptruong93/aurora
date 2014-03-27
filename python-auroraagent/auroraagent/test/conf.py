AGENT_INIT_CONFIG = \
{
    "default_config": {
        "init_hardware_database": {
            "wifi_radio": {
                "number_radio_free": "0", 
                "max_bss_per_radio": "4", 
                "radio_list": [], 
                "number_radio": "0"
            }, 
            "aurora_version": "0.2", 
            "firmware": "OpenWRT", 
            "memory_mb": "256", 
            "free_disk": "256", 
            "firmware_version": "r39154"
        }, 
        "default_active_slice": "default_slice", 
        "init_database": {
            "default_slice": {
                "VirtualInterfaces": [], 
                "RadioInterfaces": [], 
                "VirtualBridges": []
            }
        }, 
        "init_user_id_database": {
            "default_user": [
                "default_slice"
            ]
        }
    }
}

MAIN_SLICE_CONFIG_R0 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_radio",
            "attributes" : 
                {
                    "name" : "radio0",
                    "channel" : "1",
                    "txpower" : "20",
                    "disabled" : "0",
                    "country" : "CA",
                    "hwmode" : "abg"   
                }
        },
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "MAIN",
                    "radio" : "radio0",
                    "if_name" : "wlan0",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"ovs",
            "attributes":   
                {
                    "name":"main-br",
                    "interfaces":
                        ["vwlan0","veth0"],
                    "bridge_settings":
                        {
                            "controller":"tcp:10.5.8.3",
                            "dpid":"00:00:00:00:00:01"
                        },
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth0",
                    "mac":"00:00:00:00:00:10"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan0",
                    "name":"vwlan0",
                    "mac":"00:00:00:00:00:11"
                }
        }
    ]
}

SECOND_SLICE_CONFIG_R0 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "SECOND",
                    "radio" : "radio0",
                    "if_name" : "wlan0-1",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"linux_bridge",
            "attributes":   
                {
                    "name":"second-br",
                    "interfaces":
                        ["vwlan0-1","veth1"],
                    "bridge_settings":{},
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth1",
                    "mac":"00:00:00:00:00:20"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan0-1",
                    "name":"vwlan0-1",
                    "mac":"00:00:00:00:00:21"
                }
        }
    ]
}

THIRD_SLICE_CONFIG_R0 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "THIRD",
                    "radio" : "radio0",
                    "if_name" : "wlan0-2",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"linux_bridge",
            "attributes":   
                {
                    "name":"third-br",
                    "interfaces":
                        ["vwlan0-2","veth2"],
                    "bridge_settings":{},
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth2",
                    "mac":"00:00:00:00:00:30"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan0-2",
                    "name":"vwlan0-2",
                    "mac":"00:00:00:00:00:31"
                }
        }
    ]
}

FOURTH_SLICE_CONFIG_R0 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "FOURTH",
                    "radio" : "radio0",
                    "if_name" : "wlan0-3",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"linux_bridge",
            "attributes":   
                {
                    "name":"fourth-br",
                    "interfaces":
                        ["vwlan0-3","veth3"],
                    "bridge_settings":{},
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth3",
                    "mac":"00:00:00:00:00:40"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan0-3",
                    "name":"vwlan0-3",
                    "mac":"00:00:00:00:00:41"
                }
        }
    ]
}



MAIN_SLICE_CONFIG_R1 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_radio",
            "attributes" : 
                {
                    "name" : "radio1",
                    "channel" : "1",
                    "txpower" : "20",
                    "disabled" : "0",
                    "country" : "CA",
                    "hwmode" : "abg"   
                }
        },
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "MAIN_R1",
                    "radio" : "radio1",
                    "if_name" : "wlan1",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"ovs",
            "attributes":   
                {
                    "name":"main-br-r1",
                    "interfaces":
                        ["vwlan1","veth4"],
                    "bridge_settings":
                        {
                            "controller":"tcp:10.5.8.3",
                            "dpid":"00:00:00:00:01:01"
                        },
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth4",
                    "mac":"00:00:00:00:01:10"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan1",
                    "name":"vwlan1",
                    "mac":"00:00:00:00:01:11"
                }
        }
    ]
}

SECOND_SLICE_CONFIG_R1 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "SECOND_R1",
                    "radio" : "radio1",
                    "if_name" : "wlan1-1",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"linux_bridge",
            "attributes":   
                {
                    "name":"second-br-r1",
                    "interfaces":
                        ["vwlan1-1","veth5"],
                    "bridge_settings":{},
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth5",
                    "mac":"00:00:00:00:01:20"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan1-1",
                    "name":"vwlan1-1",
                    "mac":"00:00:00:00:01:21"
                }
        }
    ]
}

THIRD_SLICE_CONFIG_R1 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "THIRD_R1",
                    "radio" : "radio1",
                    "if_name" : "wlan1-2",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"linux_bridge",
            "attributes":   
                {
                    "name":"third-br-r1",
                    "interfaces":
                        ["vwlan1-2","veth6"],
                    "bridge_settings":{},
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth6",
                    "mac":"00:00:00:00:01:30"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan1-2",
                    "name":"vwlan1-2",
                    "mac":"00:00:00:00:01:31"
                }
        }
    ]
}

FOURTH_SLICE_CONFIG_R1 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "FOURTH_R1",
                    "radio" : "radio1",
                    "if_name" : "wlan1-3",
                    "encryption_type":"wep-open",
                    "key":"23456"
                }
        }
    ],     
    "VirtualBridges": [
        {
            "flavor":"linux_bridge",
            "attributes":   
                {
                    "name":"fourth-br-r1",
                    "interfaces":
                        ["vwlan1-3","veth7"],
                    "bridge_settings":{},
                    "port_settings":{}
                }
        }
    ], 
    "VirtualInterfaces": [
        {
            "flavor":"veth",
            "attributes": 
                {
                    "attach_to":"eth0",
                    "name":"veth7",
                    "mac":"00:00:00:00:01:40"
                }
        },
        {
            "flavor":"veth",
            "attributes":
                {
                    "attach_to":"wlan1-3",
                    "name":"vwlan1-3",
                    "mac":"00:00:00:00:01:41"
                }
        }
    ]
}

DEFAULT_MODIFY_CONFIG_MAIN_R0 = \
{
    "RadioInterfaces": [
        {
            "flavor" : "wifi_bss",
            "attributes" : 
                {
                    "name" : "MAIN",
                    "new_name": "MAIN MOD"
                }
        }
    ],
    "VirtualBridges": [
        {
            "flavor":"ovs",
            "attributes":   
                {
                    "name":"main-br",
                    "bridge_settings":
                        {
                            "controller":"tcp:10.5.8.3:9933"
                        },
                }
        }
    ]
}

BROKEN_MODIFY_CONFIG_MAIN_R0 = \
{
    "VirtualBridges": [
        {
            "flavor":"ovs",
            "attributes":   
                {
                    "name":"main-br",
                    "bridge_settings":
                        {
                            "controller":"invalid_controller"
                        },
                }
        }
    ]
}