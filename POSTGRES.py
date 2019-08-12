import time
t0 = time.time() 

from os.path import join
from os import path

import psycopg2
import database
import pandas as pd
import urllib

from Utilities.track import ncReadTrackData
from Utilities.config import ConfigParser

rootDir = r'C:\Users\u20405\Desktop\Post'
DatabaseName = "TCHA18_points"

def loadTrack(trackId):
    """
    Given a track id, load the data from the corresponding track file.
    
    :param str trackId: A track id code that looks like "xxx-xxxxx"
    
    :returns: A :class:`Track` object containing the track data
    """ 

    trackNum, trackYear = int(trackId.split('-')[0]), int(trackId.split('-')[1])
    trackFile = join(outputPath, 'tracks', 'tracks.{0:05d}.nc'.format(trackYear))
    if not path.exists(trackFile): 
        print "Fetching from the NCI..."
        FileURL = urllib.URLopener()
        NCIPath = r"http://dapds00.nci.org.au/thredds/fileServer/fj6/TCRM/TCHA18"
        trackFileNCI = "/".join((NCIPath, 'tracks', 'tracks.{0:05d}.nc'.format(trackYear)))
        FileURL.retrieve(trackFileNCI, trackFile)
    tracks = ncReadTrackData(trackFile)
    
    return [t for t in tracks if t.trackId==(trackNum, trackYear)][0]

working_dir = r'T:\ops\community_safety\georisk_models\inundation\sandpits\sfmartin\Eclipse Workspace\TCRM'
configFile = join(working_dir, 'tcrm2.1.ini')

config = ConfigParser()
config.read(configFile)

db = database.HazardDatabase(configFile)

locations = db.getLocations()
outputPath = config.get('Output', 'Path')
gridLimit = config.geteval('Region', 'gridLimit')

# Set up the thresholds for the different TC categories
TC_thresholds = {'Category 1': 30, 'Category 2': 40, 'Category 3': 50, 'Category 4': 70, 'Category 5': 88}


events = database.selectEvents(db)   
print events

conn = psycopg2.connect(host="tcha18-loc.ckuuiccte1ka.ap-southeast-2.rds.amazonaws.com", port="5432", database="TCHA18_loc_DB", user="u20405AWS", password="BAlgP7i871TZ3fP2ilkX")
cur = conn.cursor()

print('PostgreSQL database version:')
cur.execute('SELECT version()')
db_version = cur.fetchone()
print(db_version)

# cur.execute("DROP TABLE IF EXISTS THCA18_Points")
cur.execute("""
        CREATE TABLE IF NOT EXISTS THCA18_Points (
            pointID varchar PRIMARY KEY,
            Latitude FLOAT NOT NULL,
            Longitude FLOAT,
            Location GEOGRAPHY
        )
            """)
 
count = 0
# eventId = "001-1860"
for event in events:
    eventId = event[1]
    print " "
    print "Inserting into database:", eventId
    print eventId, event[3]
    
    track = loadTrack(event[1])
    Latitude = track.Latitude
    Longitude = track.Longitude
    track.trackId
    
    for i in range(len(track.Latitude)):
        pointId = eventId + "-" + str(i)
        print count, pointId, Latitude[i], Longitude[i] 
        cur.execute("""
                select exists(select 1 from THCA18_Points where pointId=%s)
                """,(pointId,))
        rows = cur.fetchall()

        if rows[0][0] == False:
            cur.execute("""INSERT INTO THCA18_Points(pointId, Latitude, Longitude,Location)
                         VALUES(%s,%s,%s,ST_SetSRID(ST_MakePoint(%s, %s),4326))
                         ON CONFLICT (pointId) DO NOTHING 
                         RETURNING (pointId, Latitude, Longitude);
                        """, (pointId, Latitude[i], Longitude[i], Longitude[i], Latitude[i],))
        else:
            print pointId, " already in the database"
    
    conn.commit() 
    count += 1
           
cur.close()
conn.close()

print " "
print "Time taken:"
print "hours: %i, minutes: %i, seconds: %i" %(int((time.time()-t0)/3600), int(((time.time()-t0)%3600)/60), int((time.time()-t0)%60))