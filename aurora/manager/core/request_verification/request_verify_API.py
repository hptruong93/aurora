import request_verification as verify_agent
import verification_exception as exceptions

class RequestVerifier():
    #The command names must be identical to the method calling
    #verification from aurora_db.py
    _commands = {
        verify_agent.GENERAL_CHECK : [verify_agent.APSliceNumberVerification()],
        verify_agent.CREATE_SLICE : [verify_agent.APSliceNumberVerification(), 
                        verify_agent.RadioConfigExistedVerification(),
                        verify_agent.BridgeNumberVerification(),
                        verify_agent.VirtualInterfaceNumberVerification(),
                        verify_agent.AccessConflictVerification()]
    }

    #If there is any problem with the verification process, the function will return
    #a string with error information for client to take further actions.
    #If everything is OK, the function return None
    @staticmethod
    def isVerifyOK(command, request):
        for verifier in RequestVerifier._commands[command]:
            try:
                verifier._verify(command, request)
            except exceptions.VerificationException as ex:
                #print ex._handle_exception() #Testing only
                return ex._handle_exception()
            except Exception:
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
        return None


#Use this method as an interface for the verification. Internal structure above must not be accessed from outside of the file
def verifyOK(physical_ap = '', tenant_id = 0, request = None):
    if request is None:
        command = verify_agent.GENERAL_CHECK
        return RequestVerifier.isVerifyOK(command, request)
    else:
        # There is no handling for key 'physical_ap' and 'tenant_id' on the access point
        # side of the amqp link. So these entries would be removed once verification has been done.
        request['physical_ap'] = physical_ap
        request['tenant_id'] = tenant_id
        
        command = request['command']
        result = RequestVerifier.isVerifyOK(command, request)

        #Now return the original json_entry
        request.pop('physical_ap', None)
        request.pop('tenant_id', None)

        return result


if __name__ == '__main__':
    #Testing
    request = {
    "command": "create_slice", 
    "config": {
        "RadioInterfaces": [
            {
                "attributes": {
                    "channel": "1", 
                    "country": "CA", 
                    "disabled": "0", 
                    "hwmode": "abg", 
                    "name": "radio0", 
                    "txpower": "20"
                }, 
                "flavor": "wifi_radio"
            },
            {
                "attributes": {
                    "encryption_type": "wep-open", 
                    "if_name": "wlan0", 
                    "key": "12345", 
                    "name": "MK", 
                    "radio": "radio0"
                }, 
                "flavor": "wifi_bss"
            }
        ], 
        "VirtualBridges": [
            {
                "attributes": {
                    "bridge_settings": {}, 
                    "interfaces": [
                        "vwlan0", 
                        "veth0"
                    ], 
                    "name": "linux-br", 
                    "port_settings": {}
                }, 
                "flavor": "linux_bridge"
            }
        ], 
        "VirtualInterfaces": [
            {
                "attributes": {
                    "attach_to": "wlan0", 
                    "name": "vwlan0"
                }, 
                "flavor": "veth"
            },
            {
                "attributes": {
                    "attach_to": "eth0", 
                    "name": "veth0"
                }, 
                "flavor": "veth"
            }, 
            
        ]
    }, 
    "slice": "null", 
    "user": 1
}
    print verifyOK('openflow1', 1, request)