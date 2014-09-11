#!/usr/bin/python3

import time
from datetime import date, datetime, timedelta
import re
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

def get_raw_table(sheetname):
    start = time.time()
    sheet = ll.worksheet(sheetname)
    raw_table = sheet.get_all_values()
    print("Took {}s to fetch worksheet '{}'".format(round(time.time()-start, 3), sheetname))
    return raw_table

def get_dates(raw_table):
    dates = []
    found_first = False
    for i, d in enumerate([raw_table[i][0] for i in range(0, len(raw_table))]):
        if d and len(d.split("/")) == 3:
            month, day, year = map(int, d.split("/"))
            d = date(year, month, day)
            dates.append(d.isoformat())
            if not found_first:
                found_first = True
                print("Found first date: '{}' at i: {}".format(d.isoformat(), i))
        elif found_first:
            print("Last date: {}".format(date))
            break

    return dates


def get_main():
    raw_table = get_raw_table("M")

    categories = raw_table[2]
    labels = raw_table[3]
    dates = get_dates(raw_table)

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





"""-------------------------------------------------------------------
Here begins the extraction from the table and the export into Zenobase
-------------------------------------------------------------------"""

with open("pwd_zenobase.txt") as f:              
    username, password = f.read().split("\n")[:2]
zapi = zenobase.ZenobaseAPI(username, password)

def create_streaks():
    table = get_main()
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

def create_daily_supps():
    raw_table = get_raw_table("D")
    labels = raw_table[0]
    dates = get_dates(raw_table)
    bucket = zapi.create_or_get_bucket("Lifelogger - Supps")
    bucket_id = bucket["@id"]

    for i, label in enumerate(labels):
        if not label:
            continue
        for j, date in enumerate(dates):
            if not raw_table[j+2][i]:
                continue
            try:
                weight = float(raw_table[j+2][i])
            except ValueError:
                print("Invalid data in cell: '{}', skipping".format(raw_table[j+2][i]))
                continue
            event = zenobase.ZenobaseEvent(
                    {"timestamp": date+"T00:00:00.000+02:00",
                     "tag": label,
                     "weight": {
                         "@value": weight,
                         "unit": "mg"
                     }})
            print(event)
            zapi.create_event(bucket_id, event)

def create_timestamped_supps():
    raw_table = get_raw_table("RD")
    labels = raw_table[2]
    dates = get_dates(raw_table)
    bucket = zapi.create_or_get_bucket("Lifelogger - TSupp")
    bucket_id = bucket["@id"]

    r_weight = re.compile("^[0-9\.]+")
    r_unit = re.compile("mcg|ug|mg|g")

    for i in range(8, len(labels), 2):
        for j, date in enumerate(dates):
            time_cell = raw_table[j+3][i]
            text_cell = raw_table[j+3][i+1]
            if not time_cell:
                continue
            time = time_cell
            
            try:
                weight = float(r_weight.findall(text_cell)[0])
                unit = r_unit.findall(text_cell)[0]
            except (ValueError, IndexError):
                print("Could not parse weight or unit: '{}', skipping".format(text_cell))
                continue

            # Unsupported units
            if unit in ["mcg", "ug"]:
                unit = "mg"
                weight = weight/1000

            event = zenobase.ZenobaseEvent(
                    {"timestamp": date+"T"+time+".000+02:00",
                     "tag": text_cell.split(" ")[1],
                     "weight": {
                         "@value": weight,
                         "unit": unit
                    }})
            print(event)
            zapi.create_event(bucket_id, event)


if input("Create streaks? (y/N): ") == "y":
    create_streaks()
if input("Create daily supplements? (y/N): ") == "y":
    create_daily_supps()
if input("Create timestamped supplements? (y/N): ") == "y":
    create_timestamped_supps()
