#!/usr/bin/env python
import subprocess
from dataclasses import dataclass
from enum import Enum

import typer
from rich import print as rich_print
from typer._click import ClickException


class VersionPart(Enum):
    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'


@dataclass(frozen=True, slots=True)
class Version:
    major: int = 0
    minor: int = 0
    patch: int = 0
    prefix: str = 'v'

    def __str__(self):

        return f'{self.prefix}{self.major}.{self.minor}' + (f'.{self.patch}' if self.patch else '')

    def bump(self, part: VersionPart):
        match part:
            case VersionPart.MAJOR:
                return Version(self.major + 1, 0, 0, prefix=self.prefix)
            case VersionPart.MINOR:
                return Version(self.major, self.minor + 1, 0, prefix=self.prefix)
            case VersionPart.PATCH:
                return Version(self.major, self.minor, self.patch + 1, prefix=self.prefix)
        raise ValueError(f'Incorrect version part: {part}')


GIT_PATH = '/usr/bin/git'


def git(args: list[str]):
    return subprocess.check_call([GIT_PATH, args])


def git_output(args: list[str], stderr=None):
    return subprocess.check_output([GIT_PATH, *args], text=True, stderr=stderr).rstrip()


def git_repo_is_in_dirty_state():
    git_status_output = git_output(['status', '--porcelain'])
    return any(
        not line.startswith('?? ')
        for line in git_status_output.splitlines()
    )


def git_tag_version() -> Version:
    last_call_error = None
    for prefix in ['v', '']:
        try:
            describe_output = git_output(
                ['describe', '--long', '--match', f'{prefix}[0-9]*.[0-9]*'],
                stderr=subprocess.PIPE,
            )
            break
        except subprocess.CalledProcessError as error:
            last_call_error = error
            continue
    else:
        raise ClickException(f'$ {" ".join(last_call_error.cmd)}\n{last_call_error.stderr.rstrip()}')

    describe_output_version = describe_output[len(prefix):]
    import re  # ruff: ignore[import-outside-top-level]

    result = re.match(
        r"""
        (?P<version>
            (?P<major>\d+)
            \.(?P<minor>\d+)
            (?:\.(?P<patch>\d+))?
        )
        -(?P<commit_number>\d+)
        -g[\da-f]+$""",
        describe_output_version,
        re.VERBOSE,
    )
    if not result:
        raise ClickException(f'Can not parse `git describe` output: {describe_output_version}')

    group_dict = result.groupdict()

    if group_dict.get('commit_number') == '0':
        tag = prefix + group_dict['version']
        raise ClickException(f'Commit has tag already: {tag}')

    major = int(group_dict['major'])
    minor = int(group_dict['minor'])
    patch = int(group_dict.get('patch') or 0)

    return Version(major, minor, patch, prefix=prefix)


def git_tag_new_version(version: Version):
    git(['tag', '--annotate', '--message', 'Version', str(version)])


def git_push_tag(tag):
    branch = git_output(['rev-parse', '--abbrev-ref', 'HEAD'])
    try:
        remote = git_output(['config', f'branch.{branch}.remote'])
    except subprocess.CalledProcessError as error:
        raise ClickException(f'Git branch `{branch}` has no remote') from error

    git(['push', remote, tag])
    rich_print(f'New tag was pushed to `{remote}`')


app = typer.Typer()


@app.command()
def bump(
    # ruff: ignore[function-call-in-default-argument]
    part: VersionPart = typer.Argument(VersionPart.MINOR),
    push: bool = typer.Option(False, '--push', help='Push tag to remote repository.'),
    dry_run: bool = typer.Option(False),
):
    if git_repo_is_in_dirty_state():
        raise ClickException('Git repository is in dirty state')

    version = git_tag_version()
    new_version = version.bump(part)
    new_tag = str(new_version)

    print(new_tag)  # ruff: ignore[print]
    if dry_run:
        print('Dry run')  # ruff: ignore[print]
        return

    git_tag_new_version(version)
    if push:
        git_push_tag()


if __name__ == '__main__':
    app()
