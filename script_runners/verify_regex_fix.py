import re
import json

def test_regex(text):
    # Logic extracted from the updated app.py
    json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    potential_json = None
    
    if json_block_match:
        potential_json = json_block_match.group(1)
    else:
        # Greedily match until the last brace to handle nested braces in data
        json_match = re.search(r'(\{.*"visualization_type".*\})', text, re.DOTALL)
        if json_match:
            potential_json = json_match.group(1)

    if potential_json:
        print(f"Match found: {potential_json}")
        try:
            parsed = json.loads(potential_json.strip())
            print("Successfully parsed as JSON")
            return parsed
        except Exception as e:
            print(f"Failed to parse: {e}")
    else:
        print("No match found")
    return None

print("Test 1: Simple JSON")
test_regex('Here is your flowchart: {"visualization_type": "flowchart", "data": "graph TD; A-->B"}')

print("\nTest 2: JSON with Mermaid braces (Decision node)")
test_regex('Here is your flowchart: {"visualization_type": "flowchart", "data": "graph TD; A{Decision} --> B"}')

print("\nTest 3: Markdown JSON block")
test_regex('Check this out:\n```json\n{"visualization_type": "flowchart", "data": "graph TD; A{Nested} --> B"}\n```')

print("\nTest 4: Multi-line JSON")
test_regex('Here is your flowchart:\n{\n  "visualization_type": "flowchart",\n  "data": "graph TD; A-->B"\n}')
