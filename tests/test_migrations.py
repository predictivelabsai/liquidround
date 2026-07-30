from scripts.validate_migrations import validate


def test_migration_manifest_is_valid():
    assert validate() == []
