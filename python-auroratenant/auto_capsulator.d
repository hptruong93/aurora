#!/bin/bash
# Aurora auto_capsulator Start-Up
#

start() {
    screen -dm /usr/local/bin/auto_capsulator $1
}

stop() {
    pkill auto_capsulator
}

case $1 in
    start)
        start $2
    ;;
    stop)
        stop 
    ;;
    restart)
        stop
        sleep 2
        start $2
    ;;
    *)
        echo "Usage: auto_capsulator (start|stop|restart) [INTIF]"
        exit 1
    ;;
esac
exit 0