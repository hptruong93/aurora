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

aurora wnet-delete Triage
aurora wnet-delete NurseIntern

echo "*--------------------------------------------------------------------------*"
echo Finished cleaning up
echo Ready to start

#####################################################################
wait_for_input "create MedStaff slices"
echo Creating MedStaff slices
#MedStaff
# bash bash_aurora.sh ICU MedStaff-ICU > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file MedStaff-ICU.json""
aurora ap-slice-create --ap ICU --file MedStaff-ICU.json
echo Done with slice on ICU
# bash bash_aurora.sh Triage MedStaff-Triage > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap Triage --file MedStaff-Triage.json""
aurora ap-slice-create --ap Triage --file MedStaff-Triage.json
echo Done with slice on Triage

echo Finished creating MedStaff slices
echo Waiting for slices to be ready...
sleep 4
echo Slices should now be active
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list

#####################################################################
wait_for_input "create VSM slice"
echo Creating VSM slice
#VSM
# bash bash_aurora.sh ICU VSM > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file VSM.json""
aurora ap-slice-create --ap ICU --file VSM.json

echo Finished creating VSM slice
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
#####################################################################
wait_for_input "create MedStaff wnet"
echo Creating wnets
echo ""Command issued ------------------\> aurora wnet-create MedStaff""
aurora wnet-create MedStaff

echo Finished creating MedStaff wnets
echo ""Command issued ------------------\> aurora wnet-list""
aurora wnet-list
#####################################################################
wait_for_input "adding slices to MedStaff wnet"

echo Adding slices to MedStaff wnet
echo ""Command issued ------------------\> aurora wnet-add-wslice MedStaff --ssid MedStaff-Triage MedStaff-ICU""
aurora wnet-add-wslice MedStaff --ssid MedStaff-Triage MedStaff-ICU

echo Finished adding slices to wnet
echo ""Command issued ------------------\> aurora wnet-show MedStaff""
aurora wnet-show MedStaff
#####################################################################



#####################################################################
wait_for_input "create NurseIntern slice on Triage AP"
echo Creating NurseIntern slice on Triage AP
#Nurse Intern

# bash bash_aurora.sh Triage NurseIntern-Triage > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap Triage --file NurseIntern-Triage.json""
aurora ap-slice-create --ap Triage --file NurseIntern-Triage.json
echo Done with slice on Triage


echo Finished creating NurseIntern slice on Triage AP
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
#####################################################################
wait_for_input "create NurseIntern slice on ICU AP"
echo Creating NurseIntern slice on ICU AP
# bash bash_aurora.sh ICU NurseIntern-ICU > /dev/null
echo ""Command issued ------------------\> aurora ap-slice-create --ap ICU --file NurseIntern-ICU.json""
aurora ap-slice-create --ap ICU --file NurseIntern-ICU.json
echo Done with slice on ICU


echo Finished creating NurseIntern slice on ICU AP
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list
#####################################################################
wait_for_input "create NurseIntern wnet"
echo Creating wnets
echo ""Command issued ------------------\> aurora wnet-create NurseIntern""
aurora wnet-create NurseIntern

echo Finished creating NurseIntern wnets
echo ""Command issued ------------------\> aurora wnet-list""
aurora wnet-list
#####################################################################
wait_for_input "adding slices to NurseIntern wnet"

echo Adding slices to NurseIntern wnet
echo ""Command issued ------------------\> aurora wnet-add-wslice NurseIntern --ssid NurseIntern-Triage NurseIntern-ICU""
aurora wnet-add-wslice NurseIntern --ssid NurseIntern-Triage NurseIntern-ICU

echo Finished adding slices to wnet
echo ""Command issued ------------------\> aurora wnet-show NurseIntern""
aurora wnet-show NurseIntern
#####################################################################
wait_for_input "view statistics for NurseIntern wnet"
echo ""Command issued ------------------\> aurora wnet-show -i NurseIntern""
aurora wnet-show -i NurseIntern
#####################################################################
wait_for_input "delete wnet NurseIntern"

echo Deleting NurseIntern wnet
#Make sure that none of the slice is main slice containing the radio configuration
echo ""Command issued ------------------\> aurora wnet-delete NurseIntern --all""
aurora wnet-delete NurseIntern --all
sleep 2
echo List of slices:
echo ""Command issued ------------------\> aurora ap-slice-list""
aurora ap-slice-list

echo  
echo List of wnets
echo ""Command issued ------------------\> aurora wnet-list""
aurora wnet-list