"""
Utilities for converting and saving audience definitions.
"""
import json
import os


def convert_audiences_to_json(audiences: list) -> dict:
    """
    Convert audience definitions to JSON format.
    
    Args:
        audiences: List of audience dictionaries with groups and conditions
    
    Returns:
        Dictionary in the format expected by process_data
    """
    audience_defs = {}
    for aud in audiences:
        if len(aud["groups"]) == 1:
            # Single group - just use its conditions
            group = aud["groups"][0]
            if len(group["conditions"]) == 1:
                # Single condition
                cond = group["conditions"][0]
                audience_defs[aud["name"]] = {cond["column"]: cond["values"]}
            else:
                # Multiple conditions
                audience_defs[aud["name"]] = {
                    group["logic"]: [
                        {cond["column"]: cond["values"]}
                        for cond in group["conditions"]
                    ]
                }
        else:
            # Multiple groups
            audience_defs[aud["name"]] = {
                aud["top_logic"]: [
                    {
                        group["logic"]: [
                            {cond["column"]: cond["values"]}
                            for cond in group["conditions"]
                        ]
                    }
                    for group in aud["groups"]
                ]
            }
    return audience_defs


def save_audience_definitions(audiences: list, filepath: str = "src/audience_segments.json"):
    """
    Save audience definitions to JSON file.
    
    Args:
        audiences: List of audience dictionaries
        filepath: Path to save the JSON file
    """
    audience_defs = convert_audiences_to_json(audiences)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save to JSON file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audience_defs, f, indent=2)
