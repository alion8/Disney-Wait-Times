import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import time
import re
import sys
import os
import asyncio

# Fix encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class DisneylandComprehensiveScraper:
    """
    Comprehensive scraper for Disneyland data to predict wait times

    Data sources:
    1. Queue-Times.com: Historical ride patterns and real-time wait times
    2. TouringPlans.com: Ride durations and height requirements (pre-collected)
    3. ThemeParkIQ.com: Daily calendar (hours, events, parades, fireworks, shows, closures)

    Attribution: Powered by Queue-Times.com, TouringPlans.com & ThemeParkIQ.com
    """

    def __init__(self):
        self.park_id = 16  # Disneyland
        self.base_url = "https://queue-times.com"
        self.calendar_url = f"{self.base_url}/en-US/parks/{self.park_id}/calendar"
        self.api_url = f"{self.base_url}/parks/{self.park_id}/queue_times.json"

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.rides_cache = None

    def get_all_rides(self):
        """Get list of all rides with IDs and names from API"""
        if self.rides_cache:
            return self.rides_cache

        try:
            print("Fetching ride list from API...")
            response = self.session.get(self.api_url)
            response.raise_for_status()
            data = response.json()

            rides = []
            for land in data.get('lands', []):
                for ride in land.get('rides', []):
                    rides.append({
                        'id': ride['id'],
                        'name': ride['name'],
                        'land': land['name']
                    })

            self.rides_cache = rides
            print(f"Found {len(rides)} rides")
            return rides

        except Exception as e:
            print(f"Error fetching rides: {e}")
            return []

    def get_ride_historical_patterns(self, ride_id, ride_name):
        """
        Scrape individual ride page for historical patterns

        Returns dict with:
        - by_year: average wait times per year
        - by_day_of_week: average per day (Mon-Sun)
        - by_time_of_day: average per hour
        - by_month: average per month
        - special_events: impact of events
        """
        url = f"{self.base_url}/en-US/parks/{self.park_id}/rides/{ride_id}"

        try:
            print(f"  Fetching patterns for: {ride_name}")
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            patterns = {
                'ride_id': ride_id,
                'ride_name': ride_name,
                'url': url,
                'by_year': self._extract_table_data(soup, 'Year'),
                'by_day_of_week': self._extract_table_by_position(soup, 3),  # Table 3 = Day of week
                'by_time_of_day': self._extract_table_by_position(soup, 5),  # Table 5 = Hour
                'by_month': self._extract_table_data(soup, 'Month'),
                'special_events': self._extract_table_by_position(soup, 6)  # Table 6 = Events
            }

            return patterns

        except Exception as e:
            print(f"  Error fetching ride {ride_id}: {e}")
            return None

    def _extract_table_by_position(self, soup, table_index):
        """Extract data from a table by its position/index"""
        try:
            tables = soup.find_all('table')
            if table_index < len(tables):
                table = tables[table_index]
                data = {}
                rows = table.find_all('tr')[1:]  # Skip header row

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        key = cols[0].get_text().strip()
                        # Extract all numeric values from the row
                        values = {}
                        for i, col in enumerate(cols[1:], 1):
                            text = col.get_text().strip()
                            # Try to extract number
                            match = re.search(r'(\d+(?:\.\d+)?)', text)
                            if match:
                                values[f'avg' if i == 1 else 'max'] = float(match.group(1))

                        if values:
                            # For time data, use hour number as key
                            if key.isdigit():
                                hour = int(key)
                                data[f"{hour:02d}:00"] = values
                            else:
                                # For day names, etc
                                data[key] = values

                return data
        except:
            pass

        return {}

    def _extract_table_data(self, soup, header_keyword):
        """Extract data from tables with specific headers"""
        try:
            # Find all tables
            tables = soup.find_all('table')

            for table in tables:
                # Check if this table has the header we're looking for
                headers = table.find_all('th')
                header_text = ' '.join([h.get_text().strip() for h in headers])

                if header_keyword.lower() in header_text.lower():
                    data = {}
                    rows = table.find_all('tr')[1:]  # Skip header row

                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            key = cols[0].get_text().strip()
                            # Extract all numeric values from the row
                            values = {}
                            for i, col in enumerate(cols[1:], 1):
                                text = col.get_text().strip()
                                # Try to extract number
                                match = re.search(r'(\d+(?:\.\d+)?)', text)
                                if match:
                                    values[f'value_{i}'] = float(match.group(1))

                            if values:
                                # If only one value, simplify
                                if len(values) == 1:
                                    data[key] = values['value_1']
                                else:
                                    data[key] = values

                    return data
        except:
            pass

        return {}

    def get_calendar_date_data(self, date_str):
        """
        Fetch historical data for a specific date from calendar

        Args:
            date_str: Date in format 'YYYY-MM-DD'
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            url = f"{self.calendar_url}/{date_obj.year}/{date_obj.month:02d}/{date_obj.day:02d}"

            print(f"Fetching calendar data for {date_str}...")

            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract data from tables
            tables = soup.find_all('table')

            wait_times_avg = {}
            wait_times_max = {}
            uptime = {}

            for i, table in enumerate(tables):
                rows = table.find_all('tr')[1:]  # Skip header

                if i == 0:  # Average wait times table
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ride = cols[0].get_text().strip()
                            try:
                                wait = int(re.search(r'\d+', cols[1].get_text()).group())
                                wait_times_avg[ride] = wait
                            except:
                                pass

                elif i == 1:  # Maximum wait times table
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ride = cols[0].get_text().strip()
                            try:
                                wait = int(re.search(r'\d+', cols[1].get_text()).group())
                                wait_times_max[ride] = wait
                            except:
                                pass

                elif i == 2:  # Uptime table
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ride = cols[0].get_text().strip()
                            try:
                                uptime_pct = float(re.search(r'(\d+\.?\d*)', cols[1].get_text()).group())
                                uptime[ride] = uptime_pct
                            except:
                                pass

            # Extract crowd level
            crowd_level = None
            crowd_text = soup.find(string=re.compile(r'Crowd level \d+%'))
            if crowd_text:
                match = re.search(r'(\d+)%', crowd_text)
                if match:
                    crowd_level = int(match.group(1))

            # Extract special events
            special_events = []
            if soup.find(string=re.compile(r'Early Entry', re.I)):
                special_events.append('Early Entry')
            if soup.find(string=re.compile(r'Holiday', re.I)):
                special_events.append('Holiday')

            # Get day of week
            day_of_week = date_obj.strftime('%A')

            data = {
                'date': date_str,
                'day_of_week': day_of_week,
                'url': url,
                'crowd_level': crowd_level,
                'special_events': special_events,
                'wait_times_average': wait_times_avg,
                'wait_times_max': wait_times_max,
                'ride_uptime': uptime
            }

            return data

        except Exception as e:
            print(f"Error fetching calendar data for {date_str}: {e}")
            return None

    def build_historical_dataset(self, start_date, end_date, delay=2):
        """
        Build comprehensive historical dataset for date range

        Args:
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            delay: Seconds between requests
        """
        print("="*80)
        print("BUILDING COMPREHENSIVE HISTORICAL DATASET")
        print(f"Date range: {start_date} to {end_date}")
        print("="*80)

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        historical_data = []
        current = start

        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            data = self.get_calendar_date_data(date_str)

            if data:
                historical_data.append(data)

            time.sleep(delay)
            current += timedelta(days=1)

        return historical_data

    def get_all_ride_patterns(self, delay=2):
        """Get historical patterns for all rides"""
        print("="*80)
        print("FETCHING HISTORICAL PATTERNS FOR ALL RIDES")
        print("="*80)

        rides = self.get_all_rides()
        all_patterns = []

        for ride in rides:
            patterns = self.get_ride_historical_patterns(ride['id'], ride['name'])
            if patterns:
                patterns['land'] = ride['land']
                all_patterns.append(patterns)

            time.sleep(delay)

        return all_patterns

    def save_to_json(self, data, filename):
        """Save data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\nData saved to {filename}")
        except Exception as e:
            print(f"Error saving to file: {e}")

    def get_ride_durations(self):
        """Get ride durations from TouringPlans.com data"""
        print("="*80)
        print("COLLECTING RIDE DURATIONS")
        print("Source: TouringPlans.com/disneyland/attractions/duration")
        print("="*80)

        # Duration data from TouringPlans.com
        # Note: TouringPlans uses JavaScript to load data, so we use pre-collected values
        durations = {
            "Adventureland Treehouse inspired by Walt Disney's Swiss Family Robinson": 5,
            "Alice in Wonderland": 4,
            "Astro Orbitor": 2,
            "Autopia": 5,
            "Big Thunder Mountain Railroad": 4,
            "Buzz Lightyear Astro Blasters": 5,
            "Casey Jr. Circus Train": 4,
            "Chip 'n' Dale's GADGETcoaster": 1,
            "Davy Crockett's Explorer Canoes": 10,
            "Disneyland Monorail": 15,
            "Disneyland Railroad": 22,
            "Dumbo the Flying Elephant": 2,
            "Walt Disney's Enchanted Tiki Room": 15,
            "Finding Nemo Submarine Voyage": 13,
            "Gadget's Go Coaster": 1,
            "Haunted Mansion": 9,
            "Haunted Mansion Holiday": 9,
            "Indiana Jones™ Adventure": 4,
            "\"it's a small world\"": 15,
            "Jungle Cruise": 8,
            "King Arthur Carrousel": 2,
            "Mad Tea Party": 2,
            "Matterhorn Bobsleds": 3,
            "Meet Disney Princesses at Royal Hall": 5,
            "Mickey & Minnie's Runaway Railway": 5,
            "Millennium Falcon: Smugglers Run": 5,
            "Mr. Toad's Wild Ride": 2,
            "Peter Pan's Flight": 3,
            "Pinocchio's Daring Journey": 3,
            "Pirate's Lair on Tom Sawyer Island": 15,
            "Pirates of the Caribbean": 16,
            "Roger Rabbit's Car Toon Spin": 4,
            "Sailing Ship Columbia": 12,
            "Snow White's Enchanted Wish": 2,
            "Space Mountain": 3,
            "Star Tours - The Adventures Continue": 7,
            "Star Wars: Rise of the Resistance": 18,
            "Storybook Land Canal Boats": 7,
            "The Many Adventures of Winnie the Pooh": 4,
            "Tiana's Bayou Adventure": 11,
            "Mark Twain Riverboat": 12,
            "Great Moments with Mr. Lincoln": 16
        }

        print(f"Collected durations for {len(durations)} rides")
        return durations

    def get_height_requirements(self):
        """Get height requirements from TouringPlans.com data"""
        print("\n" + "="*80)
        print("COLLECTING HEIGHT REQUIREMENTS")
        print("Source: TouringPlans.com/disneyland/attractions/height-requirements")
        print("="*80)

        # Height requirement data from TouringPlans.com
        # Note: TouringPlans uses JavaScript to load data, so we use pre-collected values
        height_requirements = {
            "Indiana Jones™ Adventure": 46,
            "Matterhorn Bobsleds": 42,
            "Big Thunder Mountain Railroad": 40,
            "Space Mountain": 40,
            "Star Tours - The Adventures Continue": 40,
            "Star Wars: Rise of the Resistance": 40,
            "Tiana's Bayou Adventure": 40,
            "Millennium Falcon: Smugglers Run": 38,
            "Chip 'n' Dale's GADGETcoaster": 35,
            "Autopia": 32
        }

        print(f"Collected height requirements for {len(height_requirements)} rides")
        return height_requirements

    async def _fetch_themeparkiq_async(self, url="https://www.themeparkiq.com/disneyland/daily-calendar"):
        """Fetch ThemeParkIQ page using zendriver"""
        try:
            import zendriver as zd

            browser = await zd.start()
            page = await browser.get(url)
            await page.sleep(2)
            html = await page.get_content()
            await browser.stop()

            return html

        except Exception as e:
            print(f"Zendriver error: {e}")
            return None

    def _filter_upcoming_times(self, items, current_time=None):
        """
        Filter items to only include upcoming times

        Args:
            items: List of items with 'times' field
            current_time: datetime object for comparison (defaults to now)

        Returns:
            Filtered list with only upcoming times
        """
        if current_time is None:
            current_time = datetime.now()

        filtered_items = []

        for item in items:
            if 'times' not in item or not item['times']:
                # No times, keep the item as-is
                filtered_items.append(item)
                continue

            upcoming_times = []
            for time_str in item['times']:
                try:
                    # Parse time string like "8:30pm" or "10:00am"
                    time_str_clean = time_str.strip().lower()

                    # Extract time using regex
                    match = re.match(r'(\d{1,2}):(\d{2})\s*([ap]m)', time_str_clean)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        am_pm = match.group(3)

                        # Convert to 24-hour format
                        if am_pm == 'pm' and hour != 12:
                            hour += 12
                        elif am_pm == 'am' and hour == 12:
                            hour = 0

                        # Create datetime for comparison
                        event_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

                        # Only include if time is in the future (with 15 minute buffer)
                        # This accounts for shows that might be starting soon
                        if event_time > current_time - timedelta(minutes=15):
                            upcoming_times.append(time_str)

                except Exception as e:
                    # If parsing fails, include the time anyway
                    upcoming_times.append(time_str)

            # Only include item if it has upcoming times
            if upcoming_times:
                item_copy = item.copy()
                item_copy['times'] = upcoming_times
                filtered_items.append(item_copy)

        return filtered_items

    def get_themeparkiq_calendar(self, date_str=None):
        """
        Fetch current day's park information from ThemeParkIQ
        Uses zendriver to handle JavaScript-rendered content

        Args:
            date_str: Date in format 'YYYY-MM-DD' (defaults to today)

        Returns:
            dict with park hours, events, parades, fireworks, shows, closed attractions
            (filtered to show only upcoming times)
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        print("="*80)
        print("FETCHING PARK CALENDAR DATA")
        print(f"Date: {date_str}")
        print("Source: ThemeParkIQ.com (using zendriver)")
        print("="*80)

        current_time = datetime.now()
        url = "https://www.themeparkiq.com/disneyland/daily-calendar"

        try:
            # Fetch with zendriver to get JavaScript-rendered content
            html = asyncio.run(self._fetch_themeparkiq_async())

            if not html:
                raise Exception("Failed to fetch page with zendriver")

            soup = BeautifulSoup(html, 'html.parser')

            calendar_data = {
                'date': date_str,
                'url': url,
                'parks': {}
            }

            # Extract Disneyland Park information
            all_parades = self._extract_themeparkiq_entertainment(soup, 'Parades')
            all_nighttime = self._extract_themeparkiq_entertainment(soup, 'Nighttime Entertainment')

            # Filter to show only upcoming times
            upcoming_parades = self._filter_upcoming_times(all_parades, current_time)
            upcoming_nighttime = self._filter_upcoming_times(all_nighttime, current_time)

            disneyland_data = {
                'hours': self._extract_themeparkiq_hours(soup, 'Disneyland Park'),
                'parades': upcoming_parades,
                'nighttime': upcoming_nighttime,
                'events': self._extract_themeparkiq_events(soup),
                'closed_attractions': self._extract_themeparkiq_closures(soup, 'Disneyland Park')
            }

            calendar_data['parks']['Disneyland Park'] = disneyland_data

            # Get character schedules (separate page) and filter to upcoming times
            all_characters = self.get_character_schedules()
            upcoming_characters = self._filter_upcoming_times(all_characters, current_time)
            calendar_data['character_meet_and_greets'] = upcoming_characters

            print(f"\nExtracted data for {date_str}:")
            print(f"  Disneyland hours: {disneyland_data['hours']}")
            print(f"  Parades: {len(all_parades)} total, {len(upcoming_parades)} upcoming")
            print(f"  Nighttime shows: {len(all_nighttime)} total, {len(upcoming_nighttime)} upcoming")
            print(f"  Events: {len(disneyland_data.get('events', []))} found")
            print(f"  Closed attractions: {len(disneyland_data.get('closed_attractions', []))} found")
            print(f"  Character meet & greets: {len(all_characters)} total, {len(upcoming_characters)} upcoming")

            return calendar_data

        except Exception as e:
            print(f"Error fetching ThemeParkIQ calendar: {e}")
            print("Returning default values...")
            return {
                'date': date_str,
                'url': url,
                'parks': {
                    'Disneyland Park': {
                        'hours': {'open': '08:00', 'close': '23:00'},
                        'parades': [],
                        'nighttime': [],
                        'events': [],
                        'closed_attractions': []
                    },
                    'Disney California Adventure Park': {
                        'hours': {'open': '08:00', 'close': '21:00'},
                        'nighttime': [],
                        'closed_attractions': []
                    }
                },
                'error': str(e)
            }

    def _extract_themeparkiq_hours(self, soup, park_name):
        """Extract park operating hours from ThemeParkIQ"""
        try:
            # Look for the park name and then find the hours nearby
            text = soup.get_text()

            # Pattern to match park hours like "8:00am - 11:00pm"
            time_pattern = r'(\d{1,2}:\d{2}[ap]m)\s*-\s*(\d{1,2}:\d{2}[ap]m)'

            # Split by lines and find the park section
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if park_name in line:
                    # Check next few lines for hours
                    for j in range(i, min(i+10, len(lines))):
                        if 'Operating' in lines[j] or 'operating' in lines[j].lower():
                            match = re.search(time_pattern, lines[j], re.IGNORECASE)
                            if match:
                                open_time = match.group(1).upper().replace('AM', ' AM').replace('PM', ' PM')
                                close_time = match.group(2).upper().replace('AM', ' AM').replace('PM', ' PM')

                                # Convert to 24-hour format
                                open_24 = datetime.strptime(open_time.strip(), '%I:%M %p').strftime('%H:%M')
                                close_24 = datetime.strptime(close_time.strip(), '%I:%M %p').strftime('%H:%M')

                                return {'open': open_24, 'close': close_24}
        except Exception as e:
            print(f"Error extracting hours for {park_name}: {e}")
            pass

        # Default hours if not found
        if 'Adventure' in park_name:
            return {'open': '08:00', 'close': '21:00'}
        return {'open': '08:00', 'close': '23:00'}

    def _extract_themeparkiq_entertainment(self, soup, section_name, park='DL'):
        """Extract parades or nighttime entertainment from ThemeParkIQ"""
        items = []

        try:
            # Find all links (entertainment names)
            links = soup.find_all('a', href=lambda x: x and '/entertainment/' in str(x))

            for link in links:
                name = link.get_text().strip()

                # Find the next sibling div with class "text-xs" (contains times)
                time_div = link.find_next_sibling('div', class_='text-xs')

                if time_div:
                    time_text = time_div.get_text()
                    # Extract times like "1:30pm", "2:45pm"
                    time_pattern = r'(\d{1,2}:\d{2}[ap]m)'
                    times = re.findall(time_pattern, time_text, re.IGNORECASE)

                    if times:
                        items.append({
                            'name': name,
                            'times': [t.strip() for t in times]
                        })

        except Exception as e:
            print(f"Error extracting {section_name}: {e}")
            pass

        return items

    def _extract_themeparkiq_events(self, soup):
        """Extract current events from ThemeParkIQ"""
        events = []

        try:
            # Look for event-related elements
            # Events might be in headings, list items, or special divs
            text = soup.get_text()

            # Common event patterns to look for
            event_patterns = [
                'Halloween Time',
                '70th Anniversary',
                'Coco Plaza',
                'Holiday',
                'Festival',
                'Celebration'
            ]

            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # Check if line contains any event pattern
                for pattern in event_patterns:
                    if pattern.lower() in line.lower() and 10 < len(line) < 100:
                        events.append({'name': line})
                        break

        except Exception as e:
            print(f"Error extracting events: {e}")
            pass

        return events

    def _extract_themeparkiq_closures(self, soup, park_name):
        """Extract closed attractions from ThemeParkIQ"""
        closures = []

        try:
            # Look for links to attraction pages that might be in a "closed" section
            # Or search for text patterns like "Closed for Refurbishment"
            text = soup.get_text()

            # Common ride names that might be closed
            common_rides = [
                'Big Thunder Mountain',
                'Space Mountain',
                'Matterhorn',
                'Pirates of the Caribbean',
                'Haunted Mansion',
                'Indiana Jones',
                'Splash Mountain',
                'It\'s a Small World',
                'Casey Jr',
                'Storybook Land',
                'Mickey\'s PhilharMagic'
            ]

            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()

                # Look for refurbishment or closed mentions
                if ('refurbishment' in line.lower() or 'closed' in line.lower()) and park_name in text[max(0,i*50-500):min(len(text),i*50+500)]:
                    # Check if any known ride names are nearby
                    context = ' '.join(lines[max(0,i-2):min(len(lines),i+3)])
                    for ride in common_rides:
                        if ride.lower() in context.lower():
                            closures.append({'name': ride})

        except Exception as e:
            print(f"Error extracting closures for {park_name}: {e}")
            pass

        return list({c['name']: c for c in closures}.values())  # Remove duplicates

    def get_character_schedules(self):
        """
        Fetch character meet and greet schedules from ThemeParkIQ

        Returns:
            list of character meet and greet schedules with times and locations
        """
        print("\n" + "="*80)
        print("FETCHING CHARACTER MEET & GREET SCHEDULES")
        print("Source: ThemeParkIQ.com/disneyland/character/schedule")
        print("="*80)

        url = "https://www.themeparkiq.com/disneyland/character/schedule"

        try:
            # Fetch with zendriver to get JavaScript-rendered content
            html = asyncio.run(self._fetch_themeparkiq_async(url))

            if not html:
                raise Exception("Failed to fetch character schedule page")

            soup = BeautifulSoup(html, 'html.parser')

            characters = []

            # Try multiple extraction methods

            # Method 1: Find character links with /character/ in href
            character_links = soup.find_all('a', href=lambda x: x and '/character/' in str(x))

            for link in character_links:
                character_name = link.get_text().strip()

                # Skip if empty, too short, or contains unwanted text
                if (not character_name or len(character_name) < 3 or
                    character_name.lower() in ['character', 'schedule', 'all characters']):
                    continue

                # Get parent element containing location and times
                parent = link.find_parent()
                location = None
                times = []

                # Search in multiple parent levels
                for level in range(5):  # Check up to 5 parent levels
                    if parent:
                        parent_text = parent.get_text()

                        # Extract times
                        time_pattern = r'(\d{1,2}:\d{2}\s*[ap]m)'
                        found_times = re.findall(time_pattern, parent_text, re.IGNORECASE)
                        if found_times and not times:
                            times = [t.strip() for t in found_times]

                        # Try to extract location (common patterns)
                        location_keywords = ['Adventure', 'Fantasyland', 'Frontierland', 'Main Street',
                                           'Tomorrowland', 'Star Wars', 'Pixar', 'Theater', 'Hall',
                                           'Plaza', 'Square', 'Courtyard']

                        for keyword in location_keywords:
                            if keyword in parent_text and not location:
                                # Extract sentence containing the keyword
                                lines = parent_text.split('\n')
                                for line in lines:
                                    if keyword in line and len(line) < 100:
                                        # Clean up the line
                                        clean_line = line.strip()
                                        if 3 < len(clean_line) < 100:
                                            location = clean_line
                                            break

                        parent = parent.find_parent()

                        # Stop if we found both
                        if location and times:
                            break

                # Add character if we have useful data
                if character_name and (location or times):
                    character_entry = {
                        'name': character_name
                    }

                    if location:
                        character_entry['location'] = location

                    if times:
                        character_entry['times'] = times

                    characters.append(character_entry)

            # Method 2: If Method 1 didn't find much, try finding all text with times
            if len(characters) < 5:
                print("  Trying alternative extraction method...")

                # Find all elements with time patterns
                all_text = soup.get_text()
                lines = all_text.split('\n')

                for i, line in enumerate(lines):
                    line = line.strip()
                    # Look for lines with time patterns
                    time_pattern = r'(\d{1,2}:\d{2}\s*[ap]m)'
                    times_found = re.findall(time_pattern, line, re.IGNORECASE)

                    if times_found and len(line) > 5 and len(line) < 100:
                        # Check nearby lines for character names
                        context_start = max(0, i-3)
                        context_end = min(len(lines), i+3)
                        context_lines = lines[context_start:context_end]

                        # Look for capitalized words that might be character names
                        for ctx_line in context_lines:
                            ctx_line = ctx_line.strip()
                            # Check if line looks like a name (starts with capital, reasonable length)
                            if (ctx_line and 3 < len(ctx_line) < 50 and
                                ctx_line[0].isupper() and
                                not any(kw in ctx_line.lower() for kw in ['schedule', 'hours', 'operating', 'park'])):

                                # This might be a character name
                                character_entry = {
                                    'name': ctx_line,
                                    'times': [t.strip() for t in times_found]
                                }

                                # Try to find location in context
                                for loc_line in context_lines:
                                    location_keywords = ['Adventure', 'Fantasyland', 'Frontierland', 'Main Street']
                                    for keyword in location_keywords:
                                        if keyword in loc_line:
                                            character_entry['location'] = loc_line.strip()
                                            break

                                characters.append(character_entry)
                                break

            # Remove duplicates based on character name
            unique_characters = []
            seen_names = set()
            for char in characters:
                if char['name'] not in seen_names:
                    unique_characters.append(char)
                    seen_names.add(char['name'])

            print(f"Found {len(unique_characters)} character meet and greets")
            return unique_characters

        except Exception as e:
            print(f"Error fetching character schedules: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_calendar_section(self, soup, section_name):
        """Extract items from a calendar section (events, parades, etc.)"""
        items = []

        try:
            # Search for specific data attributes or classes Disney uses
            # Look for schedule/calendar containers
            calendar_items = soup.find_all(attrs={
                'data-entitytype': re.compile(r'entertainment|event', re.IGNORECASE)
            })

            if not calendar_items:
                # Try finding by common class patterns
                calendar_items = soup.find_all(class_=re.compile(
                    r'scheduleItem|calendarCard|entertainmentCard',
                    re.IGNORECASE
                ))

            for item in calendar_items:
                # Extract name
                name_elem = item.find(class_=re.compile(r'name|title', re.IGNORECASE))
                if not name_elem:
                    name_elem = item.find(['h2', 'h3', 'h4', 'h5'])

                if name_elem:
                    name = name_elem.get_text().strip()

                    # Filter out CSS, JavaScript, and overly long strings
                    if (len(name) < 100 and
                        not name.startswith('#') and
                        not name.startswith('.') and
                        not '{' in name and
                        not '}' in name and
                        'onetrust' not in name.lower() and
                        'cookie' not in name.lower()):

                        # Extract times
                        time_elem = item.find(class_=re.compile(r'time|hour', re.IGNORECASE))
                        times = []
                        if time_elem:
                            time_text = time_elem.get_text()
                            times = re.findall(r'(\d{1,2}:\d{2}\s*[AP]M)', time_text)

                        item_data = {'name': name}
                        if times:
                            item_data['times'] = times

                        items.append(item_data)

        except Exception as e:
            print(f"Error extracting {section_name}: {e}")
            pass

        return items

    def _parse_calendar_item(self, element):
        """Parse a calendar item to extract name and time"""
        try:
            text = element.get_text().strip()

            # Look for time patterns
            time_pattern = r'(\d{1,2}:\d{2}\s*[AP]M)'
            times = re.findall(time_pattern, text)

            # Clean up the text to get the name
            name = re.sub(time_pattern, '', text).strip()
            name = re.sub(r'\s+', ' ', name)  # Remove extra whitespace

            if name and len(name) > 3:  # Avoid empty or very short strings
                item = {'name': name}
                if times:
                    item['times'] = times
                return item

        except:
            pass

        return None

    def display_summary(self, data):
        """Display summary of collected data"""
        if isinstance(data, list) and len(data) > 0:
            print("\n" + "="*80)
            print("DATA COLLECTION SUMMARY")
            print("="*80)

            if 'date' in data[0]:
                # Calendar data
                print(f"Total days collected: {len(data)}")
                print(f"Date range: {data[0]['date']} to {data[-1]['date']}")

                # Average crowd level
                crowd_levels = [d['crowd_level'] for d in data if d.get('crowd_level')]
                if crowd_levels:
                    avg_crowd = sum(crowd_levels) / len(crowd_levels)
                    print(f"Average crowd level: {avg_crowd:.1f}%")

                # Count rides with data
                total_rides = set()
                for day in data:
                    total_rides.update(day.get('wait_times_average', {}).keys())
                print(f"Unique rides tracked: {len(total_rides)}")

            elif 'ride_id' in data[0]:
                # Ride pattern data
                print(f"Total rides analyzed: {len(data)}")

                # Count patterns available
                patterns_count = {
                    'by_year': sum(1 for d in data if d.get('by_year')),
                    'by_day_of_week': sum(1 for d in data if d.get('by_day_of_week')),
                    'by_time_of_day': sum(1 for d in data if d.get('by_time_of_day')),
                    'by_month': sum(1 for d in data if d.get('by_month')),
                }

                print("\nPattern availability:")
                for pattern, count in patterns_count.items():
                    print(f"  {pattern}: {count} rides")

            print("="*80)


def main():
    """Example usage"""
    scraper = DisneylandComprehensiveScraper()

    print("DISNEYLAND WAIT TIME PREDICTION DATA COLLECTOR")
    print("Attribution: Powered by Queue-Times.com, TouringPlans.com & ThemeParkIQ.com")
    print()

    # Create data and output directories if they don't exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('output', exist_ok=True)

    # 1. Get all ride patterns (this is the key for predictions!)
    print("1. Collecting ride patterns from Queue-Times.com...")
    ride_patterns = scraper.get_all_ride_patterns(delay=0.5)  # Reduced delay for speed
    scraper.save_to_json(ride_patterns, 'data/disneyland_ride_patterns.json')
    scraper.display_summary(ride_patterns)

    # 2. Get ride durations from TouringPlans
    print("\n2. Collecting ride durations from TouringPlans.com...")
    durations = scraper.get_ride_durations()
    if durations:
        scraper.save_to_json(durations, 'data/ride_durations.json')

    # 3. Get height requirements from TouringPlans
    print("\n3. Collecting height requirements from TouringPlans.com...")
    heights = scraper.get_height_requirements()
    if heights:
        scraper.save_to_json(heights, 'data/ride_height_requirements.json')

    # 4. Get park calendar data from ThemeParkIQ
    print("\n4. Collecting park calendar data...")
    calendar_data = scraper.get_themeparkiq_calendar()
    if calendar_data:
        # Add generated_at timestamp for output
        calendar_data['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        scraper.save_to_json(calendar_data, 'data/park_calendar.json')

    print("\n" + "="*80)
    print("DATA COLLECTION COMPLETE!")
    print("Files created:")
    print("  data/disneyland_ride_patterns.json")
    print("  data/ride_durations.json")
    print("  data/ride_height_requirements.json")
    print("  data/park_calendar.json")
    print("="*80)


if __name__ == "__main__":
    main()
