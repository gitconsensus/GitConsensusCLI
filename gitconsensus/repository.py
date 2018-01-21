from gitconsensus import config
import datetime
import github3
import json
import requests
import yaml

message_template = """
This Pull Request has been %s by [GitConsensus](https://github.com/tedivm/GitConsensus).

## Vote Totals

| Yes | No | Abstain | Voters |
| --- | -- | ------- | ------ |
| %s  | %s | %s      | %s     |


## Vote Breakdown

%s


## Vote Results

| Criteria   | Result |
| ---------- | ------ |
| Has Quorum | %s     |
| Has Votes  | %s     |

"""


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
        self.contributors = False
        self.collaborators = {}
        auth = config.getGitToken()
        self.client = github3.login(token=auth['token'])
        self.client.set_user_agent('gitconsensus')
        self.repository = self.client.repository(self.user, self.name)
        consensusurl = "https://raw.githubusercontent.com/%s/%s/master/.gitconsensus.yaml" % (self.user, self.name)
        res = githubApiRequest(consensusurl)
        self.rules = False
        if res.status_code == 200:
            self.rules = yaml.load(res.text)
            # support older versions by converting from day to hours.
            if 'version' not in self.rules or self.rules['version'] < 2:
                if 'mergedelay' in self.rules and self.rules['mergedelay']:
                    self.rules['mergedelay'] = self.rules['mergedelay'] * 24
                if 'timeout' in self.rules and self.rules['timeout']:
                    self.rules['timeout'] = self.rules['timeout'] * 24


    def getPullRequests(self):
        prs = self.repository.iter_pulls(state="open")
        retpr = []
        for pr in prs:
            newpr = PullRequest(self, pr.number)
            retpr.append(newpr)
        return retpr

    def getPullRequest(self, number):
        return PullRequest(self, number)

    def isContributor(self, username):
        if not self.contributors:
            contributor_list = self.repository.iter_contributors()
            self.contributors = [str(contributor) for contributor in contributor_list]
        return username in self.contributors

    def isCollaborator(username):
        if username not in self.collaborators:
            self.collaborators[username] = self.repository.is_collaborator(username)
        return self.repository.is_collaborator(username)

    def getConsensus(self):
        return Consensus(self.rules)

    def setLabelColor(self, name, color):
        try:
            self.repository.create_label(name, color)
        except:
            self.repository.update_label(name, color)


class PullRequest:
    labels = False
    def __init__(self, repository, number):
        self.repository = repository
        self.consensus = repository.getConsensus()
        self.number = number
        self.pr = self.repository.client.pull_request(self.repository.user, self.repository.name, number)

        # https://api.github.com/repos/OWNER/REPO/issues/1/reactions
        reacturl = "https://api.github.com/repos/%s/%s/issues/%s/reactions" % (self.repository.user, self.repository.name, self.number)
        res = githubApiRequest(reacturl)
        reactions = json.loads(res.text)

        self.yes = []
        self.no = []
        self.abstain = []

        self.contributors_yes = []
        self.contributors_no = []
        self.contributors_abstain = []

        self.users = []
        self.doubles = []
        for reaction in reactions:
            content = reaction['content']
            user = reaction['user']
            username = user['login']

            if username in self.doubles:
                continue

            if 'blacklist' in self.repository.rules and self.repository.rules['blacklist']:
                if username in self.repository.blacklist:
                    continue

            if 'collaborators_only' in self.repository.rules and self.repository.rules['collaborators_only']:
                if not isCollaborator(username):
                    continue

            if 'contributors_only' in self.repository.rules and self.repository.rules['contributors_only']:
                if not self.repository.isContributor(username):
                    continue

            if 'whitelist' in self.repository.rules:
                if username not in self.repository.rules['whitelist']:
                    continue

            if 'prevent_doubles' in self.repository.rules and self.repository.rules['prevent_doubles']:
                # make sure user hasn't voted twice
                if content == '+1' or content == '-1' or content == 'confused':
                    if username in self.users:
                        self.doubles.append(username)
                        self.users.remove(username)
                        if username in self.yes:
                            self.yes.remove(username)
                        if username in self.no:
                            self.no.remove(username)
                        if username in self.abstain:
                            self.abstain.remove(username)
                        if username in self.contributors_yes:
                            self.contributors_yes.remove(username)
                        if username in self.contributors_no:
                            self.contributors_no.remove(username)
                        if username in self.contributors_abstain:
                            self.contributors_abstain.remove(username)
                        continue

            if content == '+1':
                self.users.append(user['login'])
                self.yes.append(user['login'])
                if self.repository.isContributor(user['login']):
                    self.contributors_yes.append(user['login'])
            elif content == '-1':
                self.users.append(user['login'])
                self.no.append(user['login'])
                if self.repository.isContributor(user['login']):
                    self.contributors_no.append(user['login'])
            elif content == 'confused':
                self.users.append(user['login'])
                self.abstain.append(user['login'])
                if self.repository.isContributor(user['login']):
                    self.contributors_abstain.append(user['login'])

        files = self.pr.iter_files()
        self.changes_consensus = False
        self.changes_license = False
        for changed_file in files:
            if changed_file.filename == '.gitconsensus.yaml':
                self.changes_consensus = True
            if changed_file.filename.lower().startswith('license'):
                self.changes_license = True

    def hoursSinceLastCommit(self):
        commits = self.pr.iter_commits()

        for commit in commits:
            commit_date_string = commit._json_data['commit']['author']['date']

        # 2017-08-19T23:29:31Z
        commit_date = datetime.datetime.strptime(commit_date_string, '%Y-%m-%dT%H:%M:%SZ')
        now = datetime.datetime.utcnow()
        delta = now - commit_date
        return delta.total_seconds() / 3600

    def hoursSincePullOpened(self):
        now = datetime.datetime.utcnow()
        delta = now - self.pr.created_at.replace(tzinfo=None)
        return delta.total_seconds() / 3600

    def hoursSinceLastUpdate(self):
        hoursOpen = self.hoursSincePullOpened()
        hoursSinceCommit = self.hoursSinceLastCommit()
        if hoursOpen < hoursSinceCommit:
            return hoursOpen
        return hoursSinceCommit

    def changesConsensus(self):
        return self.changes_consensus

    def changesLicense(self):
        return self.changes_license

    def getIssue(self):
        return self.repository.repository.issue(self.number)

    def validate(self):
        if self.repository.rules == False:
            return False
        return self.consensus.validate(self)

    def shouldClose(self):
        if 'timeout' in self.repository.rules:
            if self.hoursSinceLastUpdate() >= self.repository.rules['timeout']:
                return True
        return False

    def close(self):
        self.pr.close()
        self.addLabels(['gc-closed'])
        self.cleanInfoLabels()
        self.commentAction('closed')

    def vote_merge(self):
        self.pr.merge('GitConsensus Merge')
        self.addLabels(['gc-merged'])
        self.cleanInfoLabels()

        if 'extra_labels' in self.repository.rules and self.repository.rules['extra_labels']:
            self.addLabels([
            'gc-voters %s' % (len(self.users),),
            'gc-yes %s' % (len(self.yes),),
            'gc-no %s' % (len(self.no),),
            'gc-age %s' % (self.hoursSinceLastUpdate(),)
            ])
        self.commentAction('merged')

    def addInfoLabels(self):
        labels = self.getLabelList()

        licenseMessage = 'License Change'
        if self.changesLicense():
            self.addLabels([licenseMessage])
        else:
            self.removeLabels([licenseMessage])

        consensusMessage = 'Consensus Change'
        if self.changesConsensus():
            self.addLabels([consensusMessage])
        else:
            self.removeLabels([consensusMessage])

        hasQuorumMessage = 'Has Quorum'
        needsQuorumMessage = 'Needs Votes'
        if self.consensus.hasQuorum(self):
            self.addLabels([hasQuorumMessage])
            self.removeLabels([needsQuorumMessage])
        else:
            self.removeLabels([hasQuorumMessage])
            self.addLabels([needsQuorumMessage])

        passingMessage = 'Passing'
        failingMessage = 'Failing'
        if self.consensus.hasVotes(self):
            self.addLabels([passingMessage])
            self.removeLabels([failingMessage])
        else:
            self.removeLabels([passingMessage])
            self.addLabels([failingMessage])

    def cleanInfoLabels(self):
        self.removeLabels(['Failing', 'Passing', 'Needs Votes', 'Has Quorum'])

    def commentAction(self, action):
        table = self.buildVoteTable()
        message = message_template % (
            action,
            str(len(self.yes)),
            str(len(self.no)),
            str(len(self.abstain)),
            str(len(self.users)),
            table,
            self.consensus.hasQuorum(self),
            self.consensus.hasVotes(self)
        )

        if len(self.doubles) > 0:
            duplist = ["[%s](https://github.com/%s)" % (username, username) for username in self.doubles]
            dupuserstring = ', '.join(duplist)
            dupstring = '\n\nThe following users voted for multiple options and were exlcuded: \n%s' % (dupuserstring)
            message = "%s\n%s" % (message, dupstring)

        self.addComment(message)

    def buildVoteTable(self):
        table = '| User | Yes | No | Abstain |\n|--------|-----|----|----|'
        for user in self.users:
            if user in self.yes:
                yes = '✔'
            else:
                yes = '   '
            if user in self.no:
                no = '✔'
            else:
                no = '  '
            if user in self.abstain:
                abstain = '✔'
            else:
                abstain = '  '

            user_label = '[%s](https://github.com/%s)' % (user, user)
            row = "| %s | %s | %s | %s |" % (user_label, yes, no, abstain)
            table = "%s\n%s" % (table, row)
        return table

    def addLabels(self, labels):
        existing = self.getLabelList()
        issue = self.getIssue()
        for label in labels:
            if label not in existing:
                issue.add_labels(label)

    def removeLabels(self, labels):
        existing = self.getLabelList()
        issue = self.getIssue()
        for label in labels:
            if label in existing:
                issue.remove_label(label)

    def addComment(self, comment_string):
        return self.getIssue().create_comment(comment_string)

    def getLabelList(self):
        if not self.labels:
            issue = self.getIssue()
            self.labels = [item.name for item in issue.labels]
        return self.labels

    def isBlocked(self):
        labels = [item.lower() for item in self.getLabelList()]
        if 'wip' in labels:
            return True
        if 'dontmerge' in labels:
            return True
        return False


class Consensus:
    def __init__(self, rules):
        self.rules = rules

    def validate(self, pr):
        if pr.isBlocked():
            return False
        if not self.isAllowed(pr):
            return False
        if not self.isMergeable(pr):
            return False
        if not self.hasQuorum(pr):
            return False
        if not self.hasVotes(pr):
            return False
        if not self.hasAged(pr):
            return False
        return True

    def isAllowed(self, pr):
        if pr.changesLicense():
            if 'locklicense' in self.rules and self.rules['locklicense']:
                return False
        if pr.changesConsensus():
            if 'lockconsensus' in self.rules and self.rules['lockconsensus']:
                return False
        return True

    def isMergeable(self, pr):
        if not pr.pr.mergeable:
            return False
        return True

    def hasQuorum(self, pr):
        if 'quorum' in self.rules:
            if len(pr.users) < self.rules['quorum']:
                return False
        return True

    def hasVotes(self, pr):
        if 'threshold' in self.rules:
            total = (len(pr.yes) + len(pr.no))
            if total <= 0:
                return False
            ratio = len(pr.yes) / total
            if ratio < self.rules['threshold']:
                return False
        return True

    def hasAged(self, pr):
        hours = pr.hoursSinceLastUpdate()
        if pr.changesLicense():
            if 'licensedelay' in self.rules and self.rules['licensedelay']:
                if hours < self.rules['licensedelay']:
                    return False
        if pr.changesConsensus():
            if 'consensusdelay' in self.rules and self.rules['consensusdelay']:
                if hours < self.rules['consensusdelay']:
                    return False
        if 'mergedelay' not in self.rules:
            return True
        if hours >= self.rules['mergedelay']:
            return True
        if 'delayoverride' in self.rules and self.rules['delayoverride']:
            if pr.changesConsensus() or pr.changesLicense():
                return False
            if 'mergedelaymin' in self.rules and self.rules['mergedelaymin']:
                if hours < self.rules['mergedelaymin']:
                    return False
            if len(pr.no) > 0:
                return False
            if len(pr.contributors_yes) >= self.rules['delayoverride']:
                return True
        return False
