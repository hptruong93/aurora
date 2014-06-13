# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

import traceback
import sys

from aurora.request_verification import request_verification as Check
from aurora.request_verification import verification_exception as exceptions
from aurora.ap_provision import reader as provision_reader
from aurora.hint import sql_Info
from aurora import query_agent as query

def hint(manager, args, tenant_id, user_id, project_id):
    arg_hint = args['hint']
    favored_ap = args['ap']
    ssid = args['ssid']
    if favored_ap:
        favored_ap = favored_ap[0]

    if "location" in arg_hint:
        # Try to access the local database to grab location
        #tempList = manager.ap_query(arg_hint)
        if favored_ap is None:
            tempList = query.query(query.join_table("ap", "location_tags", "name", "ap_name"), \
                    ["ap_name", "location_tags.name", "number_slice_free"], ["status = 'UP'", 'number_slice_free > 0'])
        else:
            tempList = query.query(query.join_table("ap", "location_tags", "name", "ap_name"), \
                    ["ap_name", "location_tags.name", "number_slice_free"], 
                    ["status = 'UP'", 'number_slice_free > 0', 'ap_name = "%s"' % favored_ap])

        message = {}
        message['ap_location'] = ""
        message['ssid'] = None
        message['bridge'] = {}
        message['bridge']['flavor'] = None
        message['ap'] = ""

        for entry in tempList:
            message['ap_location'] += "%5s: %s\n" % (entry[1], entry[0])

        # Make a decision according to the token "location" OR "slice_load"
        try:
            if args.get('location') is not None: # if there is a location specification
                if args['location'][0].lower() in message['ap_location'].lower(): # check if the location is valid
                    indexSliceLoad = ""
                    if "slice-load" in arg_hint:
                        manager.LOGGER.info("Hinting --> Search the lightweight AP")
                        indexSliceLoad = "unknown"
                    elif favored_ap is not None:
                        manager.LOGGER.info("Hinting --> Locate the favored AP: " + favored_ap)
                    else:
                        manager.LOGGER.info("Hinting --> Locate a random AP")
                    
                    max_freespace = -1 #Any negative number will do
                    # Search for the proper slices
                    for entry in tempList:
                        if args['location'][0].lower() == entry[1].lower():
                            # once the location matches -- check if the AP has free spots
                            number_slice_free = entry[2]
                            if number_slice_free > 0:
                                if len(indexSliceLoad) == 0: # In this case, token is only "location"
                                    indexSliceLoad = entry[0]
                                    max_freespace = number_slice_free
                                    break
                                elif number_slice_free > max_freespace: # Token contains "slice-load"
                                    max_freespace = number_slice_free
                                    indexSliceLoad = entry[0]

                    message['ap_location'] = 'True'
                    message['ap'] = indexSliceLoad
                else:
                    message['ap'] = ""
            if args.get('ssid') is not None:
                status = sql_Info.verify_ssid(args['ssid'][0], tenant_id)
                message['ssid'] = str(status)
            if args.get('bridge') is not None:
                if args['bridge'][0] == 'ovs' or args['bridge'][0] == 'linux_bridge':
                    message['bridge']['flavor'] = 'True'
        except Exception as ex:
            traceback.print_exc(file=sys.stdout)
            
        response = {"status":True, "message":message}
        return response
    if args['file'] is None:
        raise NoSliceConfigFileException()

def suggestAP(request):
    requesting_radio = provision_reader.get_radio_wifi_bss(request['config'])
    number_slices_on_radio = _get_slice_on_requested_radio(request)
    try:
        Check.APSliceNumberVerification().verify('create_slice', request)
    except exceptions.NoAvailableSpaceLeftInAP as e:
        return {'status' : False, 'slice_number': -1, 'suggest_radio' : None, 'exception' : e}
    except exceptions.NoAvailableSpaceLeftInRadio:
        try: #Changing radio
            requesting_radio = 'radio1'

            for item in request['config']['RadioInterfaces']:
                if item['flavor'] == 'wifi_radio':
                    item['attributes']['name'] = requesting_radio
                elif item['flavor'] == 'wifi_bss':
                    item['attributes']['radio'] = requesting_radio

            number_slices_on_radio = _get_slice_on_requested_radio(request)
            Check.APSliceNumberVerification().verify('create_slice', request)
        except exceptions.NoAvailableSpaceLeftInRadio as ex:
            return {'status' : False, 'slice_number': -1, 'suggest_radio' : None, 'exception' : ex}
    except Exception as ee:
        return {'status' : False, 'slice_number': -1, 'suggest_radio' : None, 'exception' : ee}

    existing_slices = provision_reader.get_slice_count(provision_reader.get_physical_ap_info(request['physical_ap']))
    return {'status' : True, 'slice_number': number_slices_on_radio, 
            'suggest_radio' : requesting_radio, 
            'existing_slice' : existing_slices, 'exception' : None}

def _get_slice_on_requested_radio(request):
    requested_radio = provision_reader.get_radio_wifi_bss(request['config'])
    request_ap_info = provision_reader.get_physical_ap_info(request['physical_ap'])
    number_slices = provision_reader.get_number_slice_on_radio(request_ap_info, requested_radio)
    return number_slices