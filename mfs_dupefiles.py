#!/usr/bin/env python3

## manage duplicate files across multiple machines

import argparse
import MySQLdb
import hashlib
import socket

parser = argparse.ArgumentParser()
parser.add_argument("filename")
args = parser.parse_args()

# Only deal with real files.
if not os.path.isfile(args.filename):
    print("{0} does not exist.".format(args.filename))
    if os.path.isdir(args.filename):
        print("{0} is a directory. In the future, a recursive option will be added. For now, just one file at a time.".format(args.filename))
    sys.exit(0)

## myhash
## Returns an sha256 hash of the file passed
def myhash(pathname):
    bufsize = 1024*1024
    hasher = hashlib.sha256()
    with open(pathname, 'rb') as thefile:
        buffer = thefile.read(bufsize)
        while len(buffer) > 0:
            hasher.update(buffer)
            buffer = thefile.read(bufsize)
    return hasher.hexdigest()


#db = MySQLdb.connect(host='tendril8.local', port=3306, user='filer', passwd="filerpass", db="filedb")
db = MySQLdb.connect(host='localhost', port=3306, user='filer', passwd="filerpass", db="filedb")

## The file record that matches up with the database table
class Filerec:
    def __init__(self, pathname):
        if os.path.isfile(pathname):
            self.path = pathname
        else:
            return None
        self.name = os.path.basename()
        self.size = os.path.getsize()
        self.host = socket.gethostname()
        self.created = os.path.getctime(self.pathname)
        self.modified = os.path.getmtime(self.pathname)
        self.sha256 = myhash(self.pathname)
        self.problems = []
    
    def name_ok(self):
        if self.name == "":
            self.problems.append("File name is empty.")
            return False
        if len(self.name) > 128:
            self.problems.append("File name {0} has {1} characters, but the DB is limited to 128.".format(self.name, len(self.name)))
            return False
        if "/" in self.name:
            self.problems.append("File name, {0}, has a forward slash that will cause confusion with paths.".format(self.name))
            return False
        if "\\" in self.name:
            self.problems.append("File name, {0}, has a back slash that will cause confusion with paths.".format(self.name))
            return False
        return True
    def path_ok(self):
        if self.path == "":
            self.problems.append("File path is empty.")
            return False
        if not os.path.exists(self.path):
            self.problems.append("File path {0} does not exist.")
            return False
        if len(self.path) > 256:
            self.problems.append("File path {0} has {1} characters, but is limited to 256. Bump up the VARCHAR length in the database.".format(self.path, len(self.path)))
            return False
        return True
    def size_ok(self):
        if self.size < 0:
            self.problems.append("File size is negative! This won't do.")
            return False
        if self.size > 9223372036854775807:
            self.problems.append("File size of {0} has to be bullshit and certainly will not fit into mysql's BIGINT field.".format(self.size))
            return False
        if self.size == 0:
            self.problems.append("I will store a filesize of zero, but it will match every other empty file in the database. You may want to reconsider.")
            return True
        return True
    def host_ok(self):
        if self.host == "":
            self.problems.append("File host is empty.")
            return False
        if len(self.host) > 64:
            self.problems.append("File path {0} has {1} characters, but is limited to 256. Bump up the VARCHAR length in the database.".format(self.path, len(self.path)))
            return False
        return True
    def created_ok(self):
        return True
    def modified_ok(self):
        return True
    def sha256_ok(self):
        if len(self.sha256) != 256:
            self.problems.append("File sha hash has {0} characters, but must have exactly 256.".format(len(self.sha256)))
            return False
        return True
    def all_ok(self):
        return name_ok() and path_ok() and size_ok() and host_ok() and created_ok() and modified_ok() and sha256_ok()

    def store(self):
        if all_ok():
            if len(self.problems) > 0:
                print("Warnings:")
                for s in self.problems:
                    print(" - {0}".format(s))
                self.problems = []
            c = db.cursor()
            return c.execute("""INSERT INTO files (name, path, size, host, created, modified, sha256) VALUES ({name},{path},{size},{host},{created},{modified},{sha256})""".format(
                name = self.name,
                path = self.path,
                size = self.size,
                host = self.host,
                created = self.created,
                modified = self.modified,
                sha256 = self.sha256,))
        else:
            print("I am trying to add the file {0} to the database, but encountered problem(s):")
            for s in self.problems:
                print(" - {0}".format(s))
            self.problems = []
            return False

    ## listDupes
    ## Retrieve a list of duplicate files from DB
    def listDupes():
        c = db.cursor()
        c.execute("""SELECT * FROM files WHERE size={0} AND sha256={1}""".format(self.size, self.sha256))
        return []

    ## addFile
    ## if an identical record does not already exist, add this file to the DB
    def addFile():
        return self.store()


## Run!
# Store file characteristics in file record
FR = Filerec(args.filename)
mylist = FR.listDupes()
if len(mylist) == 0:
    FR.addFile()
    print("{0} is unique and has been added to the database.".format(FR.name))
else:
    for f in mylist:
        print(f)

