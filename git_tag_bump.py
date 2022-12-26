import subprocess
from enum import Enum

from click.exceptions import ClickException
import typer


class VersionPart(Enum):
    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'


def bump(
    part: VersionPart = typer.Argument(VersionPart.MINOR.value),
    push: bool = typer.Option(False, '--push', help='Push tag to remote repository.'),
):
    git_status_output = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
    for line in git_status_output.splitlines():
        if not line.startswith('?? '):
            raise ClickException('Git repository is in dirty state')

    last_call_error = None
    for prefix in ['v', '']:
        try:
            describe_output = subprocess.check_output(
                ['git', 'describe', '--long', '--match', f'{prefix}[0-9]*.[0-9]*'],
                stderr=subprocess.PIPE,
                text=True,
            ).rstrip()
            break
        except subprocess.CalledProcessError as error:
            last_call_error = error
            continue
    else:
        raise ClickException(f'$ {" ".join(last_call_error.cmd)}\n{last_call_error.stderr.rstrip()}')

    describe_output = describe_output[len(prefix):]
    import re   # pylint: disable=import-outside-toplevel
    result = re.match(
        r"""
        (?P<version>
            (?P<major>\d+)
            \.(?P<minor>\d+)
            (?:\.(?P<patch>\d+))?
        )
        -(?P<commit_number>\d+)
        -g[\da-f]+$""",
        describe_output,
        re.VERBOSE,
    )
    if not result:
        raise ClickException(f'Can not parse `git describe` output: {describe_output}')

    group_dict = result.groupdict()

    if group_dict.get('commit_number') == '0':
        tag = prefix + group_dict['version']
        raise ClickException(f'Commit has tag already: {tag}')

    major = int(group_dict['major'])
    minor = int(group_dict['minor'])
    patch = int(group_dict.get('patch') or 0)

    if part == VersionPart.MAJOR:
        major += 1
        minor = 0
        patch = 0
    elif part == VersionPart.MINOR:
        minor += 1
        patch = 0
    elif part == VersionPart.PATCH:
        patch += 1

    new_tag = f'{prefix}{major}.{minor}' + (f'.{patch}' if patch else '')
    subprocess.check_call(['git', 'tag', '--annotate', '--message', 'Version', new_tag])
    print(new_tag)

    if push:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).rstrip()
        try:
            remote = subprocess.check_output(['git', 'config', f'branch.{branch}.remote'], text=True).rstrip()
        except subprocess.CalledProcessError as error:
            raise ClickException(f'Git branch `{branch}` has no remote') from error

        subprocess.check_call(['git', 'push', remote, new_tag])


def main():
    typer.run(bump)


if __name__ == '__main__':
    main()
