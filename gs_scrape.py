import scholarly
import csv
from os import listdir
from os.path import isfile, join
import calendar
import json
import time
from requests.utils import dict_from_cookiejar

# Load last data json
filename = None
for fname in [f for f in listdir(".") if isfile(join(".", f)) and f.endswith(".json") and f.startswith("gs-")]:
    filename = fname

if filename:
    with open(filename,'r') as infile:
        data = json.loads(infile.read())
else:
    data = {}

not_found = []

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
                #print(result)
                if row[3].lower()[:44] in result.bib["journal"].lower():
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

