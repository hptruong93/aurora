import traceback
import sys
from aurora import sql_Info

def hint(manager, args):
    arg_hint = args['hint'][0]
    if "location" in arg_hint:
        # Try to access the local database to grab location
        tempList = manager.ap_filter(arg_hint)
        message = ""
        for entry in tempList:
            if not ('mcgill' in entry[0] or 'mcgill' in entry[1]):
                message += "%5s: %s\n" % (entry[1], entry[0])
        
        # Make a decision according to the token "location" OR "slice_load"
        try:
            if args.get('location') is not None: # if there is a location specification
                if args['location'].lower() in message.lower(): # check if the location is valid
                    indexSliceLoad = ""
                    freespace = 0;
                    if "slice-load" in arg_hint:
                        print "Search the lightweight AP"
                        indexSliceLoad = "unknown"
                    else:
                        print "Locate a random AP"
                    
                    # Search for the proper slices
                    for entry in tempList:
                        if args['location'].lower() == entry[0].lower():
                            # once the location matches -- check if the AP has free spots
                            apList = manager.ap_filter("name=" + entry[1])
                            if apList[0][1]['number_slice_free'] > 0:
                                if(len(indexSliceLoad)==0): # In this case, token is only "location"
                                    #TODO: this following two lines are only for testing purpose
                                    if sql_Info.checkAP_up(indexSliceLoad): # if AP is up, assign the AP
                                        indexSliceLoad = entry[1]
                                        break
                                elif(apList[0][1]['number_slice_free']>freespace): # Token contains "slice-load"
                                    if sql_Info.checkAP_up(indexSliceLoad): # if AP is up, assign the AP
                                        freespace = apList[0][1]['number_slice_free']
                                        indexSliceLoad = entry[1]

                    message = indexSliceLoad
                else:
                    message = "invalid location information"
        except Exception as ex:
            traceback.print_exc(file=sys.stdout)
            
        response = {"status":True, "message":message}
        return response
    if args['file'] is None:
        raise NoSliceConfigFileException()
