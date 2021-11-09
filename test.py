
import requests, json
from db import MMDB
import asyncio
# with open("factions.json") as file:
#     eddb = json.load(file)
# print(json.dumps(eddb[0], indent=2))

mmdb = MMDB("./db/mmdb.json")
# mmdb.eddb_sys._from_local_file()
# print(mmdb.eddb_sys.last_update.isoformat())
print(json.dumps(list(mmdb.database.values())[0], indent=2))
# asyncio.get_event_loop().close()

