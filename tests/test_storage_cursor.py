from lib.storage import get_cursor, save_cursor

def test_get_cursor_missing(dynamodb_mock, env_setup):
    # Should return None if file doesn't exist
    assert get_cursor() is None

def test_save_and_get_cursor(dynamodb_mock, env_setup):
    cursor_val = "access-cursor-12345"
    
    save_cursor(cursor_val)
    
    # Verify we can read it back
    loaded = get_cursor()
    assert loaded == cursor_val

def test_save_cursor_overwrite(dynamodb_mock, env_setup):
    save_cursor("old")
    save_cursor("new")
    assert get_cursor() == "new"
