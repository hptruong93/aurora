# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith &
#              Mike Kobierski 
#
"""Intended entry point for Aurora Manager.

Usage::

    $ python shell.py <DEBUG|INFO|WARNING|ERROR|CRITICAL>

or::

    >>> import sys
    >>> sys.path.append('/path/to/aurora/package/dir')
    >>> from aurora.shell import main
    >>> main()

"""
import sys
import traceback
import config

from aurora import manager_http_server


def main():
    try:
        manager_http_server.main()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
