import scholarly
import csv
from os import listdir
from os.path import isfile, join
import calendar
import json
import time
from requests.utils import dict_from_cookiejar
import sys


def match_journals(input,gs):
    for word in gs.strip("…. ").split(" "):
        if word.upper() not in input.upper():
            return False
    return True

input_files = []
json_prefix = "gs"
if len(sys.argv) > 1:
    print("Using csv input and json state for: ",sys.argv[1:])
    input_files = [sys.argv[1]]
    json_prefix = ".".join(sys.argv[1].split(".csv")[:-1])
else:
    input_files = [f for f in listdir(".") if isfile(join(".", f)) and f.endswith(".csv")]

# Load last data json
filename = None
for fname in [f for f in listdir(".") if isfile(join(".", f)) and f.endswith(".json") and f.startswith(json_prefix+"-")]:
    filename = fname

if filename:
    with open(filename,'r') as infile:
        data = json.loads(infile.read())
    print("Found existing json state file for input csv: ",filename)
else:
    data = {}

not_found = []

outfilename = json_prefix+"-"+str(calendar.timegm(time.gmtime()))+".json"
for file in input_files:
    if len(input_files)>1:
        print("Opening CSV input file: ",file)
    with open(file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row)==0 or row[2] == "Article Title":
                continue
            # Doc UID = author + title + journal name.
            # Ideally, should use DOI, but not always available
            # Or date of publication, but not always available
            doc_id = row[0]+"/"+row[2]+"/"+row[3]
            if doc_id in data: 
                print("Found entry in JSON state. Skipping: "+doc_id)
                continue
            print("Looking for: " + doc_id)
            data[doc_id] = {"csv":row}
            query = scholarly.search_pubs_query(row[2])
            matched = False
            for result in query:
                if "journal" in result.bib and match_journals(row[3], result.bib["journal"]):
                    print(
                        "Matched! " + result.bib["title"] + " / " + result.bib["author"])
                    print("================\n"+str(result)+"================\n")
                    matched = True
                    data[doc_id]["docinfo"] = result.__dict__
                    data[doc_id]["citedby"] = []
                    for citedby in result.get_citedby():
                        data[doc_id]["citedby"].append(citedby.__dict__)
                    break
                else:
                    print(
                        "Result does not match query! Checking next document. " + result.bib["title"] + " / " + result.bib["author"])
            if not matched:
                print("ERROR: No matches found. Skipping.")
                not_found.append(row)
                with open("not_found.json", 'w') as outfile:
                    outfile.write(json.dumps(not_found))
                continue
            with open(outfilename, 'w') as outfile:
                outfile.write(json.dumps(data))

