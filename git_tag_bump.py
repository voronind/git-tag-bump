#!/usr/bin/env python
import subprocess
from enum import Enum

import typer
from dunamai import Version
from rich import print as rich_print
from typer._click import ClickException


class VersionPart(Enum):
    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'


def bump_version(version: Version, part: VersionPart) -> str:
    parts = [int(base_part) for base_part in version.base.split('.')]
    # Fill list till 3 elements
    parts += [0] * (3 - len(parts))
    match part:
        case VersionPart.MAJOR:
            version_str = f'{parts[0] + 1}.0'
        case VersionPart.MINOR:
            version_str = f'{parts[0]}.{parts[1] + 1}'
        case VersionPart.PATCH:
            version_str = f'{parts[0]}.{parts[1]}.{parts[2] + 1}'
        case _:
            raise ValueError(f'Unknown version part value: {part}')

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
    part: VersionPart = typer.Argument(VersionPart.MINOR),
    push: bool = typer.Option(False, '--push', '-p', help='Push tag to remote repository.'),
):
    version = Version.from_git(ignore_untracked=True)

    if version.dirty:
        raise ClickException('Git repository is in dirty state')

    if version.distance == 0:
        raise ClickException(f'Commit has version tag already. Defined version: {version}')

    new_tag = bump_version(version, part)

    git_tag_new_version(new_tag)
    rich_print(f'[green]Added tag:[/green] [bold white]{new_tag}[/bold white]')

    if push:
        branch = git_output(['rev-parse', '--abbrev-ref', 'HEAD'])
        try:
            remote = git_output(['config', f'branch.{branch}.remote'])
        except subprocess.CalledProcessError as error:
            raise ClickException(f'Git branch `{branch}` has no remote') from error

        git(['push', remote, new_tag])
        rich_print(f'New tag was pushed to `{remote}`')


if __name__ == '__main__':
    app()
