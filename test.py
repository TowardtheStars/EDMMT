
import requests, json
from db import MMDB
import asyncio
# with open("factions.json") as file:
#     eddb = json.load(file)
# print(json.dumps(eddb[0], indent=2))

mmdb = MMDB()
# mmdb.eddb_sys._from_local_file()
# print(mmdb.eddb_sys.last_update.isoformat())
mmdb.load()
print(json.dumps(len(mmdb.values()), indent=2))
print(mmdb.get("1111"))
# asyncio.get_event_loop().close()

