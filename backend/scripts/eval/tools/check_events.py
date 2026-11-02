# -*- coding: utf-8 -*-
import sqlite3, json

con = sqlite3.connect('backend/data/app.db')
cur = con.cursor()
cur.execute('SELECT details_json FROM runs WHERE id="3416e62a-4e0a-44bf-bb8d-c11e2f136cba"')
row = cur.fetchone()
if row and row[0]:
    d = json.loads(row[0])
    print(json.dumps(d, ensure_ascii=False, indent=2))
