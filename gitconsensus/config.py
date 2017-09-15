import os
import yaml

settings = False
cwd = os.getcwd()
path = "%s/%s" % (os.getcwd(), '/.gitconsensus.yaml')


def getSettings():
    global settings
    return settings


def reloadSettings():
    global settings
    if os.path.isfile(path):
        with open(path, 'r') as f:
            settings = yaml.load(f)
    return settings


def getGitToken():
    token = id = ''
    with open("%s/%s" % (os.getcwd(), '/.gitcredentials'), 'r') as fd:
        return {
            "id": fd.readline().strip(),
            "token": fd.readline().strip()
        }
    return False

reloadSettings()
