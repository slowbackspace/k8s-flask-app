
#!/usr/bin/env python3 
# -*- coding: utf-8 -*-

import sys, os, json, time, random
from flask import Flask, render_template, request
from pymongo import MongoClient
from pymongo import ReadPreference
from pymongo.errors import ServerSelectionTimeoutError
from bson.timestamp import Timestamp
import datetime
from collections import defaultdict
from bson.json_util import dumps
from pymongo.read_preferences import ReadPreference    


app = Flask(__name__)
app.config["DEBUG"] = os.environ.get("DEBUG") or False
app.config['OUTSIDE_GKE'] = os.environ.get("OUTSIDE_GKE") or False
app.config['MONGODB_CONNECTION_URI'] = os.environ.get("MONGODB_CONNECTION_URI")
if app.config['OUTSIDE_GKE']:
    app.config["DEBUG"] = True
    app.config['MONGODB_CONNECTION_URI'] = "mongodb://admin:abc123@35.188.1.215:27017/admin"

print("Connecting to {}".format(app.config['MONGODB_CONNECTION_URI']))

connection_uri = app.config['MONGODB_CONNECTION_URI']
c = MongoClient(app.config['MONGODB_CONNECTION_URI'])


def to_pretty_json(value):
    return dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

app.jinja_env.filters['tojson_pretty'] = to_pretty_json

@app.route('/enable-sharding')
def enable_sharding():
    # call just once
    c.admin.command('enablesharding', "sensors")
    c.admin.command('shardcollection', "sensors.dc", key={"_id": 1}) 
    return "ok"

@app.route('/insert-big')
@app.route('/insert-big/<w>')
def insert_big_data(w=1):

    db = c.sensors # use database 

    entries = []
    txt_data = open("static/dump.txt").read()
    for i in range(0, 1): 
        r = random.randint(0,1000)
        entries.append({"sensor1": r, "sensor2": r+1, "sensor3": r+2, "txtdata": txt_data, "date": datetime.datetime.now()})
    
    db.dc.insert_many(entries)
    return "ok"

@app.route('/insert-simple')
@app.route('/insert-simple/<w>')
def insert_data(w=1):
    multi = request.args.get('multi') or 1
    multi = int(multi)
    db = c.sensors # use database 

    for i in range(0, multi):
        r = random.randint(0,1000)
        entry = {"sensor1": r, "sensor2": r+1, "sensor3": r+2, "txtdata": "simple_data", "date": datetime.datetime.now()}
        db.dc.insert(entry)
    return "ok"


@app.route('/view/<read_pref>')
def view(read_pref="primary"):
    preferences_map = {
        "primary": ReadPreference.PRIMARY,
        "secondary": ReadPreference.SECONDARY,
        "primary-preferred": ReadPreference.PRIMARY_PREFERRED,
        "secondary-preferred": ReadPreference.SECONDARY_PREFERRED,
        "nearest": ReadPreference.NEAREST,
    }

    limit = request.args.get('limit')
    lt = request.args.get('lt') or 1000
    read_pref = preferences_map.get(read_pref) or preferences_map["primary"]
    db = c.get_database('sensors', read_preference=read_pref)
    entries = db.dc.find({"sensor1": {"$lt": int(lt) }}).limit(int(limit)) if limit else db.dc.find({"sensor1": {"$lt": int(lt)}})
    count = db.dc.find({"sensor1": {"$lt": int(lt)}}).count() if lt else db.dc.count()


    # print collection statistics
    #collstats = db.command("collstats", "dc")

    # print database statistics
    #dbstats =  db.command("dbstats")
    collstats = ""
    dbstats = ""

    return render_template('view.html', entries=entries, dbstats=dbstats, collstats=collstats, count=count)

@app.route('/status')
def status():
    # while not c.is_mongos:
    #     time.sleep(1)
        
    # shards = c.admin.command("listshards")
    config_db = c.config
    shards = list(config_db.shards.find())
    mongos = config_db.mongos.find()
    chunks = config_db.chunks.find()
    
    rs_members = defaultdict(list)
    for shard in shards:
        if '/' in shard['host']:
            # woa, it's a replicaset, gotta show some stats
            hosts = shard['host'].split(",")[1]
            replset_name = shard['host'].split("/")[0]

            if not app.config['OUTSIDE_GKE']:
                s = MongoClient("mongodb://"+hosts+"/?replicaSet="+replset_name, username="admin", password="abc123", serverSelectionTimeoutMS=2000)
                try:
                    rs = s['admin'].command("replSetGetStatus")
                    members = sorted(rs['members'], key=lambda x: x['state'])
                except ServerSelectionTimeoutError:
                    members = []
            else:
                members = [{'_id': 0, 'name': 'mongod-shard3-0.mongodb-shard3-service.default.svc.cluster.local:27017', 'health': 1.0, 'state': 1, 'stateStr': 'PRIMARY', 'uptime': 9893, 'optime': {'ts': Timestamp(1524251064, 1), 't': 1}, 'optimeDate': datetime.datetime(2018, 4, 20, 19, 4, 24), 'electionTime': Timestamp(1524241192, 2), 'electionDate': datetime.datetime(2018, 4, 20, 16, 19, 52), 'configVersion': 5, 'self': True}, {'_id': 1, 'name': 'mongod-shard3-1.mongodb-shard3-service.default.svc.cluster.local:27017', 'health': 1.0, 'state': 2, 'stateStr': 'SECONDARY', 'uptime': 9826, 'optime': {'ts': Timestamp(1524251064, 1), 't': 1}, 'optimeDurable': {'ts': Timestamp(1524251064, 1), 't': 1}, 'optimeDate': datetime.datetime(2018, 4, 20, 19, 4, 24), 'optimeDurableDate': datetime.datetime(2018, 4, 20, 19, 4, 24), 'lastHeartbeat': datetime.datetime(2018, 4, 20, 19, 4, 31, 580000), 'lastHeartbeatRecv': datetime.datetime(2018, 4, 20, 19, 4, 32, 548000), 'pingMs': 0, 'syncingTo': 'mongod-shard3-0.mongodb-shard3-service.default.svc.cluster.local:27017', 'configVersion': 5}, {'_id': 2, 'name': 'mongod-shard3-2.mongodb-shard3-service.default.svc.cluster.local:27017', 'health': 1.0, 'state': 2, 'stateStr': 'SECONDARY', 'uptime': 9788, 'optime': {'ts': Timestamp(1524251064, 1), 't': 1}, 'optimeDurable': {'ts': Timestamp(1524251064, 1), 't': 1}, 'optimeDate': datetime.datetime(2018, 4, 20, 19, 4, 24), 'optimeDurableDate': datetime.datetime(2018, 4, 20, 19, 4, 24), 'lastHeartbeat': datetime.datetime(2018, 4, 20, 19, 4, 31, 580000), 'lastHeartbeatRecv': datetime.datetime(2018, 4, 20, 19, 4, 31, 507000), 'pingMs': 0, 'syncingTo': 'mongod-shard3-0.mongodb-shard3-service.default.svc.cluster.local:27017', 'configVersion': 5}]
            json_shard_members = []
            for member in members:
                rs_members[replset_name].append({"stateStr": member["stateStr"], "name": member["name"],
                                            "syncingTo": member.get("syncingTo", None), "uptime": member["uptime"] })

    from pprint import pprint
    pprint(rs_members)

    return render_template('index.html', shards=shards, mongos=mongos, rs_members=rs_members, chunks=chunks)


if __name__ == '__main__':
    app.run(debug=app.config["DEBUG"], host='0.0.0.0')
