# Aurora Manager Functions
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
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
from slice_plugin import *
from sql_check import *

class Manager():
    
    def __init__(self):
        #Sync JSON and SQL databases
        SQLCheck().syncAll()
        
    def parseargs(self, function, args, tenant_id, user_id, project_id):
        # args is a generic dictionary passed to all functions (each function is responsible for parsing
        # their own arguments
        function = function.replace('-', '_') #For functions in python
        getattr(self, function)(args, tenant_id, user_id, project_id)
    
    def ap_filter(self, args):
        try:
            JFILE = open('json/aplist.json', 'r')
            APlist = json.load(JFILE)
            JFILE.close()
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        
        if len(args) == 0: #No filter or tags
            return APlist
        elif len(args.split()) == 1: #Simple filter
            if '=' in args:
                if args.split('=')[0] == "location":
                    toPrint = filter(lambda x: (args.split('=')[1] in x[1][args.split['='][0]]), APlist)
                elif args.split('=')[0] == "name":
                    toPrint = filter(lambda x: (x[0] == args.split('=')[1]), APlist)
                else:
                    toPrint = filter(lambda x: (x[1][args.split('=')[0]] == args.split('=')[1]), APlist)
            elif '!' in args:
                if args.split('!')[0] == "location":
                    toPrint = filter(lambda x: (args.split('!')[1] not in x[1][args.split['!'][0]]), APlist)
                elif args.split('!')[0] == "name":
                    toPrint = filter(lambda x: (x[0] != args.split('!')[1]), APlist)
                else:
                    toPrint = filter(lambda x: (x[1][args.split('!')[0]] != args.split('!')[1]), APlist)
            elif '<' in args:
                toPrint = filter(lambda x: (float(x[1][args.split('<')[0]]) < float(args.split('<')[1])), APlist)
            elif '>' in args:
                toPrint = filter(lambda x: (float(x[1][args.split('>')[0]]) > float(args.split('>')[1])), APlist)
            else:
                print('Invalid command!')
                return []
            return toPrint
        else: #parse the string (Format Example: "location=mcgill & firmware!2 & location=toronto")
            op = args.split()
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
                    return []
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
                        return []
            return workinglist
            
    def ap_list(self, args, tenant_id, user_id, project_id):
        if args['filter']:
            arg_filter = args['filter'][0]
        else:
            arg_filter = []
        arg_i = args['i']
        toPrint = self.ap_filter(arg_filter)
        for entry in toPrint:
            print('\nName: '+entry[0])
            if arg_i == True: #Print extra data
                for attr in entry[1]:
                    print(attr+': '+entry[1][attr])

    def intersection(self, li1, li2): #for parsing and
        result = filter(lambda x: x in li1, li2)
        return result
    
    def ap_show(self, args, tenant_id, user_id, project_id):
        arg_name = args['ap-show'][0]
        toPrint = self.ap_filter('name='+arg_name)
        for entry in toPrint:
            print('\nName: '+entry[0])
            for attr in entry[1]:
                print(attr+': '+entry[1][attr])

    def ap_slice_clone(self, args, tenant_id, user_id, project_id):
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
    
    def ap_slice_create(self, args, tenant_id, user_id, project_id):
        if 'ap' in args:
            arg_ap = args['ap']
        else:
            arg_ap = None
        if 'filter' in args:
            arg_filter = args['filter'][0]
        else:
            arg_filter = None
        if 'file' in args:
            arg_file = args['file'][0]
        else:
            arg_file = None
        arg_tag = args['tag']
        json_list = [] #If a file is provided for multiple APs, we need to split the file for each AP, saved here
        
        #Load optional json file if applicable
        if arg_file:
            try:
                JFILE = open(arg_file, 'r')
                jsonfile = json.load(JFILE)
                JFILE.close()
            except IOError:
                print('Error opening file!')
                sys.exit(-1)
        
        if arg_ap:
            aplist = arg_ap
        else: #We need to apply the filter
            result = self.ap_filter(arg_filter)
            aplist = []
            for entry in result:
                aplist.append(entry[0])
                
        #Initialize json_list structure
        for i in range(len(aplist)):
            json_list.append({'VirtualInterfaces':[], 'VirtualBridges':[], 'RadioInterfaces':[]})
            
        #Send to plugin for parsing
        json_list = SlicePlugin(tenant_id, user_id, arg_tag).parseCreateSlice(jsonfile, len(aplist), json_list)
        
        #Send
        for json_entry in json_list:
            print json.dumps(json_entry, sort_keys=True, indent=4)
    
    def ap_slice_delete(self, args, tenant_id, user_id, project_id):
        arg_name = args['ap-slice-delete']
        data = {}
        data['action'] = 'ap-slice-delete'
        data['name'] = arg_name
        data['list'] = None
        data['json'] = None
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def ap_slice_list(self, args, tenant_id, user_id, project_id):
        arg_filter = args['filter'][0]
        arg_i = args['i']
        #GET JSON FILE FROM MANAGER
        #FOR TESTING
        try:
            JFILE = open('json/apslice-'+str(tenant_id)+'.json', 'r')
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
            
                
    def ap_slice_show(self, args, tenant_id, user_id, project_id):
        arg_id = args['ap-slice-show'][0]
        self.ap_slice_list({'filter':'ap_slice_id='+str(arg_id), 'i':True})
    
    def wnet_add_ap(self, args, tenant_id, user_id, project_id):
        arg_name = args['wnet-add-ap'][0]
        arg_slice = args['slice'][0]
        
        #Send
    
    def wnet_create(self, args, tenant_id, user_id, project_id):
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
        data['json'] = {'tenant':tenant_id, 'aggregate_rate': arg_aggrate, 'qos_priority':arg_qos, 'is_shareable':arg_share}
        toSend = json.dumps(data, sort_keys=True, indent=4)
        #Send
        print toSend
    
    def wnet_delete(self, args, tenant_id, user_id, project_id):
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
    
    def wnet_join(self, args, tenant_id, user_id, project_id): #TODO AFTER SAVI INTEGRATION
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
    
    def wnet_list(self, args, tenant_id, user_id, project_id):
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
            if entry['tenant_id'] == tenant_id or tenant_id == 0: #TODO: REPLACE admin (tenant_id == 0)
                for attr in entry:
                    print attr+": "+str(entry[attr])
            print "\n", #print new line
    
    def wnet_remove_ap(self, args, tenant_id, user_id, project_id):
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
    
    def wnet_show(self, args, tenant_id, user_id, project_id):
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
            if entry['tenant_id'] == tenant_id and entry['name'] == arg_name:
                for attr in entry:
                    print attr+": "+str(entry[attr])
            print "\n", #print new line
        
#For Testing
#Manager().parseargs('ap-slice-create', {'filter':['region=mcgill & number_radio<2 & version<1.1 & number_radio_free!2 & supported_protocol=a/b/g'], 'file':['json/slicetemp.json'], 'tag':['first']},1,1,1)
#Manager().parseargs('ap-slice-create', {'ap':['of1', 'of2', 'of3', 'of4'],'file':['json/slicetemp.json'], 'tag':['first']},1,1,1)
#Manager().parseargs('ap-slice-create', {'ap':['of1'],'file':['json/slicetemp.json'], 'tag':['first']},1,1,1)
