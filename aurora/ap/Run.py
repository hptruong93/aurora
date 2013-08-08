import SliceAgent
import sys

if __name__ == '__main__':
    agent = SliceAgent.SliceAgent()
    # AP Number
    number = sys.argv[1]
    if number == "1":
        json = 'ap-slice'
    elif number == "2":
        json = 'ap2-slice'
    elif number == "3":
        json = 'ap3-slice'
    else:
        raise Exception("Invalid AP Number argument")
        
    agent.execute('slice1','create_slice',agent.load_json(json + '1.json'),'user1')
    agent.execute('slice2','create_slice',agent.load_json(json + '2.json'),'user1')
    raw_input("Press a key to terminate...")
