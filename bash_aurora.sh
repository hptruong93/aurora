#!/bin/bash

#Usage: bash bash_aurora.sh [ap_name] [slice1_name] [slice2_name]...
#If no switch is provided, this expects name of the slices. All will use linux_bridge
#
#If switch -d or --delete is provided, and if no slice name is provided, it will attempt to delete
#all slices. Otherwise it will attempt to delete the slice with given ssids
#
#



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
else
    ap=${1}
    shift
    while [[ -n "$1" ]]; do
        aurora ap-slice-create --hint location --ap ${ap} << EOL
mcgill
1
${1}
linux_bridge
0
EOL
        shift
    done

    sleep 1
    aurora ap-slice-list
fi