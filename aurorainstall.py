#!/usr/bin/python -tt
#
# Author: Mike Kobierski
"""A short script which copies python launch code aurora and 
auroraclient to /usr/local/bin.  This eases launching 
:mod:`aurora.shell` and :mod:`auroraclient.shell`.

Run with root privileges.
Usage::

    $ sudo python aurorainstall.py
    $ sudo python aurorainstall.py --uninstall

"""
def main():
    import os
    import shutil
    import site
    import sys
    import time
    import traceback

    if os.geteuid() != 0:
        sys.exit("You need root permissions to do this!")

    args = sys.argv[1:]
    
    # Check proper usage
    if len(args) > 1:
        print "Invalid number of args.  Usage: python aurorainstall.py [--uninstall]"
        sys.exit(1)
    if len(args) == 1:
        if args[0] != "--uninstall":
            print "Invalid argument.  Usage: python aurorainstall.py [--uninstall]"
            sys.exit(1)

    auroraDirectory = os.getcwd()
    print "cwd: ", auroraDirectory
    
    # Remove aurora
    try:
        print "Removing /usr/local/bin/aurora..."
        os.remove("/usr/local/bin/aurora")
    except IOError as e:
        print >> sys.stderr, e
        print "Continuing..."
    except OSError as e:
        if (e[0] == 2):
            print "aurora does not already exist, contining..."

    # Remove aurora-manager
    try:
        print "Removing /usr/local/bin/aurora-manager..."
        os.remove("/usr/local/bin/aurora-manager")
    except IOError as e:
        print >> sys.stderr, e
        print "Continuing..."
    except OSError as e:
        if (e[0] == 2):
            print "aurora-manager does not already exist, contining..."
            
    if site.check_enableusersite():
        site_package_dir = site.getusersitepackages()
    else:
        site_package_dir = site.getsitepackages()[0]
    try:
        os.unlink(os.path.join(site_package_dir, 'aurora.pth'))
    except OSError:
        # File didn't exist
        pass
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    try:
        os.unlink(os.path.join(site_package_dir, 'python-auroraclient.pth'))
    except OSError:
        # File didn't exist
        pass
    except Exception:
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)


    # If not --uninstall
    if len(args) == 0:
        # Add module directory to python path
        try:
            os.makedirs(site_package_dir)
        except OSError:
            # File already exists
            pass
        try:
            with open(os.path.join(site_package_dir,'aurora.pth'), 'w') as F:
                F.write(auroraDirectory + '/aurora\n')
            with open(os.path.join(site_package_dir,'python-auroraclient.pth'), 'w') as F:
                F.write(auroraDirectory + '/python-auroraclient\n')
        except Exception:
            traceback.print_exc(file=sys.stdout)
            try:
                os.unlink(os.path.join(site_package_dir, 'aurora.pth'))
            except OSError:
                pass
            except Exception:
                traceback.print_exc(file=sys.stdout)
            try:
                os.unlink(os.path.join(site_package_dir, 'python-auroraclient.pth'))
            except OSError:
                pass
            except Exception:
                traceback.print_exc(file=sys.stdout)
            traceback.print_exc(file=sys.stdout)
            exit(1)

        # Create files auroramanager and aurora
        print "Creating auroramanager..."
        with open('aurora-manager', 'w') as f:
            f.write('''#!/usr/bin/python -tt
"""Script which launches aurora's manager"""
import sys

from aurora.shell import main

if __name__ == "__main__":
    sys.exit(main())
''')

        print "Creating aurora..."
        with open('aurora-client', 'w') as f:
            f.write('''#!/usr/bin/python -tt
"""Script which launches aurora's client."""
import sys

from auroraclient.shell import main

if __name__ == "__main__":
    sys.exit(main())
''')
        
        os.chmod("aurora-manager", 0755)
        os.chmod("aurora-client", 0755)
        
        
        #copy files to /usr/local/bin
        print "Copying files to /usr/local/bin..."
        try:
            shutil.move('aurora-manager', '/usr/local/bin/aurora-manager')
            shutil.move('aurora-client', '/usr/local/bin/aurora')
        except IOError as e:
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)
        print "\nTo run, first start aurora-manager:"
        print "\t$ aurora-manager"
        print "Then start aurora:"
        print "\t$ aurora --help"

if __name__ == "__main__":
    main()
