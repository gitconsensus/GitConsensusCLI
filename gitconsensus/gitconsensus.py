import click
import github3
import os
import random
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


@cli.command(short_help="List open pull requests and their status")
@click.argument('username')
@click.argument('repository_name')
def list(username, repository_name):
    repo = Repository(username, repository_name)
    requests = repo.getPullRequests()
    for request in requests:
        click.echo("PR#%s: %s" % (request.number, request.validate()))


@cli.command(short_help="Display detailed information about a specific pull request")
@click.argument('username')
@click.argument('repository_name')
@click.argument('pull_request')
def info(username, repository_name, pull_request):
    repo = Repository(username, repository_name)
    request = repo.getPullRequest(pull_request)
    click.echo("PR#%s: %s" % (request.number, request.pr.title))
    consensus = repo.getConsensus()
    click.echo("Mergeable:  %s" % (consensus.isMergeable(request),))
    click.echo("Is Blocked: %s" % (request.isBlocked(),))
    click.echo("Has Quorum: %s" % (consensus.hasQuorum(request),))
    click.echo("Has Votes:  %s" % (consensus.hasVotes(request),))
    click.echo("Has Aged:   %s" % (consensus.hasAged(request),))


@cli.command(short_help="Forced a specific pull request to be merged")
@click.argument('username')
@click.argument('repository_name')
@click.argument('pull_request')
def forcemerge(username, repository_name, pull_request):
    repo = Repository(username, repository_name)
    request = repo.getPullRequest(pull_request)
    click.echo("PR#%s: %s" % (request.number, request.pr.title))
    request.vote_merge()


@cli.command(short_help="Forced a specific pull request to be closed")
@click.argument('username')
@click.argument('repository_name')
@click.argument('pull_request')
def forceclose(username, repository_name, pull_request):
    repo = Repository(username, repository_name)
    request = repo.getPullRequest(pull_request)
    click.echo("PR#%s: %s" % (request.number, request.pr.title))
    request.close()


@cli.command(short_help="Merge open pull requests that validate")
@click.argument('username')
@click.argument('repository_name')
def merge(username, repository_name):
    repo = Repository(username, repository_name)
    requests = repo.getPullRequests()
    for request in requests:
        if request.validate():
            click.echo("Merging PR#%s" % (request.number,))
            request.vote_merge()


@cli.command(short_help="Close older unmerged opened pull requests")
@click.argument('username')
@click.argument('repository_name')
def close(username, repository_name):
    repo = Repository(username, repository_name)
    requests = repo.getPullRequests()
    for request in requests:
        if request.isBlocked():
            continue
        if request.shouldClose():
            click.echo("Closing PR#%s" % (request.number,))
            request.close()

if __name__ == '__main__':
    cli()
