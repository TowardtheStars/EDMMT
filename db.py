import json, requests, os
from datetime import datetime, timezone
import asyncio, traceback
import logging
import logging.config
from logging import getLogger

logging.config.fileConfig('log.conf')

HGE_TYPES = {
    "federation": {"Composite"}, 
    "empire": {"Shielding"}, 
    "boom": {"Heat", "Alloys"}, 
    "civil unrest": {"Mechanical components"}, 
    "war": {"Thermic", "Capacitors"}, 
    "outbreak": {"Chemical"}
}

G5_MAT = ("Chemical", "Composite", "Shielding", "Heat", "Alloys", "Mechanical components", "Thermic", "Capacitors")

class AbstractRemoteDataBase:
    def __init__(self, local_path, *args, **kwargs):
        self._last_update = datetime.min
        self.local_path = local_path
        
        self._dirs = os.path.split(self.local_path)[0]
        self._logger = getLogger()
        self._create_dirs()
        self._db = {}

        self._editable = kwargs.get("editable", False)

        # load local database after definations
        if os.path.exists(self.local_path):
            self._from_local_file()

    @property
    def last_update(self):
        return self._last_update

    def __getattr__(self, attr):
        forward_db_interfaces = [
            "get", "keys", "values", "items", 
            "__getitem__", "__iter__", "__len__", "__contains__"
        ]
        __forward_set_interfaces = [
            "__setitem__", "update", "clear"
        ]
        if self._editable:
            forward_db_interfaces = forward_db_interfaces + __forward_set_interfaces
        
        if attr in forward_db_interfaces:
            return getattr(self._db, attr)
        return self.__dict__[attr]

    @property
    def logger(self):
        return self._logger

    def load(self):
        if not os.path.exists(self.local_path):
            self.logger.debug("Local file \"{}\" does not exist, fetching from remote.".format(self.local_path))
            self.update_from_remote()
        else:
            self._from_local_file()
            self.check_update()
        
    def update_from_remote(self):
        if self._update_from_remote():
            self.save_to_local()

    def _update_from_remote(self):
        """
Override this to define a sync function, return True when update succeeded
        """
        raise NotImplemented

    def _from_local_file(self):
        """
Override this to load local file
        """
        pass

    def _save_to_local(self):
        """
Directories should already be created
        """
        raise NotImplemented

    def _create_dirs(self):
        if not os.path.exists(self._dirs):
            os.makedirs(self._dirs)

    def save_to_local(self):
        self._create_dirs()
        self._save_to_local()

    def should_update(self):
        raise NotImplemented

    @property
    def database(self):
        if not os.path.exists(self.local_path):
            self.logger.debug("Local file \"{}\" does not exist, fetching from remote.".format(self.local_path))
            self.update_from_remote()
        else:
            if len(self._db) == 0:
                self._from_local_file()
            # self.check_update() # Check update should be run seperatly
        return self._db

    def check_update(self):
        if self.should_update():
            self.update_from_remote()

    async def check_update_async(self):
        self.check_update()


class RemoteEDDBDataBase (AbstractRemoteDataBase):

    VERSION = 6

    def __init__(self, 
        name:str, local_path:str=None,
        request_headers:dict=None, converter:callable=None
        ):
        
        AbstractRemoteDataBase.__init__(self, local_path or "./db/eddb_" + name + ".json")
        
        self.name = name

        self._logger = self._logger.getChild("EDDB:" + name)
        self._remote_url = name

        # Default headers retrieve gziped data
        self.request_headers = request_headers or {"Accept-Encoding":"gzip, deflate, sdch"}
        self.converter = converter or (lambda x:x)
    
    @property
    def remote_url(self):
        return "https://eddb.io/archive/v{}/".format(self.VERSION) + self._remote_url + ".json"

    def _update_from_remote(self):
        self.logger.info("Updating database {0} from URL:{1}".format(self.name, self.remote_url))
        res = requests.get(self.remote_url, headers=self.request_headers)
        if res.status_code == 200:
            self._db = self.converter(json.loads(res.content))
            self._last_update = datetime.strptime(res.headers["Last-Modified"], '%a, %d %b %Y %H:%M:%S %Z')
            self.logger.info("Update complete.")
            return True
        else:
            self.logger.warning("Unable to sync with EDDB, using local datebase instead. Status Code: {}".format(res.status_code))
            return False

    def _save_to_local(self):
        with open(self.local_path, "w") as file:
            mdb = {
                "db": self._db,
                "timestamp": self.last_update.isoformat()
            }
            json.dump(mdb, file, indent=2)

    def _from_local_file(self):
        self.logger.info("Loading from local file \"" + self.local_path + "\"")
        try:
            with open(self.local_path) as file:
                mdb = json.load(file)
                self._db = mdb["db"]
                _last_update = datetime.fromisoformat(mdb["timestamp"])
                self._last_update = _last_update
                self.logger.debug("Local DB timestamp: " + self.last_update.isoformat())

        except Exception as e:
            self.logger.error("Unable to load from local database.")
            self.logger.error(traceback.format_exc())
        

    def should_update(self):
        """
Head the URL to check if EDDB data is updated
        """
        self.logger.info("Checking Updates of {{{name}}} from EDDB".format(name=self.name))
        res = requests.head(self.remote_url, headers=self.request_headers)
        if res.status_code != 200:
            self.logger.warning("Unable to link to EDDB, please check your Internet connection.")
            return False
        headers = res.headers
        self.logger.debug("Remote: Last-Modified: {}".format(headers["Last-Modified"]))
        self.logger.debug("Local: Last-Update: {}".format(self.last_update.isoformat()))
        lastmodified = datetime.strptime(headers["Last-Modified"], '%a, %d %b %Y %H:%M:%S %Z')
        return self._last_update < lastmodified


class MMDB(AbstractRemoteDataBase):
    """
    MMDB
    -----------
    Manufactured Materials Database (MMDB) organized in JSON structure

    MMDB Structure:
    {
        <edsm id>:
        {
            "edsm_id": <edsm id>, 
            "name": <system name>,
            "material_states":
            {
                "empire": <empire faction count>,
                "federation": <federation faction count>,
                "outbreak": <faction count>,
                "war": <faction count, war and civil war both counted>,
                "boom": <faction count>,
                "civil unrest": <faction count>
            },
            "population": <population>
        }
    }
    
    Get latest DB from EDDB

    Convert EDDB data to MMDB after updating database

---------
    Request URL
    - https://eddb.io/archive/v6/systems_populated.json
    - https://eddb.io/archive/v6/factions.json

    Headers:
    - Accept-Encoding: gzip, deflate, sdch
    
    """
    VERSION = 2

    def __init__(self, local_path=None, **kwargs):

        if local_path is None:
            local_path = "./db/mmdb.json"

        AbstractRemoteDataBase.__init__(self, local_path)

        self._logger = self._logger.getChild("MMDB")

        self.eddb_sys = RemoteEDDBDataBase(
            name="systems_populated",
            local_path=kwargs.get("systems_db_local", None)
        )

        self.eddb_faction = RemoteEDDBDataBase(
            name="factions",
            local_path=kwargs.get("factions_db_local", None),
            converter=lambda db: {str(faction["id"]): faction for faction in db}
        )

    @property
    def last_update_systems(self):
        return self.eddb_sys.last_update

    @property
    def last_update_factions(self):
        return self.eddb_faction.last_update        

    def _update_from_remote(self):
        
        def passData(dst, src, *args, **kwargs):
            for k in args:
                dst[k] = src[k]
            for k, v in kwargs.items():
                if isinstance(v, str):
                    dst[k] = src[v]
                elif isinstance(v, tuple):
                    dst[k] = v[1](src[v[0]])

        def convert(system):
            item = {}

            def count_states(factions):
                states = list()
                for faction in factions:
                    allegiance = [self.eddb_faction.database.get(str(faction["minor_faction_id"]))["allegiance"].lower()]
                    active = [state["name"].lower() for state in faction["active_states"]]
                    recovering = [state["name"].lower() for state in faction["recovering_states"]]
                    states += allegiance + active + recovering
                
                state_count = {
                    name: states.count(name) for name in HGE_TYPES.keys()
                }

                state_count["war"] += states.count("civil war")
                return state_count

            passData(
                item, system, 
                "edsm_id", "name", "population",
                material_states=("minor_factions_presences", count_states)
                )

            return item

        try:
            self.logger.info("Checking Updates")
            loop = asyncio.get_event_loop()
            task = [
                asyncio.ensure_future(self.eddb_sys.check_update_async()),
                asyncio.ensure_future(self.eddb_faction.check_update_async()),
            ]
            loop.run_until_complete(asyncio.wait(task))
            self.logger.info("Update complete")

            mmdb = {system["edsm_id"]: convert(system) for system in self.eddb_sys.database if system["is_populated"]}
                
            self._last_update = datetime.now(timezone.utc)

            self._db = mmdb
            result = True
        except Exception as e:
            self.logger.error("Failed updating MMDB")
            self.logger.error(traceback.format_exc())
            result = False
        return result

    def should_update(self):
        return self.eddb_sys.should_update() or self.eddb_faction.should_update() or self.version < MMDB.VERSION

    def _save_to_local(self):
        with open(self.local_path, "w") as file:
            json.dump(
                {
                    "db": self._db,
                    "timestamp": self.last_update.isoformat(),
                    "version": self.VERSION
                }, 
                file, indent=2
                )

    def _from_local_file(self):
        with open(self.local_path) as file:
            mdb = json.load(file)
            self._db = mdb["db"]
            self.version = mdb["version"]
            self._last_update = datetime.fromisoformat(mdb["timestamp"])
        self.logger.info("Loaded Database, size: {}".format(len(self._db)))


