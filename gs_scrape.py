import scholarly
import csv
from os import listdir
from os.path import isfile, join
import calendar
import json
import time
from requests.utils import dict_from_cookiejar
import sys
import Levenshtein
import string
import unidecode


QUERY_LIMIT = 10

def match_journals(input,comparison):
    for word in comparison.strip("…. ").split(" "):
        if alphas_only(word) not in alphas_only(input):
            #print("Did not match journal: ",input," / ",comparison)
            return False
    return True

def match_names(input,comparison):
    if "," in input:
        name = input.split(",")[0]
    elif " " in input:
        name = input.split(" ")[0]
    else:
        print("ERROR: Malformed name: ", input)
    if alphas_only(name) in alphas_only(comparison):
        return True
    #print("Did not match name: ",input," / ",comparison)
    return False

def alphas_only(input):
    words = []
    for word in input.split(" "):
        words.append("".join(filter(str.isalnum, unidecode.unidecode(word))).upper())
    return " ".join(words)

def fuzzy_compare(input,comparison,threshold=30,strip_articles=True,stopwords = ["In memoriam","[Chinese characters]"],truncation=156):
    for stopword in stopwords:
        input = input.upper().replace(stopword.upper(),"")
        comparison = comparison.upper().replace(stopword.upper(),"")
    input = alphas_only(input.upper()[:truncation]) if len(input) > truncation else alphas_only(input.upper())
    comparison = alphas_only(comparison.upper())
    if strip_articles:
        if input.strip().startswith("THE "):
            input = input.strip()[4:]
        elif input.strip().startswith("A "):
            input = input.strip()[2:]
        if comparison.strip().startswith("THE "):
            comparison = comparison.strip()[4:]
        elif comparison.strip().startswith("A "):
            comparison = comparison.strip()[2:]
    distance = Levenshtein.distance(input,comparison)
    if distance < len(input)*threshold/100:
        return True
    if len(input) > len(comparison):
        distance = Levenshtein.distance(input[:len(comparison)],comparison)
        if distance < len(input)*threshold/300:
            return True
    if len(input) < len(comparison):
        distance = Levenshtein.distance(input,comparison[:len(input)])
        if distance < len(input)*threshold/300:
            return True
    #print("Did not match fuzzy text: ",input," / ",comparison)
    return False

# with open("/Users/ssl2ab/projects/scholarly/JIABS2010-1559327675-clean.json",'r') as infile:
#         data = json.loads(infile.read())
# cleanup = set()
# for doc in data:    
#     if "docinfo" not in data[doc]:
#         print("NO DOCINFO found: ",doc)
#         cleanup.add(doc)
#     elif not fuzzy_compare(data[doc]["csv"][2],data[doc]["docinfo"]["bib"]["title"]):
#         print("DOES NOT MATCH: ")
#         print("    ",data[doc]["csv"][2])
#         print("    ",data[doc]["docinfo"]["bib"]["title"])
#         cleanup.add(doc)
# for doc in cleanup:
#     data.pop(doc)
# exit()

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
                #print("Found entry in JSON state. Skipping: "+doc_id)
                continue
            print("Looking for: " + doc_id)
            query = scholarly.search_pubs_query(row[2])
            matched = False
            count = 0
            for result in query:
                count+=1
                if "title" in result.bib and fuzzy_compare(row[2],result.bib["title"]) \
                    and "journal" in result.bib and match_journals(row[3], result.bib["journal"]) \
                    and "author" in result.bib and match_names(row[0],result.bib["author"]):
                    print(
                        "Matched! " + result.bib["title"] + " / " + result.bib["author"])
                    #print("================\n"+str(result)+"================\n")
                    matched = True
                    data[doc_id] = {"csv":row}
                    data[doc_id]["docinfo"] = result.__dict__
                    data[doc_id]["citedby"] = []
                    for citedby in result.get_citedby():
                        data[doc_id]["citedby"].append(citedby.__dict__)
                    break
                else:
                    print(
                        "Result does not match query! Checking next document. " + result.bib["title"] + " / " + result.bib["author"])
                    if count >= QUERY_LIMIT:
                        break
            if not matched:
                print("ERROR: No matches found. Skipping.")
                not_found.append(row)
                with open("not_found.json", 'w') as outfile:
                    outfile.write(json.dumps(not_found))
                continue
            with open(outfilename, 'w') as outfile:
                outfile.write(json.dumps(data))

