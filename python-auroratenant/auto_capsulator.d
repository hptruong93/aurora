#!/bin/bash
# Aurora auto_capsulator Start-Up
#
# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
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