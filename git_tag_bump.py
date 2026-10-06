#!/usr/bin/env python
import subprocess
from enum import Enum

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
):
    version = Version.from_git(ignore_untracked=True)

    if version.dirty:
        raise ClickException('Git repository is in dirty state')

    if version.distance == 0:
        raise ClickException(f'Commit has version tag already. Defined version: {version}')

    new_tag = bump_version(version, version_part)

    git_tag_new_version(new_tag)
    rich_print(f'[green]Created tag:[/green] [bold white]{new_tag}[/bold white]')


if __name__ == '__main__':
    app()
