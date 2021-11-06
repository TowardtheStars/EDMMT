import requests
import logging, json


HGE_STATES = {
"Federation": {"Composite"}, 
"Empire": {"Shielding"}, 
"Boom": {"Heat", "Alloys"}, 
"Civil Unrest": {"Mechanical components"}, 
"War": {"Thermic", "Capacitors"}, 
"Civil War": {"Thermic", "Capacitors"}, 
"Outbreak": {"Chemical"}
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def getCurrentLoc():
    pass

def getNearbyStars(name:str, radius:float):
    url = "https://www.edsm.net/api-v1/sphere-systems"
    res = requests.post(url, {
        "systemName": name,
        "radius": radius,
        "showInformation": 1,
        "showId": 1
        })

    
    if res.status_code == 200:
        return res.json()
    else:
        logger.error("Failed to get data from EDSM: {0}".format(res.status_code))

# def chewPop(j):
#     return {entry["name"]: entry["information"]["population"] if len(entry["information"]) > 0 else 0 for entry in j}



class PopulationFilterEDSM:
    def __init__(self, threshold=0):
        self.threshold = threshold

    def filter(self, entry):
        try:
            return entry["information"]["population"] > self.threshold
        except:
            return False

    def __call__(self, data:list):
        return [d for d in data if self.filter(d)]

def showdata(jsondata):
    print(json.dumps(jsondata, indent=2))


def genManuStates(stars:list):
    fmt = "https://eddbapi.kodeblox.com/api/v4/populatedsystems?systemaddress="
    result = {}

    logger.info("Getting system details.")
    res = requests.get(fmt + "&systemaddress=".join([str(sid) for sid in stars])).json()
    stars_info = res["docs"]

    while int(res["page"]) < int(res["pages"]):
        res = requests.get(fmt+"&systemaddress=".join([str(sid) for sid in stars])+"&page="+str(int(res["page"]) + 1)).json()
        stars_info.extend(res["docs"])


    for star in stars_info:
        logger.info("Summarizing System: " + star["name"])

        states = {s["name"] for s in star["states"]}
        faction_url = "https://elitebgs.app/api/ebgs/v5/factions?allegiance=federation&minimal=true&allegiance=empire&system=" + star["name"]
        
        f_res = requests.get(faction_url).json()
        f_data = f_res["docs"]
        while int(f_res["page"]) < int(f_res["pages"]):
            f_res = requests.get(faction_url + "&page=" + str(int(f_res["page"]) + 1)).json()
            f_data.extend(f_res["docs"])
        
        emp = False
        fed = False
        for f in f_data:
            if emp and fed:
                break
            elif not emp and f["allegiance"] == "empire":
                emp = True
                states.add("Empire")
            elif not fed and f["allegiance"] == "federation":
                fed = True
                states.add("Federation")

        states = states & set(HGE_STATES.keys())

        if len(states) > 0:
            result[star["name"]] = list(states)

    return result

def strip2names(edsm):
    return {e["id64"]: e["name"] for e in edsm}


def reduceEDSM2name(l):
    return [e["name"] for e in l]


def state2mat(states:dict):
    def turn(sts):
        res = set()
        for s in sts:
            res = res | HGE_STATES[s]
        return list(res)
    return {k: turn(v) for (k, v) in states.items()}

if __name__ == '__main__':
    pf = PopulationFilterEDSM(1000000)

    logger.info("Getting nearby stars from EDSM")
    ss = getNearbyStars("54 Ceti", 40)
    
    logger.info("Checking populated systems")
    populated = pf(ss)
    populated = strip2names(populated)
    logger.info("Populated systems: {}".format(len(populated)))

    logger.info("Generating Manufactured States")
    states = genManuStates(populated.keys())

    logger.info("Merging material types")
    mats = state2mat(states)
    showdata(mats)

