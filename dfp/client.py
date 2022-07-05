import logging
import requests
import time
from .singleton import Singleton


class Client(metaclass=Singleton):

    _username = None
    _password = None
    _url = None
    _token = None
    _client = None
    _token_expiration = None
    _timeout = None


    def __init__(self, url, username, password):
        if url is None or not url:
            raise ValueError("URL must be a string")
        if username is None or not username:
            raise ValueError("Username must be a string")
        if password is None or not password:
            raise ValueError("Password must be a string")

        self._url = url
        self._username = username
        self._password = password
        self._token_expiration = time.time()
        self._client = requests.Session()
        self._timeout = 10

        self._client.headers.update({"Content-Type": "application/json"})
    
    
    
    def getAccessToken(self):
        payload = {
            "username": self._username,
            "password": self._password
        }
        r = requests.post("%s/token-auth" % self._url, json = payload, timeout =  self._timeout)

        r.raise_for_status()

        self._token = r.json()["token"]
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

        r = self._client.post("%s/api/dfps/action/%s" % (self._url, action), timeout =  self._timeout)

        r.raise_for_status()

        logging.info("Run action %s successfully: %s", action, r.text)
    
    
    @Decorators.refreshToken
    def dfpStatus(self, item):
        if item is None or not item:
            raise ValueError("Item must be a string")

        r = self._client.get("%s/api/dfps" % self._url, timeout =  self._timeout)
        r.raise_for_status()
        return r.json()["data"]["attributes"][item]
    
    @Decorators.refreshToken
    def dfpIO(self, item, cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")

        r = self._client.get("%s/api/dfps/io" % self._url, timeout =  self._timeout)
        r.raise_for_status()
        return r.json()["data"]["attributes"][item]

    @Decorators.refreshToken
    def tfpAction(self, action):

        if action is None or not action:
            raise ValueError("Action must be a string")

        r = self._client.post("%s/api/tfps/action/%s" % (self._url, action), timeout =  self._timeout)

        r.raise_for_status()

        logging.info("Run action %s successfully: %s", action, r.text)
    
    
    @Decorators.refreshToken
    def tfpStatus(self, item,  cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")

        r = self._client.get("%s/api/tfps" % self._url, timeout =  self._timeout)
        r.raise_for_status()
        return r.json()["data"]["attributes"][item]

    @Decorators.refreshToken
    def tankStatus(self, item, name,  cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")
        if name is None or not name:
            raise ValueError("Name must be a string")

        r = self._client.get("%s/api/tanks/%s" % (self._url, name), timeout =  self._timeout)
        r.raise_for_status()
        return r.json()["data"]["attributes"][item]
    
    @Decorators.refreshToken
    def tfpIO(self, item, cache = False):
        if item is None or not item:
            raise ValueError("Item must be a string")
    
        r = self._client.get("%s/api/tfps/io" % self._url, timeout =  self._timeout)
        r.raise_for_status()
        return r.json()["data"]["attributes"][item]
        
    




