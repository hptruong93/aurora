# Aurora AP/AP Slice Functions (Generates a Json File)
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json
import sys
from aurora_db import AuroraDB


class mySQLtoJSON():
    
    def __init__(self):
        self.database = AuroraDB()
    
    def convertAP(self):
        #fetch SQL data and convert to object
        sqlData = self.database.fetchall('access_point')
        data = []
        for row in sqlData:
            name = row['name']
            del row['name']
            #Turn all values into strings
            for value in row:
                row[value] = str(row[value])
            data.append([name, row])
        
        #Open JSON file for writing
        try:
            JFILE = open('aplist.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(1)
        
        json.dump(data, JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()

#Testing
mySQLtoJSON().convertAP()
        
