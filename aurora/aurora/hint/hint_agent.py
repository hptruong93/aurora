import traceback
import sys
from aurora.hint import sql_Info
from aurora import query_agent as filter

def hint(manager, args):
    arg_hint = args['hint']

    if "location" in arg_hint:
        # Try to access the local database to grab location
        #tempList = manager.ap_filter(arg_hint)
        tempList = filter.query(filter.join_table("ap", "location_tags", "name", "ap_name"), \
                    ["ap_name", "location_tags.name", "number_slice_free"], ["status = 'UP'", 'number_slice_free > 0'])

        message = ""
        for entry in tempList:
            if not ('mcgill' in entry[0] or 'mcgill' in entry[1]):
                message += "%5s: %s\n" % (entry[1], entry[0])

        # Make a decision according to the token "location" OR "slice_load"
        try:
            if args.get('location') is not None: # if there is a location specification
                if args['location'].lower() in message.lower(): # check if the location is valid
                    indexSliceLoad = ""
                    if "slice-load" in arg_hint:
                        manager.LOGGER.info("Hinting --> Search the lightweight AP")
                        indexSliceLoad = "unknown"
                    else:
                        manager.LOGGER.info("Hinting --> Locate a random AP")
                    
                    max_freespace = -1 #Any negative number will do
                    # Search for the proper slices
                    for entry in tempList:
                        if args['location'].lower() == entry[1].lower():
                            # once the location matches -- check if the AP has free spots
                            number_slice_free = entry[2]
                            if number_slice_free > 0:
                                if len(indexSliceLoad) == 0: # In this case, token is only "location"
                                    indexSliceLoad = entry[0]
                                    break
                                elif number_slice_free > max_freespace: # Token contains "slice-load"
                                    max_freespace = number_slice_free
                                    indexSliceLoad = entry[0]

                    message = indexSliceLoad
                else:
                    message = "invalid location information"
        except Exception as ex:
            traceback.print_exc(file=sys.stdout)
            
        response = {"status":True, "message":message}
        return response
    if args['file'] is None:
        raise NoSliceConfigFileException()
