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
            # support older versions by converting from day to hours.
            if 'version' not in settings or settings['version'] < 2:
                if 'mergedelay' in settings and settings['mergedelay']:
                    settings['mergedelay'] = settings['mergedelay'] * 24
                if 'timeout' in settings and settings['timeout']:
                    settings['timeout'] = settings['timeout'] * 24
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
