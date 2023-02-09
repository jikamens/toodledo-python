Overview
========

Python wrapper for the Toodledo v3 API which is documented at
http://api.toodledo.com/3/. Available on PyPI at
https://pypi.org/project/toodledo/.

This fork is being actively maintained by Jonathan Kamens
<jik@kamens.us>. Thanks to Rehan Khwaja for creating this library.

Usage
=====

If you're using this library to build a web app that will be used by
multiple people, you need to be familiar with how to use OAuth2 for
authentication between your web app and Toodledo. Explaining how to do
that is beyond the scope of this document.

To use the library, you need to register an app in your Toodledo
account. This can be done at
https://api.toodledo.com/3/account/doc_register.php. You will need the
client ID and client secret for your app shown on the registration
page to connect to the API.

If you're using this library to build a private script you're running
yourself, you will probably want to use the
``CommandLineAuthorization`` function in the library to authenticate
the first time. Something like this:

.. code-block:: python

  import os
  from toodledo import TokenStorageFile, CommandLineAuthorization
  
  tokenFilePath = "fill in path to token file"
  clientId = "fill in your app client ID"
  clientSecret = "fill in your app client secret"
  scope = "basic tasks notes folders write"
  tokenStorage = TokenStorageFile(tokenFilePath)

  if not os.path.exists(tokenFilePath):
      CommandLineAuthorization(clientId, clientSecret, scope, tokenStorage)

It will prompt you to visit a URL, which will prompt you to log into
Toodledo if you're not already logged in, then click a "SIGN IN"
button. The sign in will fail since you presumably specified a bogus
redirect URL when registering the app, but you can then copy the
failed URL from your browser back into the script to complete the
authentication process.

Once you've authenticated, you create an API instance like this:

.. code-block:: python

  toodledo = Toodledo(
    clientId=clientId,
    clientSecret=clientSecret,
    tokenStorage=tokenStorage, 
    scope=scope)

And here's how you call the API:

.. code-block:: python
                
  account = toodledo.GetAccount()

  allTasks = toodledo.GetTasks(params={})

See `this more extensive example
<https://gist.github.com/jikamens/bad36fadfa73ee4f0ac1269ab3025f67>`_
of using the API in a script.

Developing the library
======================

The library uses ``poetry`` for managing packages, building, and
publishing. You can do ``poetry install`` at the top level of the
source tree to install all of the needed dependencies to build and run
the library. ``poetry build`` builds packages, and ``poetry publish``
publishes them to PyPI.

All the code in the library is both pylint and flake8 clean, and any
PRs that are submitted should maintain that. Run ``pylint *.py tests
toodledo`` and ``flake8`` to check everything.

To run the tests, set the following environment variables:

- TOODLEDO_TOKEN_STORAGE - path to a json file which will contain the
  credentials
- TOODLEDO_CLIENT_ID - your client id (see
  https://api.toodledo.com/3/account/doc_register.php)
- TOODLEDO_CLIENT_SECRET - your client secret (see
  https://api.toodledo.com/3/account/doc_register.php)

Then generate the credentials json file by running

.. code-block:: bash

  python generate-credentials.py

Then run the tests by executing

.. code-block:: bash

  pytest

in the root directory.

Please ensure that all the tests pass in any PRs you submit.
