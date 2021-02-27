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

        self.getAccessToken()
    
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
    
    @Decorators.refreshToken
    def dfpStatus(self, item):
        if item is None or not item:
            raise ValueError("Item must be a string")
        
        r = self._client.get("%s/api/dfps" % self._url)

        r.raise_for_status()

        logging.debug("Status: %s", r.text)

        return r.json()["data"]["attributes"][item]




