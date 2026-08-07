# All Blacks Calendar

This repository generates an automatically updated Apple-compatible calendar (ICS) for the New Zealand All Blacks (men), including tour matches vs provincial teams (Stormers, Sharks, Bulls, Lions).

Files created in this branch:
- docs/allblacks.ics — output calendar file (served by GitHub Pages)
- data/config.yml — list of public sources and filters (timezone, included provincial teams)
- scripts/generate_ics.py — generator script (scrapes public sources and writes an ICS)
- .github/workflows/update-calendar.yml — GitHub Action: tests, generation, publish to Pages

Subscribe: https://Guglsurfer.github.io/allblacks-calendar/allblacks.ics

Notes:
- You asked for automatic Pages configuration. The workflow tries to publish the docs/ folder using the official upload/deploy Pages actions; if the Pages deployment requires a manual approval in repo settings, follow the PR notes.
- CI runs pytest. Tests are lightweight and offline.
