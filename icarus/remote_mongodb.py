from ssh_pymongo import MongoSession

session = MongoSession(
    host='db.example.com',
    port=21,
    user='myuser',
    key='/home/myplace/.ssh/id_rsa2'
)

db = session.connection['db-name']