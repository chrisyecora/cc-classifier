from config import get_config


def test_get_config_reads_env_vars(env_setup):
    config = get_config()
    assert config.environment == "test"
    assert config.table_name == "test-table"
    assert config.user_a_name == "TestAlex"


def test_get_config_defaults(monkeypatch):
    # Unset specific env var to test default
    monkeypatch.delenv("USER_A_NAME", raising=False)

    # We need to manually trigger reset because env_setup might have run before
    from config import reset_config

    reset_config()

    config = get_config()
    assert config.user_a_name == "Alex"  # Default value
