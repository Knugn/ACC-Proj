import sys
from pymongo import Connection
from pymongo.errors import ConnectionFailure


def main():
    """ Connect to MongoDB """
    
    try:
        getconnect= Connection(host="localhost", port=27017)
	print "Connected successfully"
    except ConnectionFailure, e:
	    sys.stderr.write("Could not connect to MongoDB: %s" % e)


if __name__ == "__main__":
	main()
