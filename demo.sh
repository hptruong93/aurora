#!/bin/bash

#####################################################################
quit_at=9999
auto=0
if [[ -n "$1" ]]; then
	if [ "$1" == "-a" ]; then
		auto=1
		if [[ -n "$2" ]]; then
			quit_at=${2}
		fi
	else
		quit_at=${1}
	fi
fi


#####################################################################

wait_for_input() {
	echo Proceeding to ${1}
	if [ $auto -eq 0 ]; then
		echo "Enter 1 to continue. 2 to exit"
		select yn in "Continue" "Exit"; do
	    	case $yn in
	        	Continue ) break;;
	        	Exit ) exit;;
	    	esac
		done
	fi
}

function quit {
	if [ "$1" == "$2" ]; then
                echo Exiting at ${1}
		exit 0
	fi
}


#####################################################################
echo Step 1: Started cleaning up the system
aurora ap-slice-delete --all
sleep 3 #If the main slice cannot be deleted, we have to delete it again
aurora ap-slice-delete --all

aurora wnet-delete MedStaffWnet
aurora wnet-delete MedStaff

echo "*--------------------------------------------------------------------------*"
echo Finished cleaning up
echo Ready to start
quit ${quit_at} 1
#####################################################################
wait_for_input "create VSM slice"
echo Step 2: Creating VSM slice
#VSM
# bash bash_aurora.sh ICU VSM > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file VSM.json""
#bash bash_aurora.sh ICU VSM > /dev/null
aurora ap-slice-create --ap ICU --file VSM.json

echo Finished creating VSM slice
echo Waiting for VSM slice to be ready
sleep 6
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
quit ${quit_at} 2
#####################################################################
wait_for_input "create MedStaff slices"
echo Step 3: Creating MedStaff slices

echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file MedStaff-ICU.json""
# bash bash_aurora.sh ICU MedStaff > /dev/null
aurora ap-slice-create --ap ICU --file MedStaff-ICU.json
echo Done with slice on ICU

echo ""Command issued ------------------\> aurora ap-slice-create --ap Triage --file MedStaff-Triage.json""
# bash bash_aurora.sh Triage MedStaff > /dev/null
aurora ap-slice-create --ap Triage --file MedStaff-Triage.json
echo Done with slice on Triage

echo Finished creating MedStaff slices
echo Waiting for slices to be ready...
sleep 5
echo Slices should now be active
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
quit ${quit_at} 3
#####################################################################
wait_for_input "create MedStaff wnet"
echo Step 4: Creating wnets
echo ""Command issued ------------------\> aurora wnet-create MedStaffWnet""
aurora wnet-create MedStaffWnet

echo Finished creating MedStaffWnet wnets
echo ""Command issued ------------------\> aurora wnet-list""
aurora wnet-list
quit ${quit_at} 4
#####################################################################
wait_for_input "adding slices to MedStaffWnet wnet"

echo Step 5: Adding slices to MedStaffWnet wnet
echo ""Command issued ------------------\> aurora wnet-add-wslice MedStaffWnet --ssid MedStaff""
aurora wnet-add-wslice MedStaffWnet --ssid MedStaff

echo Finished adding slices to wnet
echo ""Command issued ------------------\> aurora wnet-show MedStaffWnet""
aurora wnet-show MedStaffWnet
quit ${quit_at} 5
#####################################################################
wait_for_input "changing MedStaff slices name to Medicine"

echo Step 6: Changing name for MedStaff slices to Medicine
echo ""Command issued ------------------\> aurora wnet-update-ssid MedStaffWnet --ssid Medicine""
aurora wnet-update-ssid MedStaffWnet --ssid Medicine

echo Command dispatched waiting for aurora agent to take action...
sleep 4
echo Waiting for changes to be applied... 
#Actually it's just a message so that user can have some feedback. We could just join the two sleeps into one
sleep 4
echo Changes applied
echo ""Command issued ------------------\> aurora wnet-show MedStaffWnet""
aurora wnet-show MedStaffWnet
quit ${quit_at} 6
#####################################################################
wait_for_input "create NurseIntern slice on Triage AP"
echo Step 7: Creating NurseIntern slice on Triage AP

echo ""Command issued ------------------\> aurora ap-slice-create --ap Triage --file NurseIntern.json""
# bash bash_aurora.sh Triage NurseIntern > /dev/null
aurora ap-slice-create --ap Triage --file NurseIntern.json

echo Finished creating NurseIntern slice on Triage AP
sleep 2
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
quit ${quit_at} 7
#####################################################################
wait_for_input "Move NurseIntern slice to ICU AP"
echo Step 8: Moving NurseIntern slice on Triage AP

echo ""Command issued ------------------\> aurora ap-slice-move --ap ICU --ssid NurseIntern""
aurora ap-slice-move --ap ICU --ssid NurseIntern

echo Finished moving NurseIntern slice on Triage AP
echo Waiting for NurseIntern to be ready
sleep 2
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
quit ${quit_at} 8
#####################################################################
wait_for_input "view statistics for NurseIntern slice"
echo Step 9: View statistics for NurseIntern slice
echo ""Command issued ------------------\> aurora ap-slice-show --ssid NurseIntern""
aurora ap-slice-show --ssid NurseIntern
quit ${quit_at} 9
#####################################################################
wait_for_input "delete slice NurseIntern"

echo Step 10: Deleting NurseIntern wnet
#Make sure that none of the slice is main slice containing the radio configuration
echo ""Command issued ------------------\> aurora ap-slice-delete --ssid NurseIntern""
aurora ap-slice-delete --ssid NurseIntern
sleep 2
echo List of slices:
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list

echo  
echo List of wnets
echo ""Command issued ------------------\> aurora wnet-list""
aurora wnet-list
