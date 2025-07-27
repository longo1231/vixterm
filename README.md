# VIX Term Structure Monitor

## Project Goal
Build a Python tool that monitors the VIX futures term structure, identifying trading opportunities when the curve shape changes.

## Requirements
1. Scrape VIX futures prices from CBOE's website
2. Calculate days to expiration for each contract
3. Plot the term structure curve
4. Calculate key metrics:
   - Contango/backwardation percentage
   - Term structure slope
   - Identify inversions
5. Simple alert when curve inverts

## Technical Constraints
- Use Python with standard data science libraries
- Handle CBOE's JavaScript-rendered pages (will need Selenium or similar)
- Create clear visualizations suitable for daily monitoring
- Error handling for weekends/holidays when data might be stale

## Data Notes
- VIX futures expire on Wednesdays
- Symbols follow pattern: VX + month code + year
- Need both spot VIX and futures prices
- CBOE provides 15-minute delayed data

## Success Criteria
A working script that can be run daily to show:
1. Current term structure shape
2. Whether we're in contango or backwardation
3. Any unusual inversions that might signal opportunities

## Development Approach
Start with fake data to test visualization, then add real CBOE scraping
