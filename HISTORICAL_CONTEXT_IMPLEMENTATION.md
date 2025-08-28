# Historical Context Integration Plan

## **Project Overview**
This document outlines the comprehensive plan for integrating historical context into the VIX Term Structure Monitor. The primary goal is to enhance the daily analysis by comparing current market conditions with previous day's data, providing users with immediate context for market movements and trend identification.

## **Current System Analysis**

### **Existing Data Storage**
- **Timestamped JSON files**: `outputs/data/YYYY-MM-DD_HHMMSS_vix_analysis.json`
- **File structure**: Organized analysis results with spot VIX, futures data, roll carry
- **Output management**: `file_manager.py` handles paths and cleanup
- **No persistence**: Each run is independent, no historical lookback

### **Current JSON Schema**
```json
{
  "timestamp": "2025-07-27T18:45:25.339855",
  "spot_vix": 14.93,
  "num_contracts": 9,
  "points_spreads": {
    "spot_to_front": 2.95,
    "front_to_second": 1.9,
    "spot_vix": 14.93,
    "front_month": 17.8844,
    "second_month": 19.7887
  },
  "roll_carry": {
    "roll_pts": -0.068,
    "synthetic_index": 18.29,
    "roll_pct": -0.37,
    "dt": 1,
    "contracts_used": "VX/Q5 to VX/U5"
  },
  "inversions": [],
  "curve_shape": "Steep Contango",
  "trading_signal": "Strong Contango - Consider Short Vol"
}
```

## **Phase 1: Historical Data Storage (Foundation)**

### **1.1 SQLite Database Schema**
Create persistent storage for historical analysis data:

```sql
-- Main VIX analysis table
CREATE TABLE vix_historical (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL UNIQUE,
    date_only TEXT NOT NULL,  -- For easy daily lookups (YYYY-MM-DD)
    spot_vix REAL NOT NULL,
    num_contracts INTEGER,
    curve_shape TEXT,
    trading_signal TEXT,
    roll_carry_pct REAL,
    roll_carry_pts REAL,
    synthetic_index REAL,
    spot_to_front REAL,
    front_to_second REAL,
    front_month_price REAL,
    second_month_price REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Individual futures contracts table
CREATE TABLE futures_historical (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price REAL NOT NULL,
    days_to_expiration INTEGER NOT NULL,
    expiration_date TEXT,
    contract_order INTEGER,  -- 0=front month, 1=second month, etc.
    FOREIGN KEY (timestamp) REFERENCES vix_historical(timestamp),
    UNIQUE(timestamp, symbol)
);

-- Inversions tracking table  
CREATE TABLE inversions_historical (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    contract1 TEXT NOT NULL,
    contract2 TEXT NOT NULL,
    inversion_amount REAL,
    FOREIGN KEY (timestamp) REFERENCES vix_historical(timestamp)
);

-- Indexes for performance
CREATE INDEX idx_vix_date ON vix_historical(date_only);
CREATE INDEX idx_vix_timestamp ON vix_historical(timestamp);
CREATE INDEX idx_futures_timestamp ON futures_historical(timestamp);
CREATE INDEX idx_futures_symbol ON futures_historical(symbol);
```

### **1.2 New Module: historical_data.py**
Create comprehensive database operations module:

```python
class VIXHistoricalData:
    """Manages historical VIX data storage and retrieval."""
    
    def __init__(self, db_path="outputs/vix_historical.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with proper schema."""
        
    def store_analysis(self, analysis_data: dict, futures_data: pd.DataFrame):
        """Store current analysis results in database."""
        
    def get_previous_day_data(self, target_date: str = None):
        """Retrieve previous trading day's analysis data."""
        
    def get_date_range_data(self, start_date: str, end_date: str):
        """Get historical data for specified date range."""
        
    def calculate_changes(self, current_data: dict, previous_data: dict):
        """Calculate all relevant changes between two analysis periods."""
        
    def migrate_json_files(self, json_dir: str):
        """Convert existing JSON files to database format."""
```

### **1.3 Data Migration Strategy**
- **Automatic migration**: Scan `outputs/data/` for existing JSON files
- **Date extraction**: Parse timestamps from filenames and content
- **Data validation**: Ensure data integrity during migration
- **Preserve originals**: Keep JSON files as backup during transition
- **One-time process**: Migration runs on first database initialization

## **Phase 2: Previous Day Comparison**

### **2.1 Enhanced Analysis Schema**
Extend the current analysis output to include historical context:

```json
{
  "timestamp": "2025-07-28T16:45:00.000000",
  "current": {
    // Existing analysis structure
    "spot_vix": 15.38,
    "curve_shape": "Steep Contango",
    "trading_signal": "Strong Contango - Consider Short Vol",
    "roll_carry": {"roll_pct": -0.42}
  },
  "previous": {
    // Previous day's data (null if not available)
    "date": "2025-07-27",
    "spot_vix": 14.93,
    "curve_shape": "Steep Contango", 
    "trading_signal": "Strong Contango - Consider Short Vol",
    "roll_carry": {"roll_pct": -0.37}
  },
  "changes": {
    "spot_vix": {
      "absolute": 0.45,
      "percentage": 3.01,
      "direction": "up"
    },
    "curve_shape": {
      "changed": false,
      "from": "Steep Contango",
      "to": "Steep Contango"
    },
    "trading_signal": {
      "changed": false,
      "from": "Strong Contango - Consider Short Vol",
      "to": "Strong Contango - Consider Short Vol"
    },
    "roll_carry": {
      "absolute": -0.05,
      "from": -0.37,
      "to": -0.42,
      "direction": "more_negative"
    },
    "contracts": [
      {
        "symbol": "VX/Q5",
        "current_price": 17.88,
        "previous_price": 17.65,
        "absolute_change": 0.23,
        "percentage_change": 1.30,
        "direction": "up"
      }
      // ... other contracts
    ],
    "summary": "VIX up 0.45 points (+3.0%) from previous day. Curve remains in steep contango."
  },
  "days_since_previous": 1,  // Handle weekends/holidays
  "has_previous_data": true
}
```

### **2.2 Change Calculation Logic**
- **Smart date handling**: Account for weekends and market holidays
- **Robust comparison**: Handle missing previous data gracefully
- **Comprehensive metrics**: Track all relevant changes (prices, signals, structure)
- **Direction indicators**: Clear up/down/unchanged classifications
- **Summary generation**: Human-readable change descriptions

## **Phase 3: Visualization Enhancements**

### **3.1 Historical Overlay on Main Chart**
Transform the current single-curve visualization:

**Before**: Single blue line showing current term structure
**After**: 
- **Current curve**: Bold blue line (primary focus)
- **Previous curve**: Dotted gray line overlay
- **Change indicators**: Green/red arrows at each contract point
- **Enhanced legend**: "Current (Today)" vs "Previous (Jul 27)"

### **3.2 Change Display Grid**
Add tabular comparison below the main chart:

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY CHANGES                            │
├─────────┬─────────┬─────────┬─────────┬──────────┬─────────┤
│Contract │ Current │Previous │  Change │    %     │   Trend │
├─────────┼─────────┼─────────┼─────────┼──────────┼─────────┤
│VX/Q5    │  17.88  │  17.65  │  +0.23  │  +1.3%   │    ↗    │
│VX/U5    │  19.79  │  19.45  │  +0.34  │  +1.7%   │    ↗    │
│VX/Z5    │  21.12  │  20.88  │  +0.24  │  +1.1%   │    ↗    │
│         │         │         │         │          │         │
│Spot VIX │  15.38  │  14.93  │  +0.45  │  +3.0%   │    ↗    │
└─────────┴─────────┴─────────┴─────────┴──────────┴─────────┘
```

### **3.3 Enhanced Dashboard Layout**
Reorganize the visual hierarchy:

1. **Header Section**: 
   - Large spot VIX with prominent change indicator
   - Date range: "Jul 28 vs Jul 27"
   - Market status with change context

2. **Main Chart Section**:
   - Term structure with historical overlay
   - Enhanced dual-axis (days + dates)
   - Change indicators at each point

3. **Analysis Section**:
   - Roll carry evolution
   - Trading signal changes
   - Curve shape progression

4. **Change Summary Section**:
   - Tabular contract changes
   - Key metric evolution
   - Summary narrative

## **Phase 4: Implementation Roadmap**

### **Week 1: Database Foundation (Priority 1)**
**Files to create/modify:**
- `historical_data.py` - New SQLite operations module
- `term_structure.py` - Add database storage after analysis
- `main.py` - Initialize database and historical context
- `requirements.txt` - Ensure sqlite3 availability (built-in Python)

**Deliverables:**
- Working SQLite database with schema
- Automatic data storage after each analysis run
- Migration utility for existing JSON files
- Database initialization in main pipeline

### **Week 2: Change Calculation Engine (Priority 2)**
**Files to modify:**
- `term_structure.py` - Enhance TermStructureAnalyzer with historical methods
- `historical_data.py` - Add change calculation functions
- `main.py` - Integrate historical comparison in analysis flow

**Deliverables:**
- Previous day data retrieval functionality
- Comprehensive change calculation logic
- Enhanced JSON output with historical context
- Robust weekend/holiday handling

### **Week 3: Visualization Enhancement (Priority 3)**
**Files to modify:**
- `visualizer.py` - Add historical overlay and change indicators
- `visualizer.py` - Create change summary table
- `email_sender.py` - Update email template for historical context

**Deliverables:**
- Term structure chart with previous day overlay
- Change indicators and improved legend
- Tabular change display below main chart
- Enhanced email template highlighting changes

### **Week 4: Integration & Testing (Priority 4)**
**Files to test/refine:**
- Full pipeline integration testing
- GitHub Actions workflow with database persistence
- Email delivery with enhanced historical content
- Error handling for missing historical data

**Deliverables:**
- Fully integrated historical context system
- Automated GitHub Actions deployment
- Enhanced daily email reports
- Complete documentation and usage examples

## **Technical Implementation Details**

### **Database Strategy**
- **SQLite choice**: Lightweight, serverless, perfect for GitHub Actions
- **Artifact persistence**: Database file saved in GitHub Actions artifacts
- **Local development**: Database persists across runs locally
- **Migration safety**: Preserve existing JSON workflow during transition

### **Performance Considerations**
- **Efficient queries**: Indexed database access for previous day lookups
- **Minimal overhead**: Historical context adds <1 second to analysis time
- **Memory usage**: Small database size (years of data < 10MB)
- **Caching strategy**: Recent data cached in memory for performance

### **Error Handling**
- **Missing data**: Graceful degradation when previous data unavailable
- **Database errors**: Fallback to JSON-only mode if database fails
- **Date handling**: Smart weekend/holiday detection for "previous day"
- **Data validation**: Ensure data consistency and format compliance

### **GitHub Actions Integration**
```yaml
# Add to daily-vix-monitor.yml
- name: Restore historical database
  uses: actions/download-artifact@v4
  with:
    name: vix-historical-db
    path: outputs/
  continue-on-error: true

# After analysis completes
- name: Archive historical database
  uses: actions/upload-artifact@v4
  with:
    name: vix-historical-db
    path: outputs/vix_historical.db
    retention-days: 90
```

## **Expected User Experience Improvements**

### **Enhanced Email Subject Lines**
- **Before**: "VIX Term Structure Analysis - Jul 28, 2025"
- **After**: "VIX 15.38 (+0.45, +3.0%) - Steep Contango Continues - Jul 28"

### **Contextual Insights**
- "VIX jumped 0.45 points from yesterday's 14.93"
- "Term structure remains in steep contango (+3 days running)"
- "Roll carry deteriorated from -0.37% to -0.42%"
- "All contracts moved higher, led by front month (+1.3%)"

### **Visual Improvements**
- **Immediate context**: See yesterday's curve overlaid on today's
- **Change magnitude**: Visual arrows indicate direction and size
- **Trend identification**: Multi-day patterns become visible
- **Professional appearance**: Cleaner, more informative charts

## **Future Extension Opportunities**

### **Multi-Day History (Phase 5+)**
- **Weekly overlays**: Show 5-day term structure evolution
- **Trend analysis**: Identify multi-day directional moves
- **Volatility patterns**: Track curve shape changes over time

### **Statistical Context (Phase 6+)**
- **Z-scores**: "Current contango 2.3σ above 30-day average"
- **Percentile rankings**: "Roll carry in 95th percentile this month"
- **Regime detection**: Identify structural market shifts

### **Advanced Visualizations (Phase 7+)**
- **Interactive charts**: HTML/JavaScript for web viewing
- **Heatmaps**: Term structure evolution over multiple days
- **Statistical overlays**: Confidence bands and distribution plots

## **Success Metrics**

### **Technical Success**
- ✅ Database initialization and migration complete
- ✅ Previous day comparison working reliably  
- ✅ Enhanced visualizations rendering correctly
- ✅ GitHub Actions integration stable
- ✅ Email delivery with historical context

### **User Experience Success**
- ✅ Immediate context: Users see change magnitude at a glance
- ✅ Trend awareness: Multi-day patterns become visible
- ✅ Professional quality: Charts suitable for sharing/presentation
- ✅ Reliable delivery: Daily emails with consistent historical context

### **System Performance**
- ✅ Analysis time increase: <1 second overhead
- ✅ Database size: Manageable growth (~1MB per year)
- ✅ GitHub Actions: Reliable artifact persistence
- ✅ Error handling: Graceful degradation when historical data missing

---

## **Development Notes**

### **Key Files to Modify**
1. **`historical_data.py`** - New module (create)
2. **`term_structure.py`** - Add historical analysis methods
3. **`visualizer.py`** - Enhanced charts with overlay
4. **`main.py`** - Integrate historical context flow
5. **`email_sender.py`** - Update template for changes
6. **`file_manager.py`** - Add database path management

### **Testing Strategy**
- **Unit tests**: Database operations and change calculations
- **Integration tests**: Full pipeline with fake historical data
- **Visual tests**: Chart generation with sample overlays
- **Email tests**: Template rendering with historical context

### **Rollback Strategy**
- **Feature flags**: Ability to disable historical context
- **JSON fallback**: Maintain existing JSON workflow
- **Database optional**: System works without database
- **Gradual rollout**: Phase-by-phase deployment

This plan provides a comprehensive roadmap for adding meaningful historical context to the VIX Term Structure Monitor while maintaining system reliability and enhancing user experience.