#!/bin/bash
# Author: Mike Kobierski
# Date: March 17th, 2014
#
# Usage:    To copy all files in aurora directory 
#
#               $ ./update_manager.sh 
#
#           To copy only a single file contained somewhere in
#           aurora directory (it will be found using bash's 'find')
#
#               $ ./update_manager.sh manager.py
#
#           To copy files from a directory
#
#               $ ./update_manager.sh ap_provision
#
#           Files can be picked using a wildcard
#
#               $ ./update_manage.sh manager*

MANAGER_USERNAME=ubuntu
MANAGER_IP=132.206.206.133
HOME_AURORA_DIR=/home/ubuntu/aurora

# Functions for debugging
function echo_
# Override standard echo, rewrite support for -n (omit newline)
{
    case "$1" in
    "-n")
        shift;
        printf %s "$@"
        ;;
    *   )
        printf %s\\n "$@"
        ;;
    esac  
}

function echo_cmd
# Displays a command then waits for user to press enter
{
    echo_ -n "$PWD$ $*" && read
}

function echo_and_run
# Displays a command, then runs it and shows the output
{
    echo_cmd $1
    eval $1 | sort
    echo
}

if [[ $# -ge 1 ]];
# Check whether arguments exist - they should be files to be copied to
# manager
then
    for file in $@
    # File arguments given are allowed to contain wildcards (*), 
    # meaning many files are intended for copy.  Find them
    # and send them one at a time
    do
        relative_filenames=$(find . -name $file)
        for sub_file in $relative_filenames
        do
            #if [[ -d sub_file ]]
            sub_file_dir=${sub_file%/*}
            sub_file_dir=${sub_file_dir#.}
            # Copy to manager(132.206.206.133), strip leading '.' from relative_filename to copy to 
            # intended directory
            
            # DEBUGGING PURPOSES ONLY
            #echo_cmd "scp -r $sub_file $MANAGER_USERNAME@$MANAGER_IP:$HOME_AURORA_DIR$sub_file_dir"
            scp -r $sub_file $MANAGER_USERNAME@$MANAGER_IP:$HOME_AURORA_DIR$sub_file_dir
        done
    done
else
    echo "Copying aurora directory"
    # Don't print output from this command
    scp -r * $MANAGER_USERNAME@$MANAGER_IP:$HOME_AURORA_DIR 2>&1 1>/dev/null
fi
exit 0
