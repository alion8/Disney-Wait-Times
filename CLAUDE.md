# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Disneyland Wait Time Prediction System that analyzes real-time wait times against historical patterns to determine the best times to visit rides.

**Data Sources:**
- Queue-Times.com: Historical ride patterns and real-time wait times
- TouringPlans.com: Ride durations and height requirements (pre-collected data)
- ThemeParkIQ.com: Daily calendar (park hours, parades, nighttime shows, events, closures)

## Running the Application

### Main Entry Point
```bash
python run.py
```
This automatically handles data collection (if needed) and runs the analyzer.

### Manual Data Collection
```bash
python scripts/disneyland_comprehensive_scraper.py
```
Collects all data (~30-40 seconds):
- Ride patterns from Queue-Times.com (54 rides)
- Ride durations (42 rides, from pre-collected TouringPlans data)
- Height requirements (10 rides, from pre-collected TouringPlans data)
- Park calendar from ThemeParkIQ (hours for both parks, parades, fireworks, shows, events)

### Manual Analysis Only
```bash
python scripts/predict_now.py
```
Requires data files to exist first.

## Architecture

### Data Flow

1. **Data Collection** (`scripts/disneyland_comprehensive_scraper.py`)
   - Fetches ride list from Queue-Times.com API
   - Scrapes individual ride pages for historical patterns (by year, month, day-of-week, hour)
   - Uses hardcoded TouringPlans.com data for durations/heights (site uses JavaScript)
   - Fetches ThemeParkIQ calendar using zendriver (hours, parades, shows, events for both parks)
   - Saves to `data/` folder

2. **Real-Time Analysis** (`scripts/predict_now.py`)
   - Loads historical patterns from `data/`
   - Fetches current wait times from Queue-Times.com API
   - Compares actual vs predicted waits
   - Generates JSON reports in `output/` folder

3. **Orchestration** (`run.py`)
   - Checks for data files
   - Runs scraper if needed
   - Runs analyzer
   - Single command execution

### Folder Structure

```
data/           - Persistent data (patterns, durations, heights, daily calendar)
output/         - Generated reports (recreated each run)
scripts/        - Implementation scripts
```

### Prediction Algorithm

Weighted average calculation for current time:
- **Time of day**: 50% weight (doubled in calculation)
- **Month**: 20% weight
- **Day of week**: 15% weight
- **Year trend**: 15% weight

Implementation in `predict_now.py:predict_for_current_time()`:
```python
predictions = []
# Add time-of-day prediction twice (50% weight)
predictions.append(time_patterns[time_key]['avg'])
predictions.append(time_patterns[time_key]['avg'])
# Add month (20% weight)
predictions.append(monthly_patterns[month]['value_1'])
# Add day-of-week (15% weight)
predictions.append(day_patterns[day_of_week]['avg'])
# Return weighted average
return round(statistics.mean(predictions), 1)
```

### Park Hours Integration

System detects park operating hours (default 8 AM - 11 PM) to filter best time recommendations.

Implementation: `predict_now.py:get_park_hours()` attempts to scrape daily hours from Queue-Times.com calendar, falls back to defaults.

### JSON Output Structure

Six separate report types in `output/`:

1. **current_waits.json** - Sorted by wait time, includes duration + height
2. **ride_comparison.json** - Actual vs predicted with crowd status (BUSY/LIGHT/NORMAL)
3. **best_times.json** - Best/worst times for popular rides (filtered by park hours)
4. **best_options_now.json** - Top 10 shortest current waits
5. **park_status.json** - Overall park analysis with crowd level
6. **park_calendar.json** - Today's park hours, parades, shows, events, and closures

Each entry includes:
- Wait times (actual and/or predicted)
- Ride duration (when available)
- Height requirement in both inches and "X ft Y in" format
- Crowd status indicators

### Height Conversion

Heights stored as inches, displayed in US-friendly format:
```python
def _convert_inches_to_feet(self, inches):
    feet = inches // 12
    remaining_inches = inches % 12
    return f"{feet} ft {remaining_inches} in"  # e.g., "3 ft 10 in"
```

## Code Organization

### scripts/disneyland_comprehensive_scraper.py

**Class: DisneylandComprehensiveScraper**

Key methods:
- `get_all_rides()` - Fetches ride list from API
- `get_ride_historical_patterns(ride_id, ride_name)` - Scrapes individual ride page
- `_extract_table_by_position(soup, table_index)` - Extracts data from HTML tables
- `get_ride_durations()` - Returns hardcoded TouringPlans data
- `get_height_requirements()` - Returns hardcoded TouringPlans data
- `get_themeparkiq_calendar(date_str)` - Fetches ThemeParkIQ daily calendar using zendriver
- `get_character_schedules()` - Fetches character meet and greet schedules from separate page
- `_filter_upcoming_times(items, current_time)` - Filters events to only show upcoming times (excludes past shows)
- `_fetch_themeparkiq_async(url)` - Async method to fetch page with zendriver
- `_extract_themeparkiq_hours(soup, park_name)` - Extracts park operating hours
- `_extract_themeparkiq_entertainment(soup, section_name)` - Extracts parades/shows with times
- `_extract_themeparkiq_events(soup)` - Extracts current special events
- `_extract_themeparkiq_closures(soup, park_name)` - Extracts closed attractions

**Note on TouringPlans Data**: Duration and height data cannot be scraped (JavaScript-rendered), so uses pre-collected values hardcoded in the methods.

**Note on ThemeParkIQ Calendar**: Uses zendriver to fetch JavaScript-rendered content. Successfully extracts:
- Park hours for Disneyland Park and California Adventure
- Parades and nighttime entertainment with show times (filtered to show only upcoming)
- Character meet and greet schedules (separate page: /character/schedule, filtered to show only upcoming)
- Current special events (Halloween Time, festivals, etc.)
- Closed attractions

**Time Filtering**: All entertainment times are automatically filtered to show only upcoming shows/meets. Past times are excluded based on current system time (with 15-minute buffer for shows that are about to start).

Falls back to default hours if scraping fails. Updates daily when scraper runs.

### scripts/predict_now.py

**Class: DisneylandRealTimeAnalyzer**

Key methods:
- `get_real_time_waits()` - Fetches current waits from API
- `predict_for_current_time(ride_name)` - Calculates prediction using weighted algorithm
- `analyze_best_time_to_visit(ride_name)` - Finds best/worst hours (filtered by park hours)
- `get_park_hours()` - Scrapes or defaults park operating hours
- `export_json_reports(analysis, timestamp)` - Generates 5 separate JSON files

Auto-cleanup: Deletes old output JSONs before generating new ones.

### run.py

Orchestration script:
- Checks for `data/` files (patterns, durations, heights, calendar)
- Prompts user for data collection if missing
- Runs `scripts/disneyland_comprehensive_scraper.py` via subprocess
- Runs `scripts/predict_now.py` via subprocess
- Shows summary of generated files

## Data Attribution

**Required Attribution**:
- Powered by Queue-Times.com (https://queue-times.com/en-US)
- TouringPlans.com for ride durations and height requirements
- ThemeParkIQ.com for park calendar and entertainment schedules

**Rate Limiting**: 0.5 second delay between ride pattern requests (in scraper)

## Dependencies

```
requests>=2.31.0
beautifulsoup4>=4.12.0
zendriver>=0.14.0
```

**Note on zendriver**: Used to fetch JavaScript-rendered content from Disney's official calendar page, bypassing bot protection.

## Key Implementation Details

### Table Extraction by Position

Queue-Times.com ride pages have multiple tables without unique identifiers. The scraper uses positional indexing:
- Table 3: Day of week patterns
- Table 5: Hourly (time of day) patterns
- Table 6: Special events impact

### Crowd Status Calculation

In `predict_now.py:export_json_reports()`:
```python
if difference > 10:
    crowd_status = 'BUSIER_THAN_USUAL'
elif difference < -10:
    crowd_status = 'LIGHTER_THAN_USUAL'
else:
    crowd_status = 'NORMAL'
```

### Output File Cleanup

`predict_now.py:main()` deletes old JSON files before generation to prevent stale data.
