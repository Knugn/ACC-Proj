import os
import swiftclient.client

sc = get_swift_connection()

def get_swift_connection():
    config = {'user':os.environ['OS_USERNAME'],
              'key':os.environ['OS_PASSWORD'],
              'tenant_name':os.environ['OS_TENANT_NAME'],
              'authurl':os.environ['OS_AUTH_URL']
              }
    return swiftclient.client.Connection(auth_version=2, **config)

def bucket_file_line_gen(swiftconnection, bucketname, filename, chunksize = 1024*1024):
    (obj_header, obj_body) = swiftconnection.get_object(bucketname, filename, resp_chunk_size=chunksize)
    linerem = ''
    for chunk in obj_body:
        first = True
        for s in chunk.split('\n'):
            if first:
                first = False
            else:
                yield linerem
                linerem = ''
            linerem += s

def bucket_file_line_count(swiftconnection, bucketname, filename, chunksize = 1024*1024):
    linecount = 0
    for line in bucketfilelinegen(swiftconnection, bucketname, filename, chunksize):
        linecount += 1
    return linecount
