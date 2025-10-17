# Disneyland Wait Time Analyzer

Analyze **real-time** Disneyland wait times against historical patterns to find the best times to visit rides.

**Data Sources:**
- Queue-Times.com - Historical patterns and real-time wait times
- TouringPlans.com - Ride durations and height requirements
- ThemeParkIQ.com - Park hours, parades, shows, and events

---

## Quick Start

### Simple (Recommended)

```bash
pip install -r requirements.txt
python run.py
```

This automatically collects data if needed, then runs the analyzer.

### Manual Steps

**Step 1: Collect Data (One Time)**
```bash
pip install -r requirements.txt
python scripts/disneyland_comprehensive_scraper.py
```

Collects data for 54 rides (~30-40 seconds):
- Historical wait time patterns
- Ride durations and height requirements
- Today's park calendar (hours, shows, events)

**Step 2: Run Analysis**
```bash
python scripts/predict_now.py
```

Compares **real-time** wait times against historical predictions.

---

## What You'll See

### Console Output

```
DISNEYLAND REAL-TIME WAIT TIME ANALYSIS
Current Time: Friday, October 17, 2025 at 03:27 PM

ACTUAL vs PREDICTED WAIT TIMES (35 rides currently open)
Rank   Ride                                   Actual     Predicted    Diff       Status
------------------------------------------------------------------------------------------
1      Tiana's Bayou Adventure                  70 min     56 min    +14 min    BUSY
2      Star Wars: Rise of the Resistance        70 min     67 min    +3 min     NORMAL
3      Roger Rabbit's Car Toon Spin             55 min     39 min    +16 min    BUSY
...

BEST OPTIONS RIGHT NOW (Shortest Actual Waits):
1  . Davy Crockett's Explorer Canoes           5 min (Predicted: 11)
2  . King Arthur Carrousel                     5 min (Predicted: 9)
...

POPULAR RIDES - BEST TIME TO VISIT ANALYSIS
Star Wars: Rise of the Resistance
  Current Actual Wait: 70 minutes
  Historical Average (this hour): 67 minutes

  Best Times to Visit (historically):
    22:00 - Average 48 min
    21:00 - Average 49 min
    08:00 - Average 59 min
```

### JSON Output Files

Six detailed reports generated in `output/`:

1. **`current_waits.json`** - Current wait times sorted by longest waits, includes ride durations and height requirements
2. **`ride_comparison.json`** - Actual vs predicted with crowd status (BUSIER/LIGHTER/NORMAL)
3. **`best_times.json`** - Best/worst times to visit popular rides (filtered by park hours)
4. **`best_options_now.json`** - Top 10 shortest current waits with total time (wait + duration)
5. **`park_status.json`** - Overall park crowd analysis with recommendations
6. **`park_calendar.json`** - Today's park hours, parades, shows, special events, and closures

---

## How It Works

### Prediction Algorithm

Weighted average calculation for current time:
- **Time of day**: 50% weight (most accurate)
- **Month**: 20% weight
- **Day of week**: 15% weight
- **Year trend**: 15% weight

### Real-Time Analysis

1. Fetches **actual** current wait times from Queue-Times.com API
2. Calculates **predicted** wait times using historical patterns
3. Compares actual vs predicted to determine crowd levels
4. Shows best/worst times to visit each ride

### Crowd Status

- **BUSIER_THAN_USUAL**: Actual wait is 10+ min above predicted
- **LIGHTER_THAN_USUAL**: Actual wait is 10+ min below predicted
- **NORMAL**: Within ±10 min of predicted

---

## Project Structure

```
├── run.py                              # Main entry point (orchestrates everything)
├── scripts/
│   ├── disneyland_comprehensive_scraper.py  # Data collector
│   └── predict_now.py                       # Real-time analyzer
├── data/                               # Persistent data (collected once)
│   ├── disneyland_ride_patterns.json   # Historical patterns by hour/day/month
│   ├── ride_durations.json             # Ride durations in minutes
│   ├── ride_height_requirements.json   # Height requirements in inches
│   └── park_calendar.json              # Daily calendar (hours, shows, events)
├── output/                             # Generated reports (updated each run)
│   ├── current_waits.json
│   ├── ride_comparison.json
│   ├── best_times.json
│   ├── best_options_now.json
│   ├── park_status.json
│   └── park_calendar.json
└── requirements.txt                    # Python dependencies
```

---

## Data Collection Details

### Queue-Times.com (54 Rides)
- Historical patterns by year, month, day-of-week, and hour
- Real-time wait times via API
- Park hours and special events

### TouringPlans.com (Pre-collected)
- Ride durations (42 rides)
- Height requirements (10 rides)
- Note: JavaScript-rendered, so uses hardcoded values

### ThemeParkIQ.com (Dynamic)
- Park operating hours (both parks)
- Parades and nighttime shows with times (filtered to upcoming only)
- Character meet and greet schedules with locations and times (filtered to upcoming only)
- Special events (Halloween Time, festivals, etc.)
- Temporarily closed attractions
- Note: Uses zendriver to handle JavaScript rendering
- **Time Filtering**: Only shows entertainment/character times that haven't passed yet (15-min buffer)

---

## Example JSON Output

### current_waits.json
```json
{
  "timestamp": "2025-10-17 15:34:20",
  "day_of_week": "Friday",
  "rides": [
    {
      "name": "Tiana's Bayou Adventure",
      "wait_time_minutes": 70,
      "ride_duration_minutes": 11,
      "total_time_minutes": 81,
      "height_requirement_inches": 40,
      "height_requirement": "3 ft 4 in",
      "status": "OPEN"
    }
  ]
}
```

### park_calendar.json
```json
{
  "date": "2025-10-17",
  "generated_at": "2025-10-17 15:34:20",
  "parks": {
    "Disneyland Park": {
      "hours": {
        "open": "08:00",
        "close": "23:00"
      },
      "parades": [
        {
          "name": "Paint the Night",
          "times": ["8:30pm", "10:30pm"]
        }
      ],
      "special_events": [
        {"name": "Halloween Time 2025"}
      ],
      "closed_attractions": []
    }
  },
  "character_meet_and_greets": [
    {
      "name": "Mickey Mouse",
      "location": "Town Square Theater",
      "times": ["9:00am", "10:30am", "2:00pm"]
    }
  ]
}
```

---

## Dependencies

```
requests>=2.31.0
beautifulsoup4>=4.12.0
zendriver>=0.14.0
```

**zendriver** - Used to fetch JavaScript-rendered content from ThemeParkIQ and bypass bot protection

---

## Re-collecting Data

### Update Historical Patterns (Monthly)
```bash
python scripts/disneyland_comprehensive_scraper.py
```

This refreshes:
- Ride wait time patterns (Queue-Times.com)
- Today's park calendar (ThemeParkIQ.com)

Run monthly to keep historical patterns current.

### Update Calendar Only (Daily)
The calendar automatically updates when you run the scraper. For most accurate park hours and show times, collect data on the day of your visit.

---

## Attribution & Rate Limiting

**Required Attribution:**
- Powered by Queue-Times.com (https://queue-times.com/en-US)
- TouringPlans.com for ride durations and height requirements
- ThemeParkIQ.com for park calendar and entertainment schedules

**Rate Limiting:**
- 0.5 second delay between ride pattern requests
- Be respectful of data sources' servers
- Don't run scraper more than once per hour

---

## Troubleshooting

### "ERROR: disneyland_ride_patterns.json not found!"

Run the data collector first:
```bash
python scripts/disneyland_comprehensive_scraper.py
```

### Predictions seem off

- Check your system time matches your timezone
- Re-run the data collector to update patterns
- Verify all files exist in `data/` folder

### Calendar data not showing

- Check if `zendriver` is installed: `pip install zendriver>=0.14.0`
- System falls back to default hours (8 AM - 11 PM) if scraping fails

---

## Technical Details

### Prediction Algorithm Implementation

```python
# predict_now.py:predict_for_current_time()
predictions = []
# Time of day (50% weight - doubled)
predictions.append(time_patterns[time_key]['avg'])
predictions.append(time_patterns[time_key]['avg'])
# Month (20% weight)
predictions.append(monthly_patterns[month]['value_1'])
# Day of week (15% weight)
predictions.append(day_patterns[day_of_week]['avg'])
# Return weighted average
return round(statistics.mean(predictions), 1)
```

### Park Hours Integration

System automatically filters "best times" recommendations to only show hours when park is open. Hours are scraped from ThemeParkIQ or default to 8 AM - 11 PM.

---

## Use Cases

- **Trip Planning**: See which rides have the shortest waits right now
- **Crowd Analysis**: Determine if current crowds are above/below normal
- **Optimal Timing**: Find the best hours to visit specific rides
- **Park Comparison**: See which attractions are busier than expected
- **Schedule Planning**: Know park hours and show times for today

---

## License & Legal

**Educational Use Only**

This tool is for educational purposes. Always verify wait times with official Disneyland sources before visiting.

**Data Attribution:**
All data is sourced from Queue-Times.com, TouringPlans.com, and ThemeParkIQ.com and is used in accordance with their terms of service.

---

## Support

**Requirements:**
- Python 3.7 or higher
- Internet connection for data collection

**Common Issues:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that `data/` folder contains all 4 JSON files
- Verify `output/` folder is created (auto-generated)

**Data Sources:**
- https://queue-times.com/en-US
- https://touringplans.com/disneyland
- https://themeparkiq.com/disneyland
