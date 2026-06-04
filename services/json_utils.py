import json
import logging

logger = logging.getLogger("json_utils")

def parse_json_robust(text: str) -> dict | list:
    """
    Robustly parses JSON from LLM response text, ignoring markdown wrap,
    extra trailing characters, double braces, or conversational text.
    """
    text = text.strip()
    
    # 1. Strip markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
        
    if text.endswith("```"):
        text = text[:-3]
        
    text = text.strip()
    
    # 2. Try standard json.loads
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # 3. Brace balancing to find the exact boundaries of the outer JSON object or list
    first_obj = text.find('{')
    first_list = text.find('[')
    
    # Determine the starting character and closing character
    if first_obj != -1 and (first_list == -1 or first_obj < first_list):
        start_char = '{'
        end_char = '}'
        start_idx = first_obj
    elif first_list != -1:
        start_char = '['
        end_char = ']'
        start_idx = first_list
    else:
        raise ValueError("No JSON object ({) or list ([) found in response text")
        
    count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == start_char:
                count += 1
            elif char == end_char:
                count -= 1
                if count == 0:
                    # Found the matching closing character!
                    json_candidate = text[start_idx:i+1]
                    try:
                        return json.loads(json_candidate)
                    except json.JSONDecodeError as err:
                        logger.warning(f"Extracted balanced segment failed to parse: {err}")
                        
    # 4. Fallback: incremental slicing from the end
    # Try parsing prefixes of the string, useful if there's trailing garbage
    for i in range(len(text), start_idx, -1):
        try:
            return json.loads(text[start_idx:i])
        except json.JSONDecodeError:
            continue
            
    # If all fails, raise original decode error on the stripped text
    return json.loads(text)
