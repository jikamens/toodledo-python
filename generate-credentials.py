#! /usr/bin/env python

"""Generate credentials for tests and updating Travis"""

from contextlib import suppress
import os

from toodledo import CommandLineAuthorization, TokenStorageFile

def EscapeForBash(token):
    charactersToEscape = "{}\"[]: "
    for character in charactersToEscape:
        token = token.replace(character, "\\" + character)
    return token

def main():
    tokenStorage = TokenStorageFile(os.environ["TOODLEDO_TOKEN_STORAGE"])

    CommandLineAuthorization(os.environ["TOODLEDO_CLIENT_ID"],
                             os.environ["TOODLEDO_CLIENT_SECRET"],
                             "basic tasks notes folders write", tokenStorage)

    with suppress(ImportError):
        from pyperclip import copy  # pylint: disable=import-outside-toplevel
        with open(os.environ["TOODLEDO_TOKEN_STORAGE"], encoding="ascii") as f:
            token = f.read()
        token = EscapeForBash(token)
        copy(token)
        print("Escaped token copied to clipboard - update Travis "
              "TOODLEDO_TOKEN_READONLY environment variable")

if __name__ == "__main__":
    main()
