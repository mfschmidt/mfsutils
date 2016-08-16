#!/usr/bin/env python3

## manage duplicate files across multiple machines

import argparse
import MySQLdb
import hashlib
import socket
import os
from datetime import datetime

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
## Returns an sha256 hash (represented as a 64-character string) of the file passed
def myhash(pathname):
    bufsize = 1024*1024
    hasher = hashlib.sha256()
    with open(pathname, 'rb') as thefile:
        buffer = thefile.read(bufsize)
        while len(buffer) > 0:
            hasher.update(buffer)
            buffer = thefile.read(bufsize)
    return hasher.hexdigest()
    # This 256-bit hash is 64 8-bit characters


db = MySQLdb.connect(host='tendril8.local', port=3306, user='filer', passwd="filepass", db="filedb")
#db = MySQLdb.connect(host='localhost', port=3306, user='filer', passwd="filepass", db="filedb")

## The file record that matches up with the database table
class Filerec:
    def __init__(self, pathname):
        if os.path.isfile(pathname):
            self.fullpath = os.path.realpath(pathname)
        else:
            return None
        self.path = os.path.dirname(self.fullpath)
        self.name = os.path.basename(self.fullpath)
        self.size = os.path.getsize(self.fullpath)
        self.host = socket.gethostname()
        self.created = datetime.fromtimestamp(os.path.getctime(self.fullpath)).strftime('%Y-%m-%d %H:%M:%S')
        self.modified = datetime.fromtimestamp(os.path.getmtime(self.fullpath)).strftime('%Y-%m-%d %H:%M:%S')
        self.sha256 = myhash(self.fullpath)
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
        if len(self.sha256) != 64:
            self.problems.append("File {0} sha hash has {1} characters, but must have exactly 64.".format(self.name, len(self.sha256)))
            self.problems.append("     HASH = {0}".format(self.sha256))
            return False
        return True
    def all_ok(self):
        return self.name_ok() and self.path_ok() and self.size_ok() and self.host_ok() and self.created_ok() and self.modified_ok() and self.sha256_ok()

    def store(self):
        if self.all_ok():
            if len(self.problems) > 0:
                print("Warnings:")
                for s in self.problems:
                    print(" - {0}".format(s))
                self.problems = []
            c = db.cursor()
            sqlInsertQuery = """INSERT INTO files ({fields}) VALUES (\"{name}\",\"{path}\",{size},\"{host}\",\"{created}\",\"{modified}\",\"{sha256}\")""".format(
                fields = "name, path, size, host, created, modified, sha256",
                name = self.name,
                path = self.path,
                size = self.size,
                host = self.host,
                created = self.created,
                modified = self.modified,
                sha256 = self.sha256,)
            print(sqlInsertQuery)
            try:
                c.execute(sqlInsertQuery)
                db.commit()
                return True
            except:
                print("All data passed validation, but the database server is not accepting our INSERT.")
                return False
        else:
            print("I am trying to add the file {0} to the database, but encountered problem(s):".format(self.fullpath))
            for s in self.problems:
                print(" - {0}".format(s))
            self.problems = []
            return False

    ## listDupes
    ## Retrieve a list of duplicate files from DB
    def listDupes(self):
        c = db.cursor()
        sqlSelectQuery = """SELECT * FROM files WHERE size={0} AND sha256=\"{1}\"""".format(self.size, self.sha256)
        print(sqlSelectQuery)
        c.execute(sqlSelectQuery)
        return c.fetchall()
        # TODO: Return a list of Filerec objects rather than mysqldb's ordered list. (Update printing out on line 173-175)

    ## addFile
    ## if an identical record does not already exist, add this file to the DB
    def addFile(self):
        return self.store()

    # TODO: Figure out how to add a stringified function to just "print()" the filerec

## Run!
# Store file characteristics in file record
FR = Filerec(args.filename)
mylist = FR.listDupes()
if len(mylist) == 0:
    if FR.addFile() != False:
        print("{0} is unique and has been added to the database.".format(FR.name))
    else:
        print("{0} was not added to the database.".format(FR.name))
else:
    print("Duplicate files exist:")
    for f in mylist:
        print("    on {host} : {fullpath}".format(
            host=f[3],
            fullpath=os.path.join(f[1],f[0])))

db.close()