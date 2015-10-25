import sys
from pymongo import MongoClient

import json

def get_db():
    client = MongoClient('192.168.0.4:12345')
    db = client.RequestsDB
    return db

def add_requests(db):

    data={"angle_start" : 0, 
	  "angle_stop" : 30,
	  "n_angles" : 10,
          "n_nodes" : 200,
          "n_levels" : 5 }
    db.Requests.insert(data)
    
def get_requests(db):
    for doc in db.Requests.find():
    	print(doc)
    return 0

if __name__ == "__main__":

    db = get_db() 
    'add_requests(db)'
    print get_requests(db)

