#!/bin/bash

#Usage without switch: bash bash_aurora.sh [ap_name] [slice1_name] [slice2_name]...
#If no switch is provided, this expects ap name, followed by names of the slices. All will use linux_bridge
#
# [var] indicates optional var
# (A / B) means either A or B would work
# [var...] indicates possiblity to include infinitely many var at this place
#
# List of switches:
# (-d / --delete) slice-ssid [slice-ssid...] --> delete slices by ssid. If nothing provided, delete all
# (-l / --list) --> list all slices
# (-r / --restart) slice-id --> restart slice with id (uuid of the slice)
# (-t / --hint) [slice-load] --> create slice with --hint option
# (-s / --show) slice-id [slice-id...] --> show slice with given id
# (-p / --ap-list) name-of-ap --> list ap
# (-ps / --ap-show) name-of-ap --> show ap
# (-w / --wnet-list) --> list all wnets
# (-ws / --wnet-show) wnet-name --> show wnet with given name
# (-c / --wnet-create) new-wnet-name --> create wnet with given name
# (-a / --wnet-add-wslice) slice-ssid [slice-ssid...] --> add slice with ssid into wnet



if [ "$1" == "-d" ] || [ "$1" == "--delete" ]; then
    if [[ -n "$2" ]]; then
        while [[ -n "$2" ]]; do
            echo aurora ap-slice-delete --ssid ${2}
            aurora ap-slice-delete --ssid ${2}
            shift
            sleep 1
        done
    else
        echo aurora-ap-slice-delete --all
        aurora ap-slice-delete --all
    fi
elif [ "$1" == "-l" ] || [ "$1" == "--list" ]; then
    echo aurora-ap-slice-list
    aurora ap-slice-list 
elif [ "$1" == "-r" ] || [ "$1" == "--restart" ]; then
    if [[ -n "$2" ]]; then
        echo aurora ap-slice-restart ${2}
        aurora ap-slice-restart ${2}
    else
        echo Missing what to restart2
    fi
elif [ "$1" == "-t" ] || [ "$1" == "--hint" ]; then
    if [[ -n "$2" ]] && ([ "$2" == "--slice-load" ] || [ "$2" == "-l" ]); then
        echo aurora ap-slice-create --hint location slice-load
        aurora ap-slice-create --hint location slice-load
    else
        echo aurora ap-slice-create --hint location
        aurora ap-slice-create --hint location
    fi
elif [ "$1" == "-s" ] || [ "$1" == "--show" ]; then
    if [[ -n "$2" ]]; then
        echo aurora ap-slice-show ${2}
        aurora ap-slice-show ${2}
    else
        echo Missing slice to show
    fi
elif [ "$1" == "-p" ] || [ "$1" == "--ap-list" ]; then
    echo aurora ap-list
    aurora ap-list
elif [ "$1" == "-ps" ] || [ "$1" == "--ap-show" ]; then
    if [[ -n "$2" ]]; then
        echo aurora ap-show ${2}
        aurora ap-show ${2}
    else
        echo Missing ap to show
    fi
elif [ "$1" == "-w" ] || [ "$1" == "--wnet-list" ]; then
    echo aurora wnet-list
    aurora wnet-list
elif [ "$1" == "-ws" ] || [ "$1" == "--wnet-show" ]; then
    if [[ -n "$2" ]]; then
        while [[ -n "$2" ]]; do
            echo aurora wnet-show ${2}
            aurora wnet-show ${2}
        done
    else
        echo Missing wnet name to show
    fi
elif [ "$1" == "-c" ] || [ "$1" == "--wnet-create" ]; then
    if [[ -n "$2" ]]; then
        while [[ -n "$2" ]]; do
            echo aurora wnet-create ${2}
            aurora wnet-create ${2}
            shift
        done
    else
        echo Missing name to create wnet
    fi
elif [ "$1" == "-a" ] || [ "$1" == "--wnet-add-wslice" ]; then
    if [[ -n "$2" ]]; then
        wnet_name=${2}
        while [[ -n "$3" ]]; do
            echo aurora wnet-add-wslice ${wnet_name} --ssid ${3}
            aurora wnet-add-wslice ${wnet_name} --ssid ${3}
            shift
        done
    else
        echo Missing wnet name
    fi
else
    ap=${1}
    shift
    while [[ -n "$1" ]]; do
        aurora ap-slice-create --hint location --ap ${ap} --ssid ${1} --location mcgill --bridge linux_bridge << EOL
1
0
EOL
        shift
        sleep 5
    done

    sleep 1
    aurora ap-slice-list
fi
