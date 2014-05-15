# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

#Take in either --backup or --restore
#If backup then the script will try to backup the aurora database STRUCTURE only.
#No data will be backup
if [ "$1" == "--backup"  ] || [ "$1" == "-b" ]; then
	mysqldump --no-data -u root -p aurora > aurora_backup.sql 

#Otherwise the script expects the file "aurora_backup.sql" to load back to mysql database
#If the file does not exist, the script ends by outputing a message saying the file does not exists
#The aurora database will be created by the script if not exists
#Will have to enter password twice (2 times)
elif [ "$1" == "--restore" ] || [ "$1" == "-r" ]; then
	if [ -f aurora_backup.sql ]; then
		mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS aurora"
		mysql -u root -p aurora < aurora_backup.sql
	else
		echo "aurora_backup.sql does not exists. Recheck the directory"
	fi
fi