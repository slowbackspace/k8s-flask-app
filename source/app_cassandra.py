
#!/usr/bin/env python3 
# -*- coding: utf-8 -*-

import datetime
import json
import os
import random
import sys
import time
from collections import defaultdict
from json import dumps

from flask import Flask, abort, render_template, request

from cassandra import ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster

app = Flask(__name__)
app.config["DEBUG"] = os.environ.get("DEBUG") or False
app.config['OUTSIDE_GKE'] = os.environ.get("OUTSIDE_GKE") or False
app.config['CASSANDRA_HOST'] = os.environ.get("CASSANDRA_HOST")
app.config['CASSANDRA_USERNAME'] = os.environ.get("CASSANDRA_USERNAME")
app.config['CASSANDRA_PASSWORD'] = os.environ.get("CASSANDRA_PASSWORD")
app.config['CASSANDRA_KEYSPACE'] = os.environ.get("CASSANDRA_KEYSPACE") or None

if app.config['OUTSIDE_GKE']:
    print("Running outside GKE")
    app.config["DEBUG"] = True
    app.config['CASSANDRA_HOST'] = "35.188.193.250"
    app.config['CASSANDRA_KEYSPACE'] = "testing"

def get_session():
    """Connect to the Cassandra hosts and return session used to execute queries"""
    hosts = []
    auth_provider = PlainTextAuthProvider(username=app.config['CASSANDRA_USERNAME'], password=app.config['CASSANDRA_PASSWORD'])
    try:
        hosts = app.config['CASSANDRA_HOST'].split(",")
    except:
        print("Could not parse list of hosts. Assuming single host.")
        hosts.append(app.config['CASSANDRA_HOST'])

    print("Connection to", hosts)
    cluster = Cluster(contact_points=hosts, auth_provider=auth_provider)
    if app.config["CASSANDRA_KEYSPACE"]:
        session = cluster.connect()
    else:
         session = cluster.connect()
    return session


@app.route('/create-table')
def create_table():
    """Creates keyspace testing and simple table structure"""
    session = get_session()
    replicas = request.args.get('replicas') or 3
    keyspace = app.config["CASSANDRA_KEYSPACE"]
    rows = session.execute("""SELECT keyspace_name FROM system_schema.keyspaces""")
    if keyspace in [row[0] for row in rows]:
        print("dropping existing keyspace...")
        session.execute("DROP KEYSPACE " + keyspace)

    session.execute("CREATE KEYSPACE IF NOT EXISTS testing WITH REPLICATION = {{ 'class':'NetworkTopologyStrategy', 'DC1': {}, 'DC2': {} }}".format(replicas, replicas))
    session.set_keyspace(keyspace)
    session.execute("""CREATE TABLE sensors(sensor1 float, sensor2 float, sensor3 float,
                        txtdata text, date timestamp PRIMARY KEY)""")
    return "ok"

@app.route('/insert-big')
def insert_big_data():
    """Insert entry to the table sensors. Entry contains randomly generated ints, date and few MB txt record."""
    db = get_db()
    multi = request.args.get('multi') or 1
    multi = int(multi)

    sql = """INSERT INTO sensors(sensor1, sensor2, sensor3, txtdata, date) VALUES (%s, %s, %s, %s, %s)"""

    txt_data = open("static/dump.txt").read()
    for i in range(0, multi):
        r = random.randint(0,1000)
        now = datetime.datetime.now()
        session.execute(sql, (r, r+1, r+2, txt_data, now.strftime('%Y-%m-%d %H:%M:%S')))
    #db.close()
    return "ok"

@app.route('/insert-simple')
def insert_data():
    """Insert entry to the table sensors. Entry contains randomly generated ints, date and small txt record."""
    multi = request.args.get('multi') or 1
    multi = int(multi)
    
    sql = """INSERT INTO sensors(sensor1, sensor2, sensor3, txtdata, date) VALUES (%s, %s, %s, %s, %s)"""
    session = get_session()
    session.set_keyspace(app.config["CASSANDRA_KEYSPACE"])

    for i in range(0, multi):
        r = random.randint(0,1000)
        now = datetime.datetime.now()
        session.execute(sql, (r, r+1, r+2, "simple_data", now.strftime('%Y-%m-%d %H:%M:%S')))
    return "ok"


@app.route('/view')
def view():
    """Gets entries from database and shows them in html table"""
    limit = request.args.get('limit')
    lt = request.args.get('lt') or 1000
    
    session = get_session()
    session.set_keyspace(app.config["CASSANDRA_KEYSPACE"])

    sql = 'SELECT sensor1, sensor2, sensor3, txtdata, date FROM sensors'
    if limit:
        sql += " LIMIT {}".format(limit)
    entries = session.execute('SELECT sensor1, sensor2, sensor3, txtdata, date FROM sensors')

    return render_template('view_cassandra.html', entries=entries)


if __name__ == '__main__':
    app.run(debug=app.config["DEBUG"], host='0.0.0.0')
