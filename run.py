#!/usr/bin/env python3
"""
Disneyland Wait Time Analyzer - Main Runner
Automatically collects data if needed, then runs the analyzer
"""

import os
import sys
import subprocess
import json
from datetime import datetime


def check_data_files():
    """Check if required data files exist"""
    required_files = [
        'data/disneyland_ride_patterns.json',
        'data/ride_durations.json',
        'data/ride_height_requirements.json'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    return missing_files

def calendar_needs_refresh():
    """Calendar data should be refreshed every run to get latest shows and schedules"""
    return True  # Always refresh to get most up-to-date park calendar

def run_data_collector():
    """Run the data collection script"""
    print("="*90)
    print("COLLECTING DATA FROM QUEUE-TIMES.COM & TOURINGPLANS.COM")
    print("This will take about 30-40 seconds")
    print("  - Ride patterns (54 rides)")
    print("  - Ride durations")
    print("  - Height requirements")
    print("="*90)
    print()

    try:
        result = subprocess.run(
            [sys.executable, 'scripts/disneyland_comprehensive_scraper.py'],
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\nError running data collector: {e}")
        return False
    except FileNotFoundError:
        print("\nError: scripts/disneyland_comprehensive_scraper.py not found!")
        return False

def run_analyzer():
    """Run the wait time analyzer"""
    print("\n" + "="*90)
    print("ANALYZING CURRENT WAIT TIMES")
    print("="*90)
    print()

    try:
        result = subprocess.run(
            [sys.executable, 'scripts/predict_now.py'],
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\nError running analyzer: {e}")
        return False
    except FileNotFoundError:
        print("\nError: scripts/predict_now.py not found!")
        return False

def main():
    """Main entry point"""
    print("DISNEYLAND WAIT TIME SYSTEM")
    print("="*90)
    print()

    # Check for missing data files
    missing_files = check_data_files()
    needs_calendar_refresh = calendar_needs_refresh()

    if missing_files:
        print("Missing required data files:")
        for file in missing_files:
            print(f"  - {file}")
        print()

        response = input("Would you like to collect all data now? This takes ~30-40 seconds. (y/n): ").strip().lower()

        if response == 'y' or response == 'yes':
            print()
            if not run_data_collector():
                print("\nData collection failed. Exiting.")
                sys.exit(1)
            print("\nData collection complete!")
        else:
            print("\nCannot proceed without data files. Exiting.")
            print("Run manually: python scripts/disneyland_comprehensive_scraper.py")
            sys.exit(1)
    elif needs_calendar_refresh:
        print("Static data files found.")
        print("Refreshing park calendar to get latest shows and schedules...")
        print()
        if not run_data_collector():
            print("\nCalendar refresh failed. Continuing anyway.")
        else:
            print("\nCalendar data updated!")
    else:
        print("All data files found.")

    # Run the analyzer
    if not run_analyzer():
        print("\nAnalyzer failed. Exiting.")
        sys.exit(1)

    print("\n" + "="*90)
    print("COMPLETE!")
    print("Data files saved in data/ folder:")
    print("  - disneyland_ride_patterns.json")
    print("  - ride_durations.json")
    print("  - ride_height_requirements.json")
    print("  - park_calendar.json")
    print("\nOutput reports saved in output/ folder:")
    print("  - current_waits.json")
    print("  - ride_comparison.json")
    print("  - best_times.json")
    print("  - best_options_now.json")
    print("  - park_status.json")
    print("  - park_calendar.json")
    print("="*90)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting.")
        sys.exit(0)
