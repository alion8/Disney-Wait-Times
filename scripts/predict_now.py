import json
from datetime import datetime
import statistics
import os
import requests

class DisneylandRealTimeAnalyzer:
    """
    Analyze Disneyland wait times RIGHT NOW:
    - Get REAL current wait times from API
    - Compare with historical predictions
    - Determine if NOW is the best time to visit
    - Show crowd level analysis

    Attribution: Powered by Queue-Times.com (https://queue-times.com/en-US)
    """

    def __init__(self, patterns_file='data/disneyland_ride_patterns.json', durations_file='data/ride_durations.json', height_requirements_file='data/ride_height_requirements.json'):
        """Initialize with ride patterns data"""
        self.patterns_file = patterns_file
        self.durations_file = durations_file
        self.height_requirements_file = height_requirements_file
        self.patterns = self._load_patterns()
        self.durations = self._load_durations()
        self.height_requirements = self._load_height_requirements()
        self.park_id = 16  # Disneyland
        self.api_url = f"https://queue-times.com/parks/{self.park_id}/queue_times.json"

        # Build ride lookup
        self.ride_patterns = {}
        if self.patterns:
            for ride in self.patterns:
                self.ride_patterns[ride['ride_name']] = ride

    def _load_patterns(self):
        """Load ride patterns from JSON file"""
        if not os.path.exists(self.patterns_file):
            print(f"ERROR: {self.patterns_file} not found!")
            print("Please run: python disneyland_comprehensive_scraper.py")
            return None

        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading patterns: {e}")
            return None

    def _load_durations(self):
        """Load ride durations from JSON file"""
        if not os.path.exists(self.durations_file):
            print(f"Warning: {self.durations_file} not found. Durations will not be included.")
            return {}

        try:
            with open(self.durations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading durations: {e}")
            return {}

    def _load_height_requirements(self):
        """Load ride height requirements from JSON file"""
        if not os.path.exists(self.height_requirements_file):
            print(f"Warning: {self.height_requirements_file} not found. Height requirements will not be included.")
            return {}

        try:
            with open(self.height_requirements_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading height requirements: {e}")
            return {}

    def _convert_inches_to_feet(self, inches):
        """Convert inches to feet and inches format (e.g., '3 ft 10 in')"""
        if isinstance(inches, str):
            return inches
        feet = inches // 12
        remaining_inches = inches % 12
        if remaining_inches == 0:
            return f"{feet} ft"
        return f"{feet} ft {remaining_inches} in"

    def get_real_time_waits(self):
        """Get ACTUAL current wait times from the API"""
        try:
            response = requests.get(self.api_url)
            response.raise_for_status()
            data = response.json()

            current_waits = {}
            for land in data.get('lands', []):
                for ride in land.get('rides', []):
                    current_waits[ride['name']] = {
                        'wait_time': ride.get('wait_time'),
                        'is_open': ride.get('is_open', False),
                        'last_updated': ride.get('last_updated')
                    }

            return current_waits
        except Exception as e:
            print(f"Error fetching real-time data: {e}")
            return {}

    def predict_for_current_time(self, ride_name):
        """Predict wait time based on historical patterns for RIGHT NOW"""
        now = datetime.now()
        ride_data = self.ride_patterns.get(ride_name)

        if not ride_data:
            return None

        day_of_week = now.strftime('%A')
        month = now.strftime('%b')
        hour = now.hour
        time_key = f"{hour:02d}:00"

        predictions = []

        # Time of day (most important)
        time_patterns = ride_data.get('by_time_of_day', {})
        if time_key in time_patterns and 'avg' in time_patterns[time_key]:
            predictions.append(time_patterns[time_key]['avg'])
            predictions.append(time_patterns[time_key]['avg'])  # Double weight

        # Month
        monthly_patterns = ride_data.get('by_month', {})
        if month in monthly_patterns and isinstance(monthly_patterns[month], dict):
            if 'value_1' in monthly_patterns[month]:
                predictions.append(monthly_patterns[month]['value_1'])

        # Day of week
        day_patterns = ride_data.get('by_day_of_week', {})
        if day_of_week in day_patterns and isinstance(day_patterns[day_of_week], dict):
            if 'avg' in day_patterns[day_of_week]:
                predictions.append(day_patterns[day_of_week]['avg'])

        if predictions:
            return round(statistics.mean(predictions), 1)
        return None

    def get_park_hours(self):
        """Get today's park operating hours"""
        # Typical Disneyland hours (can be updated by scraping calendar)
        # Most days: 8 AM - midnight (00:00)
        # Early entry: 7:30 or 8:00 AM for resort guests
        # Extended hours on busy days: until 1 AM

        # Default operating hours
        opening_hour = 8  # 8 AM
        closing_hour = 24  # Midnight (0:00 next day)

        # Try to get actual hours from calendar (optional enhancement)
        try:
            from bs4 import BeautifulSoup
            now = datetime.now()
            url = f"https://queue-times.com/en-US/parks/{self.park_id}/calendar/{now.year}/{now.month:02d}/{now.day:02d}"
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for hours pattern like "08:00-00:00" or "08:00-23:00"
            import re
            hours_text = soup.find(string=re.compile(r'\d{2}:\d{2}-\d{2}:\d{2}'))
            if hours_text:
                # Extract just the time pattern
                match = re.search(r'(\d{2}):(\d{2})-(\d{2}):(\d{2})', str(hours_text))
                if match:
                    opening_hour = int(match.group(1))
                    closing_hour = int(match.group(3))
                    if closing_hour == 0:
                        closing_hour = 24
        except:
            pass  # Use defaults if scraping fails

        return {
            'opening': opening_hour,
            'closing': closing_hour,
            'is_open_now': opening_hour <= datetime.now().hour < closing_hour
        }

    def analyze_best_time_to_visit(self, ride_name):
        """Determine the best time to visit this ride based on historical hourly patterns"""
        ride_data = self.ride_patterns.get(ride_name)
        if not ride_data:
            return None

        time_patterns = ride_data.get('by_time_of_day', {})
        if not time_patterns:
            return None

        # Get park hours
        park_hours = self.get_park_hours()
        opening_hour = park_hours['opening']
        closing_hour = park_hours['closing']

        # Get all hourly waits
        hourly_waits = []
        for hour_key, data in time_patterns.items():
            if isinstance(data, dict) and 'avg' in data:
                hour = int(hour_key.split(':')[0])
                # Only include hours when park is typically open
                if opening_hour <= hour < closing_hour:
                    hourly_waits.append((hour, data['avg']))

        if not hourly_waits:
            return None

        # Sort by wait time
        hourly_waits.sort(key=lambda x: x[1])

        best_times = hourly_waits[:3]  # Top 3 best times
        worst_times = sorted(hourly_waits, key=lambda x: x[1], reverse=True)[:3]

        current_hour = datetime.now().hour
        current_wait = None
        for hour, wait in hourly_waits:
            if hour == current_hour:
                current_wait = wait
                break

        return {
            'best_times': best_times,
            'worst_times': worst_times,
            'current_hour': current_hour,
            'current_typical_wait': current_wait,
            'park_hours': park_hours
        }

    def get_comprehensive_analysis(self):
        """Get complete analysis: real-time + predictions + recommendations"""
        now = datetime.now()

        print("Fetching REAL-TIME wait times from Disneyland...")
        real_time_waits = self.get_real_time_waits()

        if not real_time_waits:
            print("Warning: Could not fetch real-time data")

        print("Calculating predictions based on historical patterns...")

        analysis = []

        for ride_name in self.ride_patterns.keys():
            predicted = self.predict_for_current_time(ride_name)
            real_time = real_time_waits.get(ride_name, {})
            actual_wait = real_time.get('wait_time')
            is_open = real_time.get('is_open', False)

            if predicted is not None:
                # Calculate difference
                difference = None
                if actual_wait is not None and actual_wait > 0:
                    difference = actual_wait - predicted

                analysis.append({
                    'ride_name': ride_name,
                    'actual_wait': actual_wait if is_open else None,
                    'predicted_wait': predicted,
                    'difference': difference,
                    'is_open': is_open,
                    'status': 'OPEN' if is_open else 'CLOSED'
                })

        return analysis, now

    def export_json_reports(self, analysis, timestamp):
        """Export organized JSON files for easy consumption"""
        print("\nExporting JSON reports...")

        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)

        # 1. Current Wait Times
        current_waits = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'day_of_week': timestamp.strftime('%A'),
            'rides': []
        }

        for ride in analysis:
            if ride['is_open'] and ride['actual_wait'] is not None:
                ride_entry = {
                    'name': ride['ride_name'],
                    'wait_time_minutes': ride['actual_wait'],
                    'status': 'OPEN'
                }
                # Add duration if available
                if ride['ride_name'] in self.durations:
                    ride_entry['ride_duration_minutes'] = self.durations[ride['ride_name']]
                    ride_entry['total_time_minutes'] = ride['actual_wait'] + self.durations[ride['ride_name']]

                # Add height requirement if available
                if ride['ride_name'] in self.height_requirements:
                    height_inches = self.height_requirements[ride['ride_name']]
                    ride_entry['height_requirement_inches'] = height_inches
                    ride_entry['height_requirement'] = self._convert_inches_to_feet(height_inches)
                else:
                    ride_entry['height_requirement_inches'] = None
                    ride_entry['height_requirement'] = 'Any Height'

                current_waits['rides'].append(ride_entry)

        current_waits['rides'].sort(key=lambda x: x['wait_time_minutes'], reverse=True)

        with open('output/current_waits.json', 'w', encoding='utf-8') as f:
            json.dump(current_waits, f, indent=2, ensure_ascii=False)
        print("  - output/current_waits.json")

        # 2. Predictions vs Actual
        comparison = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'hour': timestamp.hour,
            'rides': []
        }

        for ride in analysis:
            if ride['is_open'] and ride['actual_wait'] is not None:
                crowd_status = 'NORMAL'
                if ride['difference'] and ride['difference'] > 10:
                    crowd_status = 'BUSIER_THAN_USUAL'
                elif ride['difference'] and ride['difference'] < -10:
                    crowd_status = 'LIGHTER_THAN_USUAL'

                ride_entry = {
                    'name': ride['ride_name'],
                    'actual_wait_minutes': ride['actual_wait'],
                    'predicted_wait_minutes': round(ride['predicted_wait'], 1),
                    'difference_minutes': round(ride['difference'], 1) if ride['difference'] else 0,
                    'crowd_status': crowd_status
                }

                # Add duration if available
                if ride['ride_name'] in self.durations:
                    ride_entry['ride_duration_minutes'] = self.durations[ride['ride_name']]

                # Add height requirement if available
                if ride['ride_name'] in self.height_requirements:
                    height_inches = self.height_requirements[ride['ride_name']]
                    ride_entry['height_requirement_inches'] = height_inches
                    ride_entry['height_requirement'] = self._convert_inches_to_feet(height_inches)
                else:
                    ride_entry['height_requirement_inches'] = None
                    ride_entry['height_requirement'] = 'Any Height'

                comparison['rides'].append(ride_entry)

        comparison['rides'].sort(key=lambda x: x['actual_wait_minutes'], reverse=True)

        with open('output/ride_comparison.json', 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print("  - output/ride_comparison.json")

        # 3. Best Times to Visit (for popular rides)
        popular_rides = [
            'Star Wars: Rise of the Resistance',
            'Indiana Jones™ Adventure',
            'Space Mountain',
            'Matterhorn Bobsleds',
            'Haunted Mansion Holiday'
        ]

        best_times = {
            'generated_at': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'rides': []
        }

        for ride_name in popular_rides:
            ride_info = next((r for r in analysis if r['ride_name'] == ride_name), None)
            if ride_info and ride_info['is_open']:
                best_time_analysis = self.analyze_best_time_to_visit(ride_name)

                if best_time_analysis:
                    ride_data = {
                        'name': ride_name,
                        'current_wait_minutes': ride_info['actual_wait'],
                        'historical_average_this_hour': round(ride_info['predicted_wait'], 1),
                        'best_times': [],
                        'worst_times': []
                    }

                    for hour, wait in best_time_analysis['best_times']:
                        ride_data['best_times'].append({
                            'time': f"{hour:02d}:00",
                            'average_wait_minutes': round(wait, 1)
                        })

                    for hour, wait in best_time_analysis['worst_times']:
                        ride_data['worst_times'].append({
                            'time': f"{hour:02d}:00",
                            'average_wait_minutes': round(wait, 1)
                        })

                    best_times['rides'].append(ride_data)

        with open('output/best_times.json', 'w', encoding='utf-8') as f:
            json.dump(best_times, f, indent=2, ensure_ascii=False)
        print("  - output/best_times.json")

        # 4. Park Status Overview
        open_rides = [r for r in analysis if r['is_open'] and r['actual_wait'] is not None]
        actual_waits_list = [r['actual_wait'] for r in open_rides if r['actual_wait']]
        predicted_waits_list = [r['predicted_wait'] for r in open_rides if r['predicted_wait']]

        park_status = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'day_of_week': timestamp.strftime('%A'),
            'park_hours': self.get_park_hours(),
            'total_rides_open': len(open_rides),
            'total_rides_closed': len([r for r in analysis if not r['is_open']]),
            'average_wait_time_minutes': round(statistics.mean(actual_waits_list), 1) if actual_waits_list else 0,
            'average_historical_wait_minutes': round(statistics.mean(predicted_waits_list), 1) if predicted_waits_list else 0,
            'crowd_level': 'NORMAL'
        }

        if actual_waits_list and predicted_waits_list:
            overall_diff = park_status['average_wait_time_minutes'] - park_status['average_historical_wait_minutes']

            if overall_diff > 5:
                park_status['crowd_level'] = 'BUSIER_THAN_TYPICAL'
                park_status['crowd_difference_minutes'] = round(overall_diff, 1)
                park_status['recommendation'] = 'Consider visiting later or focus on low-wait attractions'
            elif overall_diff < -5:
                park_status['crowd_level'] = 'LIGHTER_THAN_TYPICAL'
                park_status['crowd_difference_minutes'] = round(overall_diff, 1)
                park_status['recommendation'] = 'Great time to visit! Take advantage of lower waits'
            else:
                park_status['crowd_difference_minutes'] = round(overall_diff, 1)
                park_status['recommendation'] = 'Normal crowds for this time of day'

        with open('output/park_status.json', 'w', encoding='utf-8') as f:
            json.dump(park_status, f, indent=2, ensure_ascii=False)
        print("  - output/park_status.json")

        # 5. Shortest Waits (Best Options Now)
        shortest = sorted(open_rides, key=lambda x: x['actual_wait'] if x['actual_wait'] else 999)[:10]

        best_options = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'rides': []
        }

        for ride in shortest:
            ride_entry = {
                'name': ride['ride_name'],
                'wait_time_minutes': ride['actual_wait'],
                'predicted_wait_minutes': round(ride['predicted_wait'], 1)
            }

            # Add duration if available
            if ride['ride_name'] in self.durations:
                ride_entry['ride_duration_minutes'] = self.durations[ride['ride_name']]
                ride_entry['total_time_minutes'] = ride['actual_wait'] + self.durations[ride['ride_name']]

            # Add height requirement if available
            if ride['ride_name'] in self.height_requirements:
                height_inches = self.height_requirements[ride['ride_name']]
                ride_entry['height_requirement_inches'] = height_inches
                ride_entry['height_requirement'] = self._convert_inches_to_feet(height_inches)
            else:
                ride_entry['height_requirement_inches'] = None
                ride_entry['height_requirement'] = 'Any Height'

            best_options['rides'].append(ride_entry)

        with open('output/best_options_now.json', 'w', encoding='utf-8') as f:
            json.dump(best_options, f, indent=2, ensure_ascii=False)
        print("  - output/best_options_now.json")

        # 6. Park Calendar - Copy from data/ (already filtered to upcoming times)
        calendar_file = 'data/park_calendar.json'
        if os.path.exists(calendar_file):
            try:
                with open(calendar_file, 'r', encoding='utf-8') as f:
                    calendar_data = json.load(f)

                # Create output format (data is already filtered to upcoming times by scraper)
                calendar_output = {
                    'date': calendar_data.get('date', timestamp.strftime('%Y-%m-%d')),
                    'generated_at': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'parks': {}
                }

                # Process Disneyland Park data
                if 'Disneyland Park' in calendar_data.get('parks', {}):
                    dl_data = calendar_data['parks']['Disneyland Park']
                    calendar_output['parks']['Disneyland Park'] = {
                        'hours': dl_data.get('hours', {}),
                        'parades': dl_data.get('parades', []),
                        'nighttime_entertainment': dl_data.get('nighttime', []),
                        'special_events': dl_data.get('events', []),
                        'closed_attractions': dl_data.get('closed_attractions', [])
                    }

                # Process California Adventure if available
                if 'Disney California Adventure Park' in calendar_data.get('parks', {}):
                    dca_data = calendar_data['parks']['Disney California Adventure Park']
                    calendar_output['parks']['Disney California Adventure Park'] = {
                        'hours': dca_data.get('hours', {}),
                        'nighttime_entertainment': dca_data.get('nighttime', []),
                        'closed_attractions': dca_data.get('closed_attractions', [])
                    }

                # Add character meet and greets
                calendar_output['character_meet_and_greets'] = calendar_data.get('character_meet_and_greets', [])

                with open('output/park_calendar.json', 'w', encoding='utf-8') as f:
                    json.dump(calendar_output, f, indent=2, ensure_ascii=False)
                print("  - output/park_calendar.json")
            except Exception as e:
                print(f"  - Warning: Could not export calendar data: {e}")

        print("\nAll JSON reports exported successfully!")

    def display_comprehensive_report(self):
        """Display complete analysis with real-time vs predictions"""
        analysis, now = self.get_comprehensive_analysis()

        print("\n" + "="*90)
        print("DISNEYLAND REAL-TIME WAIT TIME ANALYSIS")
        print(f"Powered by Queue-Times.com (https://queue-times.com/en-US)")
        print("="*90)
        print(f"\nCurrent Time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}")
        print(f"Analysis Hour: {now.hour}:00")
        print("="*90)

        # Separate open and closed rides
        open_rides = [r for r in analysis if r['is_open'] and r['actual_wait'] is not None]
        closed_rides = [r for r in analysis if not r['is_open']]

        # Sort by actual wait time
        open_rides.sort(key=lambda x: x['actual_wait'] if x['actual_wait'] else 0, reverse=True)

        print(f"\n{'='*90}")
        print(f"ACTUAL vs PREDICTED WAIT TIMES ({len(open_rides)} rides currently open)")
        print(f"{'='*90}")
        print(f"{'Rank':<6} {'Ride':<38} {'Actual':<10} {'Predicted':<12} {'Diff':<10} {'Status'}")
        print("-"*90)

        for i, ride in enumerate(open_rides[:20], 1):
            ride_name = ride['ride_name'][:36]
            actual = ride['actual_wait'] if ride['actual_wait'] else 0
            predicted = ride['predicted_wait']
            diff = ride['difference']

            diff_str = f"{diff:+.0f} min" if diff is not None else "N/A"

            # Color code the difference
            status_indicator = ""
            if diff is not None:
                if diff > 10:
                    status_indicator = "BUSY"
                elif diff < -10:
                    status_indicator = "LIGHT"
                else:
                    status_indicator = "NORMAL"

            print(f"{i:<6} {ride_name:<38} {actual:>4.0f} min   {predicted:>4.0f} min    {diff_str:<10} {status_indicator}")

        # Show shortest waits
        shortest = sorted(open_rides, key=lambda x: x['actual_wait'] if x['actual_wait'] else 999)[:10]
        print(f"\n{'='*90}")
        print(f"BEST OPTIONS RIGHT NOW (Shortest Actual Waits):")
        print("-"*90)
        for i, ride in enumerate(shortest, 1):
            ride_name = ride['ride_name'][:50]
            actual = ride['actual_wait'] if ride['actual_wait'] else 0
            print(f"{i:<3}. {ride_name:<50} {actual:>4.0f} min (Predicted: {ride['predicted_wait']:.0f})")

        # Show park hours
        park_hours_info = self.get_park_hours()
        print(f"\n{'='*90}")
        print("PARK HOURS TODAY")
        print("="*90)
        opening_time = f"{park_hours_info['opening']:02d}:00"
        closing_time = "00:00" if park_hours_info['closing'] == 24 else f"{park_hours_info['closing']:02d}:00"
        print(f"Operating Hours: {opening_time} - {closing_time}")
        print(f"Park Currently: {'OPEN' if park_hours_info['is_open_now'] else 'CLOSED'}")

        # Analyze specific popular rides with best time recommendations
        print(f"\n{'='*90}")
        print("POPULAR RIDES - BEST TIME TO VISIT ANALYSIS")
        print(f"(Filtered to show only hours when park is open: {opening_time}-{closing_time})")
        print("="*90)

        popular_rides = [
            'Star Wars: Rise of the Resistance',
            'Indiana Jones™ Adventure',
            'Space Mountain',
            'Matterhorn Bobsleds',
            'Haunted Mansion Holiday'
        ]

        for ride_name in popular_rides:
            ride_info = next((r for r in analysis if r['ride_name'] == ride_name), None)
            if ride_info and ride_info['is_open']:
                best_time_analysis = self.analyze_best_time_to_visit(ride_name)

                print(f"\n{ride_name}")
                print("-" * 90)
                print(f"  Current Actual Wait: {ride_info['actual_wait']} minutes")
                print(f"  Historical Average (this hour): {ride_info['predicted_wait']:.0f} minutes")

                if best_time_analysis:
                    print(f"\n  Best Times to Visit (historically):")
                    for hour, wait in best_time_analysis['best_times']:
                        time_str = f"{hour:02d}:00"
                        is_current = " <-- NOW!" if hour == now.hour else ""
                        print(f"    {time_str} - Average {wait:.0f} min{is_current}")

                    print(f"\n  Worst Times to Avoid:")
                    for hour, wait in best_time_analysis['worst_times']:
                        time_str = f"{hour:02d}:00"
                        is_current = " <-- NOW!" if hour == now.hour else ""
                        print(f"    {time_str} - Average {wait:.0f} min{is_current}")

        # Overall crowd analysis
        print(f"\n{'='*90}")
        print("OVERALL PARK ANALYSIS")
        print("="*90)

        actual_waits_list = [r['actual_wait'] for r in open_rides if r['actual_wait']]
        predicted_waits_list = [r['predicted_wait'] for r in open_rides if r['predicted_wait']]

        if actual_waits_list and predicted_waits_list:
            avg_actual = statistics.mean(actual_waits_list)
            avg_predicted = statistics.mean(predicted_waits_list)
            overall_diff = avg_actual - avg_predicted

            print(f"\nAverage Actual Wait Time: {avg_actual:.1f} minutes")
            print(f"Average Historical Wait (this hour): {avg_predicted:.1f} minutes")
            print(f"Difference: {overall_diff:+.1f} minutes")

            if overall_diff > 5:
                print(f"\n[!] BUSIER than typical for this time ({overall_diff:.0f} min above average)")
                print("    Consider visiting later or focus on low-wait attractions")
            elif overall_diff < -5:
                print(f"\n[+] LIGHTER than typical for this time ({abs(overall_diff):.0f} min below average)")
                print("    Great time to visit! Take advantage of lower waits")
            else:
                print(f"\n[=] NORMAL crowds for this time of day")

        # Show closed rides count
        if closed_rides:
            print(f"\nCurrently Closed: {len(closed_rides)} attractions")

        print(f"\n{'='*90}")


def main():
    """Main function - comprehensive real-time analysis"""
    print("DISNEYLAND REAL-TIME WAIT TIME ANALYZER")
    print("Getting actual wait times and comparing with historical patterns...")
    print()

    # Clean up old JSON output files from output folder
    output_files = [
        'output/current_waits.json',
        'output/ride_comparison.json',
        'output/best_times.json',
        'output/best_options_now.json',
        'output/park_status.json',
        'output/park_calendar.json'
    ]

    for file in output_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except Exception as e:
                print(f"Warning: Could not delete {file}: {e}")

    analyzer = DisneylandRealTimeAnalyzer()

    if not analyzer.patterns:
        print("\nPlease run the data collector first:")
        print("  python disneyland_comprehensive_scraper.py")
        return

    # Get and display comprehensive analysis
    analyzer.display_comprehensive_report()

    # Export JSON reports
    analysis, timestamp = analyzer.get_comprehensive_analysis()
    analyzer.export_json_reports(analysis, timestamp)

    print("\n" + "="*90)
    print("TIP: Focus on rides with ACTUAL waits below historical average!")
    print("="*90)


if __name__ == "__main__":
    main()
