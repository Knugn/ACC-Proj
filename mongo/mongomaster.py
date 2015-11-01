import sys
from pymongo import MongoClient

import json

def get_db():
    client = MongoClient('192.168.0.4:27017',replicaset='rs0')
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

def start_replica_set():
	config ={'_id': 'rs0', 'members': [
    		{'_id': 0, 'host': 'master:27017'},
     		{'_id': 1, 'host': 'slave1:27017'},
     		{'_id': 2, 'host': 'slave2:27017'}]}

  	 c.admin.command("replSetInitiate", config)



if __name__ == "__main__":
    start_replica_set
    db = get_db() 
    add_requests(db)
    print get_requests(db)

