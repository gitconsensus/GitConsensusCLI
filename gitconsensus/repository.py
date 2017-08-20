import config
import datetime
import github3
import json
import requests
import yaml

def githubApiRequest(url):
    auth = config.getGitToken()
    headers = {
        'Accept': 'application/vnd.github.squirrel-girl-preview',
        'user-agent': 'gitconsensus',
        'Authorization': "token %s" % (auth['token'],)
    }
    return requests.get(url, headers=headers)


class Repository:

    def __init__(self, user, repository):
        self.user = user
        self.name = repository
        auth = config.getGitToken()
        self.client = github3.login(token=auth['token'])
        self.client.set_user_agent('gitconsensus')
        self.repository = self.client.repository(self.user, self.name)
        consensusurl = "https://raw.githubusercontent.com/%s/%s/master/.gitconsensus.yaml" % (self.user, self.name)
        res = githubApiRequest(consensusurl)
        self.rules = False
        if res.status_code == 200:
            self.rules = yaml.load(res.text)

    def getPullRequests(self):
        prs = self.repository.iter_pulls(state="open")
        retpr = []
        for pr in prs:
            newpr = PullRequest(self, pr.number)
            retpr.append(newpr)
        return retpr


class PullRequest:

    def __init__(self, repository, number):
        self.repository = repository
        self.number = number
        self.pr = self.repository.client.pull_request(self.repository.user, self.repository.name, number)

        # https://api.github.com/repos/OWNER/REPO/issues/1/reactions
        reacturl = "https://api.github.com/repos/%s/%s/issues/%s/reactions" % (self.repository.user, self.repository.name, self.number)
        res = githubApiRequest(reacturl)
        reactions = json.loads(res.text)

        self.yes = []
        self.no = []
        self.users = []
        for reaction in reactions:
            content = reaction['content']
            user = reaction['user']
            if content == '+1':
                self.yes.append(user['login'])
            elif content == '-1':
                self.no.append(user['login'])
            else:
                continue

            if user['login'] not in self.users:
                self.users.append(user['login'])

    def daysSinceLastCommit(self):
        commits = self.pr.iter_commits()

        for commit in commits:
            commit_date_string = commit._json_data['commit']['author']['date']

        # 2017-08-19T23:29:31Z
        commit_date = datetime.datetime.strptime(commit_date_string, '%Y-%m-%dT%H:%M:%SZ')
        now = datetime.datetime.now()
        delta = commit_date - now
        return delta.days

    def validate(self):
        if self.repository.rules == False:
            return False
        consenttest = Consensus(self.repository.rules)
        return consenttest.validate(self)

    def shouldClose(self):
        if 'timeout' in self.repository.rules:
            if self.repository.rules['timeout'] < self.daysSinceLastCommit():
                return True
        return False

    def merge(self):
        self.pr.merge('Consensus Merge')



class Consensus:
    def __init__(self, rules):
        self.rules = rules

    def validate(self, pr):
        if not self.isMergeable(pr):
            return False
        if not self.hasQuorum(pr):
            return False
        if not self.hasVotes(pr):
            return False
        if not self.hasAged(pr):
            return False
        return False

    def isMergeable(self, pr):
        if not pr.mergeable:
            return False
        return True

    def hasQuorum(self, pr):
        if 'quorum' in self.rules:
            if len(pr.users) < self.rules['quorum']:
                return False
        return True

    def hasVotes(self, pr):
        if 'threshold' in self.rules:
            ratio = len(pr.yes) / (len(pr.yes) + len(pr.no))
            if ratio < self.rules['threshold']:
                return False
        return True

    def hasAged(self, pr):
        if 'mergedelay' in self.rules:
            days = pr.daysSinceLastCommit()
            if days < self.rules['mergdelay']:
                return False
        return True
