#!/usr/bin/python -tt
#
# Mike Kobierski aurora install script

"""A short script which copies python launch code
aurora and auroraclient to /usr/local/bin.  This
eases launching aurora/manager/ManagerServer.py
and auroraclient/shell.py.

Run with root privileges.
Examples:
    $ sudo python aurorainstall.py
    $ sudo python aurorainstall.py --uninstall
"""
def main():
    import sys
    import shutil
    import os
    import time
    args = sys.argv[1:]
    
    # Check proper usage
    if len(args) > 1:
        print "Invalid number of args.  Usage: python aurorainstall.py [--uninstall]"
        exit(1)
    if len(args) == 1:
        if args[0] != "--uninstall":
            print "Invalid argument.  Usage: python aurorainstall.py [--uninstall]"
            exit(1)

    auroraDirectory = os.getcwd()
    print "cwd: ", auroraDirectory
    
    # Remove aurora
    try:
        print "Removing /usr/local/bin/aurora..."
        os.remove("/usr/local/bin/aurora")
    except IOError as e:
        if (e[0] == errno.EPERM):
            print >> sys.stderr, "You need root permissions to do this!"
            sys.exit(1)
        else:
            print >> sys.stderr, e
            print "Continuing..."
    except OSError as e:
        if (e[0] == 2):
            print "aurora does not already exist, contining..."
    # Remove auroramanager
    try:
        print "Removing /usr/local/bin/auroramanager..."
        os.remove("/usr/local/bin/auroramanager")
    except IOError as e:
        if (e[0] == errno.EPERM):
            print >> sys.stderr, "You need root permissions to do this!"
            sys.exit(1)
        else:
            print >> sys.stderr, e
            print "Continuing..."
    except OSError as e:
        if (e[0] == 2):
            print "auroramanager does not already exist, contining..."
            
    
    # If not --uninstall
    if len(args) == 0:
        #create files auroramanager and aurora
        print "Creating auroramanager..."
        with open('auroramanager', 'w') as f:
            f.write('''#!/usr/bin/python -tt
"""Script which launches ManagerServer.py.
Usage: auroramanager [-n] [args]
    -n starts process in a new terminal
"""

if __name__ == "__main__":
    import subprocess
    import shlex
    import sys
    import os
    args = sys.argv[1:]
    auroraDirectory = \''''+auroraDirectory+'''\'
    
    if len(args) > 0:
        if args[0] == '-n':
            python_execute = "python ManagerServer.py " + ' '.join(args[1:])
            to_execute = "gnome-terminal --tab -e \\\"/bin/bash -c '" + python_execute + "; exec /bin/bash'\\\""
        else:
            to_execute = "python ManagerServer.py " + ' '.join(args)
    else:
        to_execute = "python ManagerServer.py"
    
    os.chdir(auroraDirectory + '/aurora/manager')
    
    # split args into a list
    execute_args = shlex.split(to_execute)              

    try:
        server_proc = subprocess.Popen(execute_args)
        server_proc.wait()
    except KeyboardInterrupt:
        time.sleep(2)
        pass
''')

        print "Creating aurora..."
        with open('auroralauncher', 'w') as f:
            f.write('''#!/usr/bin/python -tt
"""Script which launches auroraclient/shell.py.
Usage: aurora [-n] [args]
    -n starts process in a new terminal
"""

if __name__ == "__main__":
    import subprocess
    import shlex
    import sys
    import os
    args = sys.argv[1:]
    auroraDirectory = \''''+auroraDirectory+'''\'
    
    if len(args) > 0:
        if args[0] == '-n':
            python_execute = "python shell.py " + ' '.join(args[1:])
            to_execute = "gnome-terminal --tab -e \\\"/bin/bash -c '" + python_execute + "; exec /bin/bash'\\\""
        else:
            to_execute = "python shell.py " + ' '.join(args)
    else:
        to_execute = "python shell.py"
    
    os.chdir(auroraDirectory + '/auroraclient')
    
    # split args into a list
    execute_args = shlex.split(to_execute)      

    try:
        server_proc = subprocess.Popen(execute_args)
        server_proc.wait()
    except KeyboardInterrupt:
        pass
''')
        
        os.chmod("auroramanager", 0755)
        os.chmod("auroralauncher", 0755)
        
        
        #copy files to /usr/local/bin
        print "Copying files to /usr/local/bin..."
        try:
            shutil.move('auroramanager', '/usr/local/bin/auroramanager')
            shutil.move('auroralauncher', '/usr/local/bin/aurora')
        except IOError as e:
            if (e[0] == 13):
                print >> sys.stderr, "You need root permissions to do this!"
            print >> sys.stderr, e
            sys.exit(1)
        print "\nTo run, first start auroramanager:\n\t$ auroramanager -n\nThen start aurora:\n\t$ aurora --help"
        print "Omitting '-n' will launch in current terminal."

if __name__ == "__main__":
    main()
