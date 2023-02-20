from json import loads
import os
from tempfile import NamedTemporaryFile

from pytest import fixture

from toodledo import TokenStorageFile, Toodledo, TaskCache


class TokenReadOnly:
    """Read the API tokens from an environment variable"""

    def __init__(self, name):
        self.name = name
        self.token = self.Load()

    def Save(self, token):
        """Do nothing - this may cause a problem if the refresh token
        changes"""
        self.token = token

    def Load(self):
        """Load and return the token. Called by Toodledo class"""
        return loads(os.environ[self.name])


@fixture(scope='session', params=['cached', 'direct'])
def toodledo(request):
    if "TOODLEDO_TOKEN_STORAGE" in os.environ:
        tokenStorage = TokenStorageFile(os.environ["TOODLEDO_TOKEN_STORAGE"])
    else:
        # for travis
        tokenStorage = TokenReadOnly("TOODLEDO_TOKEN_READONLY")
    session = Toodledo(clientId=os.environ["TOODLEDO_CLIENT_ID"],
                       clientSecret=os.environ["TOODLEDO_CLIENT_SECRET"],
                       tokenStorage=tokenStorage,
                       scope="basic tasks notes folders write")
    with NamedTemporaryFile() as cache_file:
        if request.param == 'cached':
            os.unlink(cache_file.name)
            session = TaskCache(
                session, cache_file.name, fields='folder,context,duedate,'
                'duedatemod,length,note,parent,priority,repeat,star,startdate,'
                'status,tag')
        yield session
