
#!/usr/bin/env python3 
# -*- coding: utf-8 -*-

import sys, os, json, time, random
from flask import Flask, render_template, request, abort
import datetime
from collections import defaultdict
from json import dumps

import MySQLdb
import MySQLdb.cursors


app = Flask(__name__)
app.config["DEBUG"] = os.environ.get("DEBUG") or False
app.config['OUTSIDE_GKE'] = os.environ.get("OUTSIDE_GKE") or False
app.config['MYSQL_HOST'] = os.environ.get("MYSQL_HOST")
app.config['MYSQL_USER'] = os.environ.get("MYSQL_USER")
app.config['MYSQL_PASSWORD'] = os.environ.get("MYSQL_PASSWORD")
app.config['MYSQL_DATABASE'] = os.environ.get("MYSQL_DATABASE")

if app.config['OUTSIDE_GKE']:
    print("Running outside GKE")
    app.config["DEBUG"] = True
    app.config['MYSQL_HOST'] = "35.193.158.196"
    app.config['MYSQL_USER'] = "root"
    app.config['MYSQL_PASSWORD'] = "hesloheslo"
    app.config['MYSQL_DATABASE'] = "testing"

def get_db():
    db = MySQLdb.connect(
        host=app.config['MYSQL_HOST'], 
        user=app.config['MYSQL_USER'],
        passwd=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DATABASE'])
        # cursorclass=MySQLdb.cursors.DictCursor)
    return db

def to_pretty_json(value):
    return dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

app.jinja_env.filters['tojson_pretty'] = to_pretty_json


@app.route('/create-table')
def create_table():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DROP TABLE IF EXISTS sensors")
    cursor.execute("""CREATE TABLE IF NOT EXISTS sensors(
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    sensor1 INT,
                    sensor2 INT,
                    sensor3 INT,
                    txtdata LONGTEXT,
                    date DATETIME)""")
    #db.close()
    return "ok"

@app.route('/insert-big')
def insert_big_data():
    db = get_db()
    multi = request.args.get('multi') or 1
    multi = int(multi)

    sql = """INSERT INTO sensors(sensor1, sensor2, sensor3, txtdata, date) VALUES (%s, %s, %s, %s, %s)"""
    c = db.cursor()

    entries = []
    txt_data = open("static/dump.txt").read()
    for i in range(0, multi):
        r = random.randint(0,1000)
        now = datetime.datetime.now()
        try:
            c.execute(sql, (r, r+1, r+2, txt_data, now.strftime('%Y-%m-%d %H:%M:%S')))
            db.commit()
        except Exception as e:
            db.rollback()
            print(e)
            abort(500)
    #db.close()
    return "ok"

@app.route('/insert-simple')
def insert_data():
    db = get_db()
    multi = request.args.get('multi') or 1
    multi = int(multi)
    
    sql = """INSERT INTO sensors(sensor1, sensor2, sensor3, txtdata, date) VALUES (%s, %s, %s, %s, %s)"""
    c = db.cursor()

    for i in range(0, multi):
        r = random.randint(0,1000)
        now = datetime.datetime.now()
        try:
            c.execute(sql, (r, r+1, r+2, "simple_data", now.strftime('%Y-%m-%d %H:%M:%S')))
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
    #db.close()
    return "ok"


@app.route('/view')
def view():
    db = get_db()
    limit = request.args.get('limit')
    lt = request.args.get('lt') or 1000
    cursor = db.cursor()

    entries = []

    sql = "SELECT * FROM sensors \
        WHERE sensor1 < '%d' LIMIT %d" % (int(lt)+1, int(limit))
    # Execute the SQL command
    cursor.execute(sql)
    # Fetch all the rows in a list of lists.
    entries = cursor.fetchall()
   
    # disconnect from server
    #db.close()

    return render_template('view_mysql.html', entries=entries, dbstats=[], collstats=[], count=0)


if __name__ == '__main__':
    app.run(debug=app.config["DEBUG"], host='0.0.0.0')
