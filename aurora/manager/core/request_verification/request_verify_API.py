import request_verification as verify_agent
import verification_exception as exceptions
import sys, traceback

class RequestVerifier():
    #The command names must be identical to the method calling
    #verification from aurora_db.py
    _commands = {
        verify_agent.GENERAL_CHECK : [verify_agent.APSliceNumberVerification()],
        verify_agent.CREATE_SLICE : [verify_agent.APSliceNumberVerification(), 
                        verify_agent.RadioConfigExistedVerification(),
                        verify_agent.BridgeNumberVerification(),
                        verify_agent.VirtualInterfaceNumberVerification(),
                        verify_agent.AccessConflictVerification()],
        verify_agent.DELETE_SLICE : [verify_agent.ValidDeleteVerification()]
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
        "command": "delete_slice", 
        "slice": "9e2a82e3-a19e-4be6-a158-9dc9ad0f9c2b", 
        "user": 1,
    }
    print verifyOK(tenant_id = 1, request = request)