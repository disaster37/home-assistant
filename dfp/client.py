import logging
import requests
import time
import threading
from .singleton import Singleton

class Client(metaclass=Singleton):

    _username = None
    _password = None
    _url = None
    _token = None
    _client = None
    _token_expiration = None
    _cache = {}
    _cache_refresh = 1000
    _available = False


    def __init__(self, url, username, password, cache_refresh = None):
        if url is None or not url:
            raise ValueError("URL must be a string")
        if username is None or not username:
            raise ValueError("Username must be a string")
        if password is None or not password:
            raise ValueError("Password must be a string")

        self._url = url
        self._username = username
        self._password = password
        self._cache = {}

        if cache_refresh is not None:
            self._cache_refresh = cache_refresh

        self.getAccessToken()

        x = threading.Thread(target=self._updateCache)
        x.start()
    
    def addCache(self, module):
        if module not in ["dfp", "dfpIO", "tfp", "tfpIO"]:
            raise ValueError("Module must be: dfp, dfpIO, tfp or tfpIO")
        
        if module not in self._cache:
            self._cache[module] = {}
    
    def getFromCache(self, module, item):
        if module not in ["dfp", "dfpIO", "tfp", "tfpIO"]:
            raise ValueError("Module must be: dfp, dfpIO, tfp or tfpIO")
        
        if len(self._cache[module]) == 0:
            return None
        else:
            return self._cache[module][item]
    
    def getAccessToken(self):
        payload = {
            "username": self._username,
            "password": self._password
        }
        r = requests.post("%s/token-auth" % self._url, data = payload)

        r.raise_for_status()

        self._token = r.json()["token"]

        self._client = requests.Session()
        self._client.headers.update({"Authorization": "Bearer %s" % self._token})
        self._token_expiration = time.time() + 3500

        logging.debug("Auth successfully")

    
    class Decorators():
        @staticmethod
        def refreshToken(decorated):
            # the function that is used to check
            # the JWT and refresh if necessary
            def wrapper(api,*args,**kwargs):
                if time.time() > api._token_expiration:
                    api.getAccessToken()
                return decorated(api,*args,**kwargs)

            return wrapper

    
    @Decorators.refreshToken
    def dfpAction(self, action):

        if action is None or not action:
            raise ValueError("Action must be a string")

        r = self._client.post("%s/api/dfps/action/%s" % (self._url, action))

        r.raise_for_status()

        logging.info("Run action %s successfully: %s", action, r.text)
    
    
    def dfpStatus(self, item,  cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")

        # Check if value is managed by cache
        if cache is True and "dfp" in self._cache:
            return self.getFromCache("dfp", item)
        else:
            return self._dfpStatus()[item]
    
    def dfpIO(self, item, cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")

        # Check if value is managed by cache
        if cache is True and "dfpIO" in self._cache:
            return self.getFromCache("dfpIO", item)
        else:
            return self._dfpIO()[item]

    def isAvailable(self):
        return self._available
        
    def _updateCache(self):
        while True:
            try:
                for module in self._cache:
                    if module == "dfp":
                        self._cache[module] = self._dfpStatus()
                    elif module == "dfpIO":
                        self._cache[module] = self._dfpIO()
                self._available = True
            except Exception as e:
                logging.error("Exception when refresh cash: %s", e)
                self._available = False
            
            time.sleep(self._cache_refresh / 1000)

    @Decorators.refreshToken
    def _dfpStatus(self):
        r = self._client.get("%s/api/dfps" % self._url)
        r.raise_for_status()
        return r.json()["data"]["attributes"]
    
    @Decorators.refreshToken
    def _dfpIO(self):
        r = self._client.get("%s/api/dfps/io" % self._url)
        r.raise_for_status()
        return r.json()["data"]["attributes"]
    




