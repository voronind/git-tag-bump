#!/usr/bin/env python
import subprocess
from enum import Enum
from pathlib import Path

import typer
from dunamai import Version
from rich import print as rich_print
from typer._click import ClickException


class VersionPart(Enum):
    M = 'M'     # major
    m = 'm'     # minor
    p = 'p'     # patch


def bump_version(version: Version, bumped_part: VersionPart) -> str:
    parts = [int(base_part) for base_part in version.base.split('.')]
    # Fill list till 3 elements
    parts += [0] * (3 - len(parts))
    match bumped_part:
        case VersionPart.M:
            version_str = f'{parts[0] + 1}.0'
        case VersionPart.m:
            version_str = f'{parts[0]}.{parts[1] + 1}'
        case VersionPart.p:
            version_str = f'{parts[0]}.{parts[1]}.{parts[2] + 1}'
        case _:
            raise ValueError(f'Unknown version part: {bumped_part}')

    if version.epoch:
        version_str = f'{version.epoch}!{version_str}'

    return f'v{version_str}'


GIT_PATH = '/usr/bin/git'


def git(args: list[str]):
    return subprocess.check_call([GIT_PATH, *args])


def git_output(args: list[str], stderr=None):
    return subprocess.check_output([GIT_PATH, *args], text=True, stderr=stderr).rstrip()


def git_tag_new_version(tag):
    git(['tag', '--annotate', '--message', 'Version', tag])


def git_push_tag(tag):
    branch = git_output(['rev-parse', '--abbrev-ref', 'HEAD'])
    try:
        remote = git_output(['config', f'branch.{branch}.remote'])
    except subprocess.CalledProcessError as error:
        raise ClickException(f'Git branch `{branch}` has no remote') from error

    git(['push', remote, tag])
    rich_print(f'New tag was pushed to `{remote}`')


def uv_build():
    uv_build_command = ['uv', 'build', '--clear']
    rich_print(f'Run: {" ".join(uv_build_command)}')
    subprocess.check_call(uv_build_command)


app = typer.Typer()


@app.command()
def bump(
    # ruff: ignore[function-call-in-default-argument]
    version_part: VersionPart = typer.Argument(
        metavar='version-part',
        help='Version part to bump:'
             ' [bold green]M[/bold green]ajor,'
             ' [bold green]m[/bold green]inor'
             ' or [bold green]p[/bold green]atch',
    ),
    push: bool = typer.Option(False, '--push', '-p', help='Push tag to remote repository.'),
    build: bool = typer.Option(True, '--build/--no-build', '-b/-no-b', help='Run `uv build`'),
):
    version = Version.from_git(ignore_untracked=True)

    if version.dirty:
        raise ClickException('Git repository is in dirty state')

    if version.distance == 0:
        raise ClickException(f'Commit has version tag already. Defined version: {version}')

    new_tag = bump_version(version, version_part)

    git_tag_new_version(new_tag)
    rich_print(f'[green]Created tag:[/green] [bold white]{new_tag}[/bold white]')

    if push:
        git_push_tag(new_tag)

    if build and Path.isdir('dist'):
        uv_build()


if __name__ == '__main__':
    app()
