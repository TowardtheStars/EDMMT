import requests
import logging, json
import traceback



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def getCurrentLoc():
    pass

def getNearbyStars(name:str, radius:float):
    url = "https://www.edsm.net/api-v1/sphere-systems"
    res = requests.post(url, {
        "systemName": name,
        "radius": radius
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
    fmt = "https://elitebgs.app/api/ebgs/v5/systems?factionDetails=true&name="
    result = {}

    logger.info("Getting system details.")
    
    res = requests.get(fmt + "&name=".join([str(sid) for sid in stars])).json()
    stars_info = res["docs"]

    for star in stars_info:
        try:
            logger.info("Summarizing System: " + star["name"])
            
            states_primitive = [faction["faction_details"]["faction_presence"]["state"] for faction in star["factions"]]
            
            states_active = [faction["faction_details"]["faction_presence"]["active_states"] for faction in star["factions"]]
            states_active = [state for state_list in states_active for state in state_list]
            states_active = [s["state"] for s in states_active]
            
            states_recovering = [faction["faction_details"]["faction_presence"]["recovering_states"] for faction in star["factions"]]
            states_recovering = [state for state_list in states_recovering for state in state_list]
            states_recovering = [s["state"] for s in states_recovering]

            allegiance = {faction["faction_details"]["allegiance"] for faction in star["factions"]}
            
            states = set(
                map(
                    str.capitalize, 
                    (set(states_primitive) | set(states_active) | set(states_recovering) | allegiance)
                    )
                ) & HGE_STATES.keys()

            if len(states) > 0:
                result[star["name"]] = list(states)
        except Exception as e:
            logger.warning("Unable to extract data of system: " + star["name"])
            logger.warning(traceback.format_exc())

    return result

def strip2names(edsm):
    return {e["name"] for e in edsm}


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
    ss = getNearbyStars("54 Ceti", 100)
    
    logger.info("Checking populated systems")
    populated = pf(ss)
    populated = strip2names(populated)
    logger.info("Populated systems: {}".format(len(populated)))

    logger.info("Generating Manufactured States")
    states = genManuStates(populated)

    logger.info("Merging material types")
    mats = state2mat(states)
    mats = {k: v for (k, v) in mats.items() if "Chemical" in v}
    showdata(mats)

