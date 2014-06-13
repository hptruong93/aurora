#!/bin/bash

wait_for_input() {
	echo Proceeding to ${1}
	echo "Enter 1 to continue. 2 to exit"
	select yn in "Continue" "Exit"; do
    	case $yn in
        	Continue ) break;;
        	Exit ) exit;;
    	esac
	done
}

#####################################################################
echo Started cleaning up the system
aurora ap-slice-delete --all
sleep 3 #If the main slice cannot be deleted, we have to delete it again
aurora ap-slice-delete --all

aurora wnet-delete MedStaffWnet
aurora wnet-delete MedStaff

echo "*--------------------------------------------------------------------------*"
echo Finished cleaning up
echo Ready to start

#####################################################################
wait_for_input "create VSM slice"
echo Creating VSM slice
#VSM
# bash bash_aurora.sh ICU VSM > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file VSM.json""
bash bash_aurora.sh ICU VSM > /dev/null

echo Finished creating VSM slice
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
#####################################################################
wait_for_input "create MedStaff slices"
echo Creating MedStaff slices
#MedStaff
echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file MedStaff-ICU.json""
bash bash_aurora.sh ICU MedStaff > /dev/null

echo Done with slice on ICU
echo ""Command issued ------------------\> aurora ap-slice-create --ap Triage --file MedStaff-Triage.json""
bash bash_aurora.sh Triage MedStaff > /dev/null
echo Done with slice on Triage

echo Finished creating MedStaff slices
echo Waiting for slices to be ready...
sleep 4
echo Slices should now be active
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list

#####################################################################
wait_for_input "create MedStaff wnet"
echo Creating wnets
echo ""Command issued ------------------\> aurora wnet-create MedStaffWnet""
aurora wnet-create MedStaffWnet

echo Finished creating MedStaffWnet wnets
echo ""Command issued ------------------\> aurora wnet-list""
aurora wnet-list
#####################################################################
wait_for_input "adding slices to MedStaffWnet wnet"

echo Adding slices to MedStaffWnet wnet
echo ""Command issued ------------------\> aurora wnet-add-wslice MedStaffWnet --ssid MedStaff""
aurora wnet-add-wslice MedStaffWnet --ssid MedStaff

echo Finished adding slices to wnet
echo ""Command issued ------------------\> aurora wnet-show MedStaffWnet""
aurora wnet-show MedStaffWnet

#####################################################################
wait_for_input "create NurseIntern slice on Triage AP"
echo Creating NurseIntern slice on Triage AP

echo ""Command issued ------------------\> aurora ap-slice-create --ap Triage --file NurseIntern-Triage.json""
bash bash_aurora.sh Triage NurseIntern > /dev/null

echo Finished creating NurseIntern slice on Triage AP
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
#####################################################################
wait_for_input "Move NurseIntern slice to ICU AP"
echo Moving NurseIntern slice on Triage AP

echo ""Command issued ------------------\> aurora ap-slice-move --ap ICU --ssid NurseIntern""
aurora ap-slice-move --ap ICU --ssid NurseIntern

sleep 2
echo Finished moving NurseIntern slice on Triage AP
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
#####################################################################
wait_for_input "view statistics for NurseIntern slice"
echo ""Command issued ------------------\> aurora ap-slice-show --ssid NurseIntern""
aurora ap-slice-show --ssid NurseIntern
#####################################################################
wait_for_input "delete slice NurseIntern"

echo Deleting NurseIntern wnet
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
