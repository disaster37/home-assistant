import logging
import requests
import time
import threading
from threading import RLock
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
    _lock = RLock()


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
        self._token_expiration = time.time()

        if cache_refresh is not None:
            self._cache_refresh = cache_refresh

        x = threading.Thread(target=self._updateCache)
        x.start()

        logging.warning("Call singleton constructor")
    
    def addCache(self, module):
        if module not in ["dfp", "dfpIO", "tfp", "tfpIO"]:
            raise ValueError("Module must be: dfp, dfpIO, tfp or tfpIO")
        
        if module not in self._cache:
            self._lock.acquire()
            self._cache[module] = {}
            self._lock.release()
    
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
        self._token_expiration = time.time() + 18000

        logging.debug("Auth successfully")

    
    class Decorators():
        @staticmethod
        def refreshToken(decorated):
            # the function that is used to check
            # the JWT and refresh if necessary
            def wrapper(api,*args,**kwargs):
                if time.time() > api._token_expiration:
                    try:
                        api.getAccessToken()
                    except Exception as e:
                        logging.error(e)
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

    @Decorators.refreshToken
    def tfpAction(self, action):

        if action is None or not action:
            raise ValueError("Action must be a string")

        r = self._client.post("%s/api/tfps/action/%s" % (self._url, action))

        r.raise_for_status()

        logging.info("Run action %s successfully: %s", action, r.text)
    
    
    def tfpStatus(self, item,  cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")

        # Check if value is managed by cache
        if cache is True and "tfp" in self._cache:
            return self.getFromCache("tfp", item)
        else:
            return self._tfpStatus()[item]
    
    def tfpIO(self, item, cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")

        # Check if value is managed by cache
        if cache is True and "tfpIO" in self._cache:
            return self.getFromCache("tfpIO", item)
        else:
            return self._tfpIO()[item]

    def isAvailable(self):
        return self._available
        
    def _updateCache(self):
        while True:
            logging.warning("Update cash - Lock")
            self._lock.acquire()
            try:
                for module in self._cache:
                    if module == "dfp":
                        self._cache[module] = self._dfpStatus()
                    elif module == "dfpIO":
                        self._cache[module] = self._dfpIO()
                    elif module == "tfp":
                        self._cache[module] = self._tfpStatus()
                    elif module == "tfpIO":
                        self._cache[module] = self._tfpIO()
                self._available = True
                logging.warning("Update cash - Finish")
                self._lock.release()
            except Exception as e:
                logging.error("Exception when refresh cash: %s", e)
                logging.error("Wait 30s")
                self._available = False
                self._lock.release()
                time.sleep(30)
            finally:
              logging.warning("Update cash - Unlock")

            
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

    @Decorators.refreshToken
    def _tfpStatus(self):
        r = self._client.get("%s/api/tfps" % self._url)
        r.raise_for_status()
        return r.json()["data"]["attributes"]
    
    @Decorators.refreshToken
    def _tfpIO(self):
        r = self._client.get("%s/api/tfps/io" % self._url)
        r.raise_for_status()
        return r.json()["data"]["attributes"]
    




