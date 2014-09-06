#!/usr/bin/python3

import time

import gspread

email, password = open("pwd.txt").read().split("\n")[:2]
gc = gspread.login(email, password)
print("Authorized successfully!")

ll = gc.open("Lifelogger")
#print("Worksheets: {}".format(ll.worksheets()))
s_main = ll.worksheet("M")


def fetch():
    return s_main.get_all_values()
start = time.time()
raw_table = fetch()
print("Took {}s to fetch".format(time.time()-start))

categories = raw_table[2]
labels = raw_table[3]
print(categories)

dates = []
for date in [raw_table[i][0] for i in range(4, len(raw_table))]: #s_main.col_values(1)[4:]:
    if date and len(date.split("/")) == 3:
        # TODO: Format to YYYY-MM-DD
        dates.append(date)
    else:
        print(date)
        break
print(dates)

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
        if cell:
            print(cell)
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
    print(table)
    return table

table = load_table()

