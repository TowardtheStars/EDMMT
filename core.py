import requests
import logging, json
import traceback
from db import *

logger = logging.getLogger()

def getLastLoc(cmdr_name, edsm_api_key):
    url = "https://www.edsm.net/api-logs-v1/get-position"
    data = {
        "commanderName": cmdr_name,
        "apiKey": edsm_api_key,
        "showId": 1
    }
    res = requests.post(url, data)

    if res.status_code == 200:
        if res.json()["msgnum"] == 100:
            return res.json()["systemId"], res.json()["system"]
        else:
            logger.error(res.json()["msg"])
    else:
        logger.error("Failed to connect to EDSM API, status code: {}".format(res.status_code))
    return None


def getNearbyStars(name:str, radius:float):
    url = "https://www.edsm.net/api-v1/sphere-systems"
    res = requests.post(url, {
        "systemName": name,
        "radius": radius,
        "showId": 1,
        "showInformation": 1
        })
    
    if res.status_code == 200:
        data = res.json()
        """ transform into 
{
    <edsm id>:
    {
        "name":<system name>, 
        "distance": <distance>
    }
}
        """

        data = {
            d["id"]:{
                "name": d["name"],
                "distance": d["distance"],
                "population": d["information"]["population"]
            }
            for d in data
        }

        return data
    else:
        logger.error("Failed to get data from EDSM: {0}".format(res.status_code))

def crossref(nearby_stars):

    return [
        {
            "edsm_id": edsm_id,
            "distance": nearby_stars[edsm_id]["distance"],
            "name": nearby_stars[edsm_id]["name"],
            "material_states": mmdb[str(edsm_id)]["material_states"],
            "population": nearby_stars[edsm_id]["population"]
        } 
        for edsm_id in nearby_stars if str(edsm_id) in mmdb.keys()
    ]

def mat_string(crossref_entry):
    mat_count = {g5: 0 for g5 in G5_MAT}
    for state in crossref_entry["material_states"]:
        for mat in HGE_TYPES[state]:
            mat_count[mat] += crossref_entry["material_states"][state]
    return ", ".join([str(ct) + ' x ' + g5 for g5, ct in mat_count.items() if ct > 0])


