from dataclasses import dataclass
import re

@dataclass
class Classification:
    transaction_number: int  # 1-indexed
    classification: str      # S, A, or B
    percentage: int | None   # Classifier's percentage (None = 50%)

@dataclass
class ParseResult:
    classifications: list[Classification]
    errors: list[str]  # Invalid lines

def parse_line(line: str) -> Classification | None:
    line = line.strip()
    if not line:
        return None
        
    # Regex breakdown:
    # ^(\d+)      : Start with digits (group 1)
    # ([SABsab])  : Classification char (group 2)
    # (\d+)?$     : Optional percentage digits at end (group 3)
    match = re.match(r"^(\d+)([SABsab])(\d+)?$", line)
    if not match:
        return None
        
    number_str, class_char, percent_str = match.groups()
    
    number = int(number_str)
    classification = class_char.upper()
    percentage = int(percent_str) if percent_str else None
    
    return Classification(
        transaction_number=number,
        classification=classification,
        percentage=percentage
    )

def parse_reply(message: str) -> ParseResult:
    classifications = []
    errors = []
    
    # Split on newlines
    lines = message.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        result = parse_line(line)
        if result:
            classifications.append(result)
        else:
            errors.append(line)
            
    return ParseResult(classifications=classifications, errors=errors)

def format_error_response(errors: list[str]) -> str:
    if not errors:
        return ""
    return f"Could not parse: {', '.join(errors)}. Format: #S, #A, or #S70"

def format_invalid_transaction_response(number: int, max_number: int) -> str:
    return f"Transaction #{number} not found. Please reply with a number between 1 and {max_number}."
