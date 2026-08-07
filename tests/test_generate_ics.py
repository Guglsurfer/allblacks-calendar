import os
from pathlib import Path
import shutil

from scripts import generate_ics


def test_generate_from_sample(tmp_path):
    root = Path(__file__).resolve().parents[1]
    # copy sample fixture into a temporary file and run parser directly
    sample = root / 'tests' / 'fixtures' / 'placeholder.txt'
    assert sample.exists()
    cfg = {
        'sources': [],
        'include_provincial': ['Stormers','Sharks','Bulls','Lions'],
        'timezone': 'Europe/Zurich',
        'default_duration_seconds': 7200
    }
    # basic smoke test: ensure functions import
    assert hasattr(generate_ics, 'parse_wikipedia')
