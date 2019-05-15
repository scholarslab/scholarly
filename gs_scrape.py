import scholarly
import csv
from os import listdir
from os.path import isfile, join
import calendar
import json
import time
from requests.utils import dict_from_cookiejar
from selenium import webdriver

# Load last data json
filename = None
for fname in [f for f in listdir(".") if isfile(join(".", f)) and f.endswith(".json") and f.startswith("gs-")]:
    filename = fname

if filename:
    with open(filename,'r') as infile:
        data = json.loads(infile.read())
else:
    data = {}

outfilename = "gs-"+str(calendar.timegm(time.gmtime()))+".json"
for file in [f for f in listdir(".") if isfile(join(".", f)) and f.endswith(".csv")]:
    with open(file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            print("Looking for: " + row[2] + " / " + row[0])
            if row[2] == "Article Title":
                continue
            # Doc UID = author + title + journal name.
            # Ideally, should use DOI, but not always available
            # Or date of publication, but not always available
            doc_id = row[0]+"/"+row[2]+"/"+row[3]
            if doc_id in data: 
                print("Found existing entry for document. Skipping: "+doc_id)
                continue
            data[doc_id] = {"csv":row}
            query = scholarly.search_pubs_query(row[2])
            matched = False
            for result in query:
                print(result)
                if row[3].lower()[:44] in result.bib["journal"].lower() and row[0].split(",")[0].lower() in result.bib["author"].lower():
                    print(
                        "Matched! " + result.bib["title"] + " / " + result.bib["author"])
                    print("================\n"+str(result)+"================\n")
                    matched = True
                    data[doc_id]["docinfo"] = result
                    data[doc_id]["citedby"] = result.get_citedby()
                    break
                else:
                    print(
                        "Not matched! " + result.bib["title"] + " / " + result.bib["author"])
            if not matched:
                print("No matches found or script has been CAPTCHAed. Quitting.")
                exit()
            with open(outfilename, 'w') as outfile:
                outfile.write(json.dumps(data))

