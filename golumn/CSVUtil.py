from __future__ import print_function
from pandas import read_csv
import threading

data = read_csv("tmp/data_10m.csv",
                error_bad_lines=False,
                chunksize=10000
                )

data.columns  # all column labels
data.index    # number of records

data.iloc[0][0]

count = list()
src = "/Users/scott.pierce/code/golumn/tmp/data_10m.csv"
# raw count
sum((1 for line in open(src, 'rb')))


def line_index(src):
    counts = list()
    offset = 0
    with open(src, "r") as f:
        for line in f:
            size = len(line)
            offset += size
            counts.append((size, offset))
    return counts


def blocks(files, size=65536):
    while True:
        b = files.read(size)
        if not b: break
        yield b

with open("file", "r") as f:
    print(sum(bl.count("\n") for bl in blocks(f)))


chunks = read_csv("/Users/scott.pierce/code/golumn/tmp/data_10m.csv",
                error_bad_lines=False,
                chunksize=10000
                )

count = 0
for chunk in chunks:
        chunk.to_sql(name='Table', if_exists='append', con=con)
        count += 1
        print(count)
reader

data.columns  # all column labels
data.index    # number of records

data.iloc[0][0]

