#!/usr/bin/env python3
import os
import sys
import subprocess
from typing import Dict
from pptx.enum.dml import MSO_THEME_COLOR
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simplified format to just show the message
)

# Set ppt_generator logger to WARNING to reduce PowerPoint-related output
logging.getLogger('src.ppt_generator').setLevel(logging.WARNING)

# Auto-install missing dependencies
required = ['pandas', 'python-pptx']
missing = []
for pkg in required:
    mod = 'pptx' if pkg == 'python-pptx' else pkg
    try:
        __import__(mod)
    except ImportError:
        missing.append(pkg)
if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])

# Base directory
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directory and file paths
EXPORTS_DIR: str = os.path.join(BASE_DIR, 'exports')
TEMPLATE_PATH: str = os.path.join(os.path.dirname(__file__), 'templates', 'template clean.pptx')

def get_output_pptx_path(input_filename: str, export_type: str = "full") -> str:
    """
    Generate the output PPTX filename based on the input filename and export type.
    
    Args:
        input_filename: Name of the input file (e.g., 'data.xlsx' or 'data.csv')
        export_type: Type of export ('full' or 'condensed')
    
    Returns:
        Relative path to the output PPTX file in exports directory
    """
    # Get the base name without extension
    base_name = os.path.splitext(os.path.basename(input_filename))[0]
    # Create output filename with export type and .pptx extension
    output_filename = f"{base_name}_{export_type}.pptx"
    # Return relative path in the exports directory
    return os.path.join("exports", output_filename)

# Default output path (will be overridden by get_output_pptx_path)
DEFAULT_OUTPUT_PPTX: str = os.path.join(BASE_DIR, 'OnePulse_Summary_with_cover_templates.pptx')

# Chart dimensions
CHART_WIDTH: float = 11.42  # 29cm
CHART_HEIGHT: float = 4.92  # 12.5cm
FOOTER_OFFSET: float = 0.5

# Theme color management
def reset_theme_colors():
    """Reset the theme color lookup and index to their initial values."""
    global theme_lookup, next_accent_index
    theme_lookup = {'Total': MSO_THEME_COLOR.ACCENT_1}
    next_accent_index = 2

# Initialize theme colors
reset_theme_colors()

# Theme color mapping
theme_lookup: Dict[str, MSO_THEME_COLOR] = {'Total': MSO_THEME_COLOR.ACCENT_1}
next_accent_index: int = 2  # start assigning from ACCENT_2 

# Chart settings
CHART_WIDTH = 9  # inches
CHART_HEIGHT = 4.5  # inches
CHART_LEFT = 0.5  # inches from left
CHART_TOP = 1  # inches from top

# Font settings
TITLE_FONT = 'Calibri'
TITLE_SIZE = 12  # points
TITLE_COLOR = (0, 0, 0)  # RGB

# Footer settings
FOOTER_OFFSET = 0.5  # inches from bottom
FOOTER_FONT = 'Calibri'
FOOTER_SIZE = 10  # points
FOOTER_COLOR = (0, 0, 0)  # RGB 