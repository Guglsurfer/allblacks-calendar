# All Blacks calendar generator
# Generates docs/allblacks.ics from public sources (scraping) according to data/config.yml

import os
import sys
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from icalendar import Calendar, Event
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
CONFIG_PATH = os.path.join(ROOT, 'data', 'config.yml')
OUTPUT_PATH = os.path.join(ROOT, 'docs', 'allblacks.ics')


def load_config(path=CONFIG_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def fetch_url(url, timeout=15):
    logging.info(f'Fetching {url}')
    r = requests.get(url, timeout=timeout, headers={'User-Agent':'allblacks-calendar-bot/1.0'})
    r.raise_for_status()
    return r.text


def parse_wikipedia(html, config):
    # Tries to extract fixture rows from a Wikipedia-style table
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table', {'class':'wikitable'})
    events = []
    for table in tables:
        # Find header columns
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        rows = table.find_all('tr')
        for tr in rows[1:]:
            cols = [td.get_text(' ', strip=True) for td in tr.find_all(['td', 'th'])]
            if not cols:
                continue
            rowtext = ' | '.join(cols)
            # Heuristic: look for a date and an opponent name
            # Try to find a date-like string in first columns
            date_str = None
            opponent = None
            venue = None
            for c in cols:
                # naive date detect (YYYY or Month)
                if any(month in c for month in ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']) or any(digit for digit in c if digit.isdigit()):
                    date_str = c
                    break
            # opponent detection: match known opponent keywords from config
            for team in config.get('include_provincial', []) + config.get('extra_opponents', []):
                if team.lower() in rowtext.lower():
                    opponent = team
                    break
            # fallback: try to find capitalized team words in cols
            if not opponent:
                # naive: take second column if exists
                if len(cols) >= 2:
                    opponent = cols[1]
            if not date_str:
                continue
            try:
                # try parsing date with several formats
                dt = None
                for fmt in ['%d %B %Y', '%d %b %Y', '%Y', '%d %B %Y %H:%M', '%d %b %Y %H:%M', '%d %B %Y %H:%M %Z']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except Exception:
                        continue
                if dt is None:
                    # as a last resort, try dateutil if available
                    from dateutil import parser
                    dt = parser.parse(date_str, fuzzy=True)
                events.append({'start': dt, 'opponent': opponent, 'venue': venue, 'source':'wikipedia'})
            except Exception as e:
                logging.debug(f'Could not parse date "{date_str}": {e}')
                continue
    return events


def parse_generic_tables(html, config):
    # Generic table scanner to catch simple lists
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for tr in rows:
            cols = [td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])]
            if len(cols) < 2:
                continue
            rowtext = ' | '.join(cols)
            # simple heuristics
            if any(team.lower() in rowtext.lower() for team in (["All Blacks"] + config.get('include_provincial', []))):
                # try to extract date
                date_candidates = [c for c in cols if any(d.isdigit() for d in c)]
                if not date_candidates:
                    continue
                date_str = date_candidates[0]
                try:
                    from dateutil import parser
                    dt = parser.parse(date_str, fuzzy=True)
                    opponent = None
                    for team in config.get('include_provincial', []) + config.get('extra_opponents', []):
                        if team.lower() in rowtext.lower():
                            opponent = team
                            break
                    events.append({'start': dt, 'opponent': opponent or cols[-1], 'venue': None, 'source':'generic'})
                except Exception:
                    continue
    return events


def find_events_from_sources(config):
    sources = config.get('sources', [])
    for src in sources:
        try:
            html = fetch_url(src)
            # try parsers in order
            events = parse_wikipedia(html, config)
            if events:
                logging.info(f'Parsed {len(events)} events from {src} using wikipedia parser')
                return events, src
            events = parse_generic_tables(html, config)
            if events:
                logging.info(f'Parsed {len(events)} events from {src} using generic parser')
                return events, src
        except Exception as e:
            logging.warning(f'Failed to parse {src}: {e}')
            continue
    return [], None


def filter_events(events, config):
    filtered = []
    for ev in events:
        # filter to All Blacks (national) matches and selected provincial opponents
        opponent = (ev.get('opponent') or '').lower()
        include_prov = [t.lower() for t in config.get('include_provincial', [])]
        if any(p in opponent for p in include_prov) or 'all black' in opponent or opponent.strip() == '':
            filtered.append(ev)
    return filtered


def build_ics(events, config, output_path=OUTPUT_PATH):
    tz = pytz.timezone(config.get('timezone', 'Europe/Zurich'))
    cal = Calendar()
    cal.add('prodid', '-//Guglsurfer/allblacks-calendar//')
    cal.add('version', '2.0')
    for ev in events:
        start = ev['start']
        if start.tzinfo is None:
            start = tz.localize(start)
        e = Event()
        summary = f"All Blacks vs {ev.get('opponent') or 'TBD'}"
        e.add('summary', summary)
        e.add('dtstart', start)
        # assume 2h duration if no end
        e.add('dtend', start + config.get('default_duration', 7200) * timedelta_seconds())
        if ev.get('venue'):
            e.add('location', ev['venue'])
        e.add('description', f"Source: {ev.get('source')}")
        cal.add_component(e)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(cal.to_ical())
    logging.info(f'Wrote {output_path} with {len(events)} events')


def timedelta_seconds(seconds=0):
    from datetime import timedelta
    return timedelta(seconds=seconds)


def main():
    config = load_config()
    events, src = find_events_from_sources(config)
    if not events:
        logging.error('No events found from any source')
        sys.exit(2)
    events = filter_events(events, config)
    if not events:
        logging.error('No events matched filters after parsing')
        sys.exit(3)
    build_ics(events, config)

if __name__ == '__main__':
    main()
