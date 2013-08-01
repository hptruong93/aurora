# Aurora-client
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Temporary Client Implementing functions of ap-client (assume we already have JSON files for querying)
JSON File Format for Sending:
{
    "action": ... , #The action i.e. delete, clone, add
    "name": ... , #Name/id if applicable (i.e. for delete, add, clone)
    "list" : [...], #List of APs/slices/wnets (by name, tag etc.) to perform on
    "json": [...] #attached json file
}
"""
import json
import sys
from utils import print_list, print_dict

class Client():
    
    def __init__(self):
        pass
        
    def parseargs(self, function, args, extra=None):
        # args is a generic dictionary passed to all functions (each function is responsible for parsing
        # their own arguments
        function = function.replace('-', '_') #For functions in python
        if not extra:
            getattr(self, function)(args)
        else:
            getattr(self, function)(args, extra)    
    
    def ap_list(self, args, printScreen=True):
        arg_filter = args['filter'][0]
        arg_i = args['i']
        #GET JSON FILE FROM MANAGER
        #FOR TESTING
        try:
            JFILE = open('json/aplist.json', 'r')
            APlist = json.load(JFILE)
            JFILE.close()
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        #FOR TESTING END
        
        if len(arg_filter) == 0: #No filter or tags
            if printScreen:
                for entry in APlist:
                    print('\nName: '+entry[0])
                    if arg_i == True: #Print extra data
                        for attr in entry[1]:
                            print(attr+': '+entry[1][attr])
            return APlist
        elif len(arg_filter.split()) == 1: #Simple filter
            if '=' in arg_filter:
                if arg_filter.split('=')[0] == "location":
                    toPrint = filter(lambda x: (arg_filter.split('=')[1] in x[1][arg_filter.split['='][0]]), APlist)
                elif arg_filter.split('=')[0] == "name":
                    toPrint = filter(lambda x: (x[0] == arg_filter.split('=')[1]), APlist)
                else:
                    toPrint = filter(lambda x: (x[1][arg_filter.split('=')[0]] == arg_filter.split('=')[1]), APlist)
            elif '!' in arg_filter:
                if arg_filter.split('!')[0] == "location":
                    toPrint = filter(lambda x: (arg_filter.split('!')[1] not in x[1][arg_filter.split['!'][0]]), APlist)
                elif arg_filter.split('!')[0] == "name":
                    toPrint = filter(lambda x: (x[0] != arg_filter.split('!')[1]), APlist)
                else:
                    toPrint = filter(lambda x: (x[1][arg_filter.split('!')[0]] != arg_filter.split('!')[1]), APlist)
            elif '<' in arg_filter:
                toPrint = filter(lambda x: (float(x[1][arg_filter.split('<')[0]]) < float(arg_filter.split('<')[1])), APlist)
            elif '>' in arg_filter:
                toPrint = filter(lambda x: (float(x[1][arg_filter.split('>')[0]]) > float(arg_filter.split('>')[1])), APlist)
            else:
                print('Invalid command!')
                return
            if printScreen:
                for entry in toPrint:
                    print('\nName: '+entry[0])
                    if arg_i == True: #Print extra data
                        for attr in entry[1]:
                            print(attr+': '+entry[1][attr])
            return toPrint
        else: #parse the string (Format Example: "location=mcgill & firmware!2 & location=toronto")
            op = arg_filter.split()
            atom = op.pop(0)
            if '=' in atom:
                if atom.split('=')[0] == "location":
                    workinglist = filter(lambda x: (atom.split('=')[1] in x[1]['location']), APlist)
                elif atom.split('=')[0] == "name":
                    workinglist = filter(lambda x: (x[0] == atom.split('=')[1]), APlist)
                else:
                    workinglist = filter(lambda x: (x[1][atom.split('=')[0]] == atom.split('=')[1]), APlist)
            elif '!' in atom:
                if atom.split('!')[0] == "location":
                    workinglist = filter(lambda x: (atom.split('!')[1] not in x[1][atom.split['!'][0]]), APlist)
                elif atom.split('=')[0] == "name":
                    workinglist = filter(lambda x: (x[0] != atom.split('=')[1]), APlist)
                else:
                    workinglist = filter(lambda x: (x[1][atom.split('!')[0]] != atom.split('!')[1]), APlist)
            elif '<' in atom:
                workinglist = filter(lambda x: (float(x[1][atom.split('<')[0]]) < float(atom.split('<')[1])), APlist)
            elif '>' in atom:
                workinglist = filter(lambda x: (float(x[1][atom.split('>')[0]]) > float(atom.split('>')[1])), APlist)
            while len(op) > 0:
                if (len(op) % 2) != 0 or len(op[1]) == 1: #Incorrect amount of arguments
                    print('Insufficient number of arguments!')
                    return
                else:
                    atom = op.pop(1)
                    if '=' in atom:
                        if atom.split('=')[0] == "location":
                            templist = filter(lambda x: (atom.split('=')[1] in x[1]['location']), APlist)
                        else:
                            templist = filter(lambda x: (x[1][atom.split('=')[0]] == atom.split('=')[1]), APlist)
                    elif '!' in atom:
                        if atom.split('!')[0] == "location":
                            templist = filter(lambda x: (atom.split('!')[1] not in x[1]['location']), APlist)
                        else:
                            templist = filter(lambda x: (x[1][atom.split('!')[0]] != atom.split('!')[1]), APlist)
                    elif '<' in atom:
                        templist = filter(lambda x: (float(x[1][atom.split('<')[0]]) < float(atom.split('<')[1])), APlist)
                    elif '>' in atom:
                        templist = filter(lambda x: (float(x[1][atom.split('>')[0]]) > float(atom.split('>')[1])), APlist)
                    operation = op.pop(0)
                    if operation == "&":
                        workinglist = self.intersection(workinglist, templist)
                    else:
                        print('Unexpected character!')
                        return
            if printScreen:
                for entry in workinglist:
                    print('\nName: '+entry[0])
                    if arg_i == True: #Print extra data
                        for attr in entry[1]:
                            print(attr+': '+entry[1][attr])
            return workinglist
    
    def intersection(self, li1, li2): #for parsing and
        result = filter(lambda x: x in li1, li2)
        return result
    
    def ap_show(self, args):
        arg_name = args['ap-show'][0]
        self.ap_list({'filter':'name='+arg_name, 'i':True})
    
    def ap_slice_clone(self, args):
        arg_ap = args['ap']
        arg_slice = args['ap-slice-clone'][0]
        data = {}
        data['action'] = 'ap-slice-clone'
        data['name'] = arg_slice
        data['list'] = arg_ap
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def ap_slice_create(self, args):
        if 'ap' in args:
            arg_ap = args['ap']
        else:
            arg_ap = None
        if 'filter' in args :
            arg_filter = args['filter']
        else:
            arg_filter = None
        if 'file' in args:
            arg_file = args['file'][0]
        else:
            arg_file = None
        arg_tag = args['tag']
        data = {}
        
        #Load optional json file if applicable
        if arg_file:
            try:
                JFILE = open(arg_file, 'r')
                jsonfile = json.load(JFILE)
                data['file'] = jsonfile
                JFILE.close()
            except IOError:
                print('Error opening file!')
                sys.exit(-1)
        
        data['action'] = 'ap-slice-create'
        data['name'] = arg_tag
        
        if arg_ap:
            data['list'] = arg_ap
        else: #We need to apply the filter
            result = self.ap_list({'filter':arg_filter, 'i':False}, printScreen=False)
            data['list'] = []
            for entry in result:
                data['list'].append(entry[0])
        
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def ap_slice_delete(self, args):
        arg_name = args['ap-slice-delete']
        data = {}
        data['action'] = 'ap-slice-delete'
        data['name'] = arg_name
        data['list'] = None
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def ap_slice_list(self, args):
        arg_filter = args['filter'][0]
        arg_i = args['i']
        #GET JSON FILE FROM MANAGER
        #FOR TESTING
        try:
            JFILE = open('json/apslice.json', 'r')
            APslice = json.load(JFILE)
            JFILE.close()
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        #FOR TESTING END
        if len(arg_filter) == 0: #No args
            for entry in APslice:
                if not arg_i:
                    for attr in entry:
                        if attr != "slice_qos_priority" and attr != "slice_qos_aggregate_rate" and attr != "RadioInterfaces" \
                            and attr != "VirtualInterfaces" and attr != "VirtualBridges":
                            print attr+": "+str(entry[attr])
                else:
                    for attr in entry:
                        print attr+": "+str(entry[attr])
                print "\n", #print new line
        
        elif len(arg_filter.split()) == 1: #One argument
            if '=' in arg_filter:
                toPrint = filter(lambda x: arg_filter.split('=')[1] == str(x[arg_filter.split('=')[0]]), APslice)
            elif '!' in arg_filter:
                toPrint = filter(lambda x: arg_filter.split('!')[1] != str(x[arg_filter.split('!')[0]]), APslice)
            else:
                print('Invalid command!')
                return
            for entry in toPrint:
                if not arg_i:
                    for attr in entry:
                        if attr != "slice_qos_priority" and attr != "slice_qos_aggregate_rate" and attr != "RadioInterfaces" \
                            and attr != "VirtualInterfaces" and attr != "VirtualBridges":
                            print attr+": "+str(entry[attr])
                else:
                    for attr in entry:
                        print attr+": "+str(entry[attr])
                print "\n", #print new line
                
        else: #Multiple arguments
            op = arg_filter.split()
            atom = op.pop(0)
            if '=' in atom:
                workinglist = filter(lambda x: atom.split('=')[1] == str(x[atom.split('=')[0]]), APslice)
            elif '!' in atom:
                workinglist = filter(lambda x: atom.split('!')[1] != str(x[atom.split('=')[0]]), APslice)
            while len(op) > 0:
                if (len(op) % 2) != 0 or len(op[1]) == 1: #Incorrect amount of arguments
                    print('Insufficient number of arguments!')
                    return
                else:
                    atom = op.pop(1)
                    if '=' in atom:
                        templist = filter(lambda x: atom.split('=')[1] == str(x[atom.split('=')[0]]), APslice)
                    elif '!' in atom:
                        templist = filter(lambda x: atom.split('!')[1] != str(x[atom.split('!')[0]]), APslice)
                    operation = op.pop(0)
                    if operation == "&":
                        workinglist = self.intersection(workinglist, templist)
                    else:
                        print('Unexpected character!')
                        return
            for entry in workinglist:
                if not arg_i:
                    for attr in entry:
                        if attr != "slice_qos_priority" and attr != "slice_qos_aggregate_rate" and attr != "RadioInterfaces" \
                            and attr != "VirtualInterfaces" and attr != "VirtualBridges":
                            print attr+": "+str(entry[attr])
                else:
                    for attr in entry:
                        print attr+": "+str(entry[attr])
                print "\n", #print new line
            
                
    def ap_slice_show(self, args):
        arg_id = args['ap-slice-show'][0]
        self.ap_slice_list({'filter':'ap_slice_id='+str(arg_id), 'i':True})
    
    def wnet_add_ap(self, args):
        arg_name = args['wnet-add-ap'][0]
        arg_slice = args['slice']
        data = {}
        data['action'] = 'wnet-add-ap'
        data['name'] = arg_name
        data['list'] = arg_slice
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def wnet_create(self, args, tenant): #TODO
        arg_name = args['wnet-create'][0]
        arg_slice = args['slice']
        arg_qos = args['qos_priority'][0]
        arg_share = args['shareable']
        if 'aggregate_rate' in args:
            arg_aggrate = args['aggregate_rate'][0]
        else:
            arg_aggrate = None
        data = {}
        data['action'] = 'wnet-create'
        data['name'] = arg_name
        data['list'] = arg_slice
        data['json'] = {'tenant':tenant, 'aggregate_rate': arg_aggrate, 'qos_priority':arg_qos, 'is_shareable':arg_share}
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def wnet_delete(self, args):
        arg_name = args['wnet-delete'][0]
        arg_f = args['f']
        data = {}
        if arg_f:
            data['action'] = 'wnet-delete-force'
        else:
            data['action'] = 'wnet-delete'
        data['name'] = arg_name
        data['list'] = None
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def wnet_join(self, args):
        arg_netname = args['wnet-join'][0]
        arg_wnetname = args['wnet_name'][0]
        data = {}
        data['action'] = 'wnet-join'
        data['name'] = arg_netname
        data['list'] = [arg_wnetname]
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def wnet_list(self, args, tenant, name):
        #GET JSON FILE FROM MANAGER
        #FOR TESTING
        try:
            JFILE = open('json/wnet.json', 'r')
            wnet = json.load(JFILE)
            JFILE.close()
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        #FOR TESTING END
        for entry in wnet:
            if entry['tenant'] == tenant:
                for attr in entry:
                    print attr+": "+str(entry[attr])
            print "\n", #print new line 
        
    
    def wnet_remove_ap(self, args):
        arg_name = args['wnet-remove-ap'][0]
        arg_slice = args['slice']
        data = {}
        data['action'] = 'wnet-remove-ap'
        data['name'] = arg_name
        data['list'] = arg_slice
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def wnet_show(self, args, tenant):
        arg_name = args['wnet-show'][0]
        #GET JSON FILE FROM MANAGER
        #FOR TESTING
        try:
            JFILE = open('json/wnet.json', 'r')
            wnet = json.load(JFILE)
            JFILE.close
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        #FOR TESTING END
        for entry in wnet:
            if entry['tenant'] == tenant and entry['name'] == arg_name:
                for attr in entry:
                    print attr+": "+str(entry[attr])
            print "\n", #print new line
        
#For Testing
#Client().parseargs('ap-list', {'filter':['region=mcgill & number_radio<3 & version<1.1 & number_radio_free!2 & supported_protocol=a/b/g'], 'i':True})
#Client().parseargs('ap-slice-list', {'filter':'physical_ap=openflowkevin & ap_slice_id=2 & project_id=2', 'i':True})
#Client().parseargs('wnet-show', {'wnet-show':['wnet-2']},'savi')
#Client().parseargs('wnet-remove-ap', {'wnet-remove-ap':['openflow'], 'slice':[1,2,3,4,5,6,7]})
#Client().parseargs('ap-show', {'ap-show':['openflowkevin']})
#Client().parseargs('ap-slice-create', {'filter':['region=mcgill & number_radio<2 & version<1.1 & number_radio_free!2 & supported_protocol=a/b/g'], 'file':['json/temp.json'], 'tag':['first']})
#Client().parseargs('wnet-create', {'wnet-create':['newnet'], 'slice':['slice1', 'slice2'], 'qos_priority':[u'1'], 'aggregate_rate':['2'], 'shareable':False}, 'savi')
