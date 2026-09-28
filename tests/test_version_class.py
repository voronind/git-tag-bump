from git_tag_bump import Version, VersionPart


def test_version():
    version = Version(1)
    assert str(version) == 'v1.0'

    new_version = version.bump(VersionPart.MAJOR)
    assert str(new_version) == 'v2.0'
