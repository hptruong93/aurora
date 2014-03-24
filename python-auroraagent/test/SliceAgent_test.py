import importlib
import inspect
import os
import sys
import time

# Since this file is for testing, add subdirectories to python path.
# This lets them run without issue without using relative imports.
cmd_folder = os.path.realpath(
    os.path.abspath(
        os.path.split(inspect.getfile(inspect.currentframe()))[0]
    )
)
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

cmd_subfolder = os.path.realpath(
    os.path.abspath(
        os.path.join(
            os.path.split(inspect.getfile(inspect.currentframe()))[0],
            ".."
        )
    )
)
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

cmd_subfolder = os.path.realpath(
    os.path.abspath(
        os.path.join(
            os.path.split(inspect.getfile(inspect.currentframe()))[0],
            "..",
            "modules"
        )
    )
)
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

import conf
from SliceAgent import SliceAgent


def print_databases(agent, tag=None):
    if tag:
        print tag
    print "Database"
    print json.dumps(agent.database.database, indent=4)
    print "Previous Database"
    print json.dumps(agent.database.prev_database, indent=4)

def get_test_agent():
    """Returns an initialized SliceAgent instance."""
    return SliceAgent(conf.AGENT_INIT_CONFIG)

def test_create_slice(agent, slice, slice_config):
    """Create a slice using slice_config"""
    agent.execute(slice, "create_slice", config=slice_config, user="1")

def test_modify_slice(agent, slice, slice_config=conf.DEFAULT_MODIFY_CONFIG_MAIN_R0):
    agent.execute(slice, "modify_slice", config=slice_config, user="1")

def test_restart_slice(agent, slice):
    agent.restart_slice(slice)

def main_test_create():
    slice_id = "slice1"
    agent = get_test_agent()
    test_create_slice(agent, slice_id, conf.MAIN_SLICE_CONFIG_R0)
    print "Creation complete!"
    time.sleep(3)
    del agent

def main_test_create_and_modify():
    slice_id = "slice1"
    agent = get_test_agent()
    test_create_slice(agent, slice_id, conf.MAIN_SLICE_CONFIG_R0)
    print "Creation complete!"
    time.sleep(1)
    test_modify_slice(agent, slice_id)
    print "Modification complete!"
    time.sleep(1)
    del agent

def main_test_create_and_restart_1():
    slice_id = "slice1"
    agent = get_test_agent()
    test_create_slice(agent, slice_id, conf.MAIN_SLICE_CONFIG_R0)
    print "Creation complete!"
    time.sleep(1)

    agent.database.backup_current_config()

    test_restart_slice(agent, slice_id)
    print "Restarted %s" % slice_id
    time.sleep(4)
    del agent

def main_test_create_and_restart_2():
    # Create slice 1 - MAIN
    slice_id = "slice1"
    agent = get_test_agent()
    test_create_slice(agent, slice_id, conf.MAIN_SLICE_CONFIG_R0)
    print "Creation complete (%s)!" % slice_id
    time.sleep(1)

    # Create slice 2 - SECOND
    slice_id = "slice2"
    test_create_slice(agent, slice_id, conf.SECOND_SLICE_CONFIG_R0)
    print "Creation complete (%s)!" % slice_id
    time.sleep(1)

    agent.database.backup_current_config()

    test_restart_slice(agent, "slice1")
    print "Restarted %s" % slice_id
    time.sleep(4)


    del agent

def main():
    main_test_create_and_restart_1()

if __name__ == "__main__":
    main()