from lib.parser import parse_reply, Classification

def test_parse_simple_shared():
    result = parse_reply("1S")
    assert len(result.classifications) == 1
    c = result.classifications[0]
    assert c.transaction_number == 1
    assert c.classification == "S"
    assert c.percentage is None
    assert len(result.errors) == 0

def test_parse_simple_user():
    result = parse_reply("2A")
    assert len(result.classifications) == 1
    c = result.classifications[0]
    assert c.transaction_number == 2
    assert c.classification == "A"

def test_parse_shared_with_percentage():
    result = parse_reply("3S70")
    assert len(result.classifications) == 1
    c = result.classifications[0]
    assert c.transaction_number == 3
    assert c.classification == "S"
    assert c.percentage == 70

def test_case_insensitive():
    result = parse_reply("1s")
    assert result.classifications[0].classification == "S"
    
    result = parse_reply("2b")
    assert result.classifications[0].classification == "B"

def test_multiple_lines():
    reply = "1S\n2A\n3S70"
    result = parse_reply(reply)
    assert len(result.classifications) == 3
    assert result.classifications[0].transaction_number == 1
    assert result.classifications[1].transaction_number == 2
    assert result.classifications[2].transaction_number == 3

def test_invalid_format():
    result = parse_reply("invalid")
    assert len(result.classifications) == 0
    assert len(result.errors) == 1
    assert "invalid" in result.errors[0]

def test_mixed_valid_invalid():
    reply = "1S\ninvalid\n2A"
    result = parse_reply(reply)
    assert len(result.classifications) == 2
    assert len(result.errors) == 1

def test_ignore_whitespace():
    result = parse_reply("  1 S 70  ")
    # Our spec says regex per line `^(\d+)([SABsab])(\d+)?$`
    # It also says "trim whitespace". 
    # If "1 S 70" has internal spaces, regex might fail depending on implementation.
    # Let's stick to the spec: "trim whitespace" usually means leading/trailing.
    # If internal spaces are allowed, we need to adjust regex.
    # Spec says "Reply format: #S #A #B". Usually users might type "1 S".
    # Let's support internal spaces if possible, or strictly follow "trim whitespace" (strip()).
    # Assuming strict per spec regex: `^(\d+)([SABsab])(\d+)?$` implies NO internal spaces.
    # So "1 S 70" would be invalid. "  1S70  " -> "1S70" valid.
    
    # Test strict adherence first (strip only)
    result = parse_reply("  1S70  ") 
    assert len(result.classifications) == 1
    assert result.classifications[0].percentage == 70

def test_skip_blank_lines():
    reply = "1S\n\n2A"
    result = parse_reply(reply)
    assert len(result.classifications) == 2
