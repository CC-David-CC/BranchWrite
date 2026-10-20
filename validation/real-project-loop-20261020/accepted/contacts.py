"""Run: python3 contacts.py SEARCH_TEXT"""
import argparse
from directory import load_contacts, search_contacts

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("query",nargs="?",default="")
    args=parser.parse_args()
    for entry in search_contacts(load_contacts("contacts.json"),args.query):
        print(entry["name"])

if __name__=="__main__": main()
