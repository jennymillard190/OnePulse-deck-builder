#!/usr/bin/env python3
"""
Debug script to check what file the app is actually reading from.
"""

import os
import json

def debug_app_file_check():
    """Check what file the app is actually reading from"""
    print("=== Debug: App File Check ===")
    
    # Get project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check the app's audience_segments.json
    app_json_path = os.path.join(project_root, "src", "audience_segments.json")
    if os.path.exists(app_json_path):
        print(f"✓ Found app's audience_segments.json: {app_json_path}")
        print(f"File size: {os.path.getsize(app_json_path)} bytes")
        print(f"Last modified: {os.path.getmtime(app_json_path)}")
        
        with open(app_json_path, 'r') as f:
            content = f.read()
            print(f"File content length: {len(content)} characters")
            print(f"First 200 characters: {content[:200]}")
            
            # Try to parse as JSON
            try:
                app_json = json.loads(content)
                print(f"✓ Valid JSON")
                print(f"Has __groups__: {'__groups__' in app_json}")
                if '__groups__' in app_json:
                    print(f"Groups: {app_json['__groups__']}")
                print(f"Keys: {list(app_json.keys())}")
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON: {e}")
    else:
        print(f"✗ App's audience_segments.json not found: {app_json_path}")
    
    # Check if there are other audience_segments.json files
    print(f"\n=== Searching for other audience_segments.json files ===")
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'audience_segments.json':
                full_path = os.path.join(root, file)
                print(f"Found: {full_path}")
                print(f"  Size: {os.path.getsize(full_path)} bytes")
                print(f"  Modified: {os.path.getmtime(full_path)}")
                
                with open(full_path, 'r') as f:
                    content = f.read()
                    print(f"  Content length: {len(content)} characters")
                    print(f"  First 100 chars: {content[:100]}")
    
    # Check the exports directory
    print(f"\n=== Checking exports directory ===")
    exports_dir = os.path.join(project_root, "exports")
    if os.path.exists(exports_dir):
        files = os.listdir(exports_dir)
        print(f"Files in exports: {files}")
        for file in files:
            if file.endswith('.pptx'):
                full_path = os.path.join(exports_dir, file)
                print(f"  {file}: {os.path.getsize(full_path)} bytes, modified {os.path.getmtime(full_path)}")
    else:
        print(f"Exports directory not found: {exports_dir}")

if __name__ == "__main__":
    debug_app_file_check() 