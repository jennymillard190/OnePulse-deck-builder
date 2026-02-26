"""
OnePulse Chart Generation Package

This package provides functionality to generate PowerPoint charts from OnePulse survey data.
"""

from . import config
from . import data_loader
from . import data_processor
from . import ppt_generator
from . import main

# Expose key functions
from .main import process_data
from .ppt_generator import generate_presentation 