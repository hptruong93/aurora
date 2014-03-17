#!/bin/bash
MANAGER_USERNAME=ubuntu
MANAGER_IP=132.206.206.133
HOME_AURORA_DIR=/home/ubuntu/aurora

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
            # Copy to manager(132.206.206.133), strip leading '.' from relative_filename to copy to 
            # intended directory
            #echo "Copying..." ${sub_file#.}
            scp -r $sub_file $MANAGER_USERNAME@$MANAGER_IP:$HOME_AURORA_DIR${sub_file#.}
        done
    done
else
    # Don't print output from this command
    scp -r * $MANAGER_USERNAME@$MANAGER_IP:$HOME_AURORA_DIR 2>&1 1>/dev/null
fi
exit 0
