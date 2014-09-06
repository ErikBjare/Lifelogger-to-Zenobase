#!/usr/bin/python3

import time
from datetime import date, datetime, timedelta
import pprint

import requests
import gspread

import zenobase


with open("pwd.txt") as f:
    email, password = f.read().split("\n")[:2]
    gc = gspread.login(email, password)
print("Authorized successfully!")

ll = gc.open("Lifelogger")
#print("Worksheets: {}".format(ll.worksheets()))
s_main = ll.worksheet("M")


start = time.time()
raw_table = s_main.get_all_values()
print("Took {}s to fetch".format(time.time()-start))

categories = raw_table[2]
labels = raw_table[3]

dates = []
for d in [raw_table[i][0] for i in range(4, len(raw_table))]: #s_main.col_values(1)[4:]:
    if d and len(d.split("/")) == 3:
        month, day, year = map(int, d.split("/"))
        d = date(year, month, day)
        dates.append(d.isoformat())
    else:
        print("Last date: {}".format(date))
        break

def next_cat_col(i):
    n = 1
    while True:
        if i+n > len(categories)-1:
            return i
        if categories[i+n]:
            return i+n
        n += 1

def get_category_labels(i):
    end_col = next_cat_col(i)
    return zip(range(i, end_col), labels[i:end_col])

def get_label_cells(category, label):
    ci = categories.index(category)
    i = labels.index(label, ci)
    cells = {}
    for j, date in enumerate(dates):
        cell = raw_table[4+j][i]
        if cell and cell != "#VALUE!":
            cells[date] = cell
    return cells

def load_table():
    table = {}
    for i, cat in enumerate(categories):
        if not cat:
            continue
        table[cat] = {}
        #print(cat)
        for i, label in get_category_labels(i):
            table[cat][label] = get_label_cells(cat, label)
            #print(" - {}".format(label))
    #pprint.pprint(table, indent=2)
    return table

table = load_table()


def create_streaks():
    with open("pwd_zenobase.txt") as f:              
        username, password = f.read().split("\n")[:2]
    zapi = zenobase.ZenobaseAPI(username, password)
    bucket = zapi.create_or_get_bucket("Lifelogger - Streaks")
    bucket_id = bucket["@id"]
    for label in table["Streaks"]:
        for d in table["Streaks"][label]:
            val = table["Streaks"][label][d]
            mapping = {"TRUE": 1, "FALSE": -1}
            try:
                state = mapping[val]
            except KeyError:
                print("Warning, could not detect state of '{}'".format(val))
                continue
            event = zenobase.ZenobaseEvent({"timestamp": d+"T00:00:00.000+02:00", "count": state, "tag": label})
            zapi.create_event(bucket_id, event)
            print("Created event: {}".format(event))

create_streaks()



