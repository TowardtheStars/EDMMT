import sys, os, json
from db import MMDB
from core import *

profile = {
        "name": "",
        "EDSM_API_key": ""
    }


def first_time_launching():
    print("I need your CMDR name and EDSM API key to continue.")
    profile = {
        "name": "",
        "EDSM_API_key": ""
    }
    print("CMDR Name:")
    
    profile["name"] = input()
    print("EDSM API key:")
    profile["EDSM_API_key"] = input()

    with open("profile.json", "w") as file:
        json.dump(profile, file)

def has_profile():
    flag = os.path.exists("profile.json")
    if flag:
        try:
            with open("profile.json") as file:
                profile = json.load(file)
            loc = getLastLoc(profile["name"], profile["EDSM_API_key"])
            if loc is None:
                print("Wrong profile data.")
        except Exception as e:
            print("Wrong profile data.")
        
        return loc is not None
    return False

def getloc():
    if has_profile():
        with open("profile.json") as file:
            profile = json.load(file)

        return getLastLoc(profile["name"], profile["EDSM_API_key"])



NO_MODE = -1
EXIT = 0
TRACK_MODE = 1
RANDOM_MODE = 2


def main():
    
    print("Loading Database...")
    mmdb = MMDB()
    mmdb.load()
    print("Load complete")

    while not has_profile():
        first_time_launching()
    
    running = True
    print("Tracking CMDR position")
    print("Please open EDDiscovery or other tools to keep your position tracked by EDSM.")
    print("Input searching radius (max 100, in ly): ")
    radius = float(input())

    while running:
        print("Current Location: ")
        locid, locname = getloc()
        print(locname)
        print("Checking Data...")
        data = getNearbyStars(locname, radius)
        result = crossref(mmdb.database, data)
        result.sort(key=lambda d: d["distance"])
        if len(result) > 0:
            for i in range(min(10, len(result))):
                print(result[i]["name"], result[i]["distance"], mat_string(result[i]),sep='\t')
        else:
            print("No results found.")
            print("Input searching radius (max 100, in ly): ")
            radius = float(input())
        print("Continue? Enter \"exit\" to exit program.")
        next_step = input()
        if next_step == 'exit':
            running = False

        print()

        if next_step.capitalize() in G5_MAT:
            

if __name__ == '__main__':
    main()