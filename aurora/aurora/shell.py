import sys
import traceback

from aurora import manager_http_server


def main():
    try:
        manager_http_server.main()

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()