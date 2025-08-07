import pandas as pd
import os
from pathlib import Path
from core.specs.spec_manager import SpecManager
from core.config import Paths
SPECS_PATH = Paths.SPECS_PATH

# Create a spec manager instance using path from config
spec_manager = SpecManager(Paths.SPECS_PATH)

def load_familiar_specs():
    return spec_manager.load_familiar_specs()

def load_process_list():
    return spec_manager.load_process_list()

def load_specs_for_process(process):
    return spec_manager.load_specs_for_process(process)

def load_issuers():
    return spec_manager.load_issuers()

def spec_exists(process, spec):
    return spec_manager.spec_exists(process, spec)

def add_spec_entry(process, spec, issuer="", notes=""):
    return spec_manager.add_spec_entry(process, spec, issuer, notes)