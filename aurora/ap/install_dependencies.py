import subprocess

def install(library):
    # Check if pip exists, if not, install it (easy install better exist)
    try:
        import pip
    except ImportError:
        subprocess.check_call(["easy_install", "pip"])
        # Upgrade distribute; seems a requirement for pip 1.5 on OpenWRT
        subprocess.check_call(["easy_install","-U","setuptools"])
    
    try:
        subprocess.check_call(["pip", "install", library])
    except:
        raise Exception("Installation of library %s failed" % library)
