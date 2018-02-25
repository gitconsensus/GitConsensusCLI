import click
import github3
import os
import random
import requests
from gitconsensus import config
from gitconsensus.repository import Repository
import string

@click.group()
@click.pass_context
def cli(ctx):
    if ctx.parent:
        print(ctx.parent.get_help())


@cli.command(short_help="Obtain an authorization token")
def auth():
    username = click.prompt('Username')
    password = click.prompt('Password', hide_input=True)
    def twofacallback(*args):
        return click.prompt('2fa Code')

    hostid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    note = 'gitconsensus - %s' % (hostid,)
    note_url = 'https://github.com/tedivm/GitConsensus'
    scopes = ['repo']
    auth = github3.authorize(username, password, scopes, note, note_url, two_factor_callback=twofacallback)

    with open("%s/%s" % (os.getcwd(), '/.gitcredentials'), 'w') as fd:
        fd.write(str(auth.id) + '\n')
        fd.write(auth.token + '\n')


@cli.command(short_help="Create a new gitconsensus configuration")
@click.argument('template', required=False)
def init(template):
    if not template:
        template = 'recommended'

    if os.path.isfile('.gitconsensus.yaml'):
        click.echo('.gitconsensus.yaml already exists.')
        exit(-1)

    baseurl = 'https://raw.githubusercontent.com/gitconsensus/gitconsensus_examples/master/examples/%s/.gitconsensus.yaml'
    url = baseurl % (template)
    response = requests.get(url)

    if not response.ok:
        click.echo('Unable to find template "%s"' % (template))
        exit(-1)

    with open('.gitconsensus.yaml', 'wb') as f:
        f.write(response.content)


@cli.command(short_help="List open pull requests and their status")
@click.argument('username')
@click.argument('repository_name')
def list(username, repository_name):
    repo = get_repository(username, repository_name)
    requests = repo.getPullRequests()
    for request in requests:
        click.echo("PR#%s: %s" % (request.number, request.validate()))


@cli.command(short_help="Display detailed information about a specific pull request")
@click.argument('username')
@click.argument('repository_name')
@click.argument('pull_request')
def info(username, repository_name, pull_request):
    repo = get_repository(username, repository_name)
    request = repo.getPullRequest(pull_request)
    click.echo("PR#%s: %s" % (request.number, request.pr.title))
    consensus = repo.getConsensus()
    click.echo("Mergeable:    %s" % (consensus.isMergeable(request),))
    click.echo("Is Blocked:   %s" % (request.isBlocked(),))
    click.echo("Is Allowed:   %s" % (consensus.isAllowed(request),))
    click.echo("Has Quorum:   %s" % (consensus.hasQuorum(request),))
    click.echo("Has Votes:    %s" % (consensus.hasVotes(request),))
    click.echo("Has Aged:     %s" % (consensus.hasAged(request),))
    click.echo("Should Close: %s" % (request.shouldClose(),))
    click.echo("Last Update:  %s" % (request.hoursSinceLastUpdate(),))


@cli.command(short_help="Forced a specific pull request to be merged")
@click.argument('username')
@click.argument('repository_name')
@click.argument('pull_request')
def forcemerge(username, repository_name, pull_request):
    repo = get_repository(username, repository_name)
    request = repo.getPullRequest(pull_request)
    click.echo("PR#%s: %s" % (request.number, request.pr.title))
    request.vote_merge()


@cli.command(short_help="Forced a specific pull request to be closed")
@click.argument('username')
@click.argument('repository_name')
@click.argument('pull_request')
def forceclose(username, repository_name, pull_request):
    repo = get_repository(username, repository_name)
    request = repo.getPullRequest(pull_request)
    click.echo("PR#%s: %s" % (request.number, request.pr.title))
    request.close()


@cli.command(short_help="Merge open pull requests that validate")
@click.argument('username')
@click.argument('repository_name')
def merge(username, repository_name):
    repo = get_repository(username, repository_name)
    requests = repo.getPullRequests()
    for request in requests:
        if request.validate():
            click.echo("Merging PR#%s" % (request.number,))
            request.vote_merge()
        else:
            request.addInfoLabels()


@cli.command(short_help="Close older unmerged opened pull requests")
@click.argument('username')
@click.argument('repository_name')
def close(username, repository_name):
    repo = get_repository(username, repository_name)
    requests = repo.getPullRequests()
    for request in requests:
        if request.isBlocked():
            continue
        if request.shouldClose():
            click.echo("Closing PR#%s" % (request.number,))
            request.addInfoLabels()
            request.close()


@cli.command(short_help="Add labels and set colors")
@click.argument('username')
@click.argument('repository_name')
@click.option('--color-negative', default='#ee0701')
@click.option('--color-positive', default='#0052cc')
@click.option('--color-notice', default='#fbf904')
def createlabels(username, repository_name, color_negative, color_positive, color_notice):
    repo = get_repository(username, repository_name)
    repo.setLabelColor('License Change', color_notice)
    repo.setLabelColor('Consensus Change', color_notice)
    repo.setLabelColor('Has Quorum', color_positive)
    repo.setLabelColor('Needs Votes', color_negative)
    repo.setLabelColor('Passing', color_positive)
    repo.setLabelColor('Failing', color_negative)
    repo.setLabelColor('gc-merged', color_positive)
    repo.setLabelColor('gc-closed', color_negative)


def get_repository(username, repository_name):
    credentials = config.getGitToken()
    client = github3.login(token=credentials['token'])
    return Repository(username, repository_name, client)


if __name__ == '__main__':
    cli()
