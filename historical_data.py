"""
Historical data management for VIX Term Structure Monitor.
Provides SQLite-based storage and retrieval of VIX analysis results with change tracking.
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import glob
import os
from scipy import stats


class VIXHistoricalData:
    """Manages historical VIX data storage and retrieval using SQLite."""
    
    def __init__(self, db_path: str = "outputs/vix_historical.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize SQLite database with proper schema."""
        # Ensure outputs directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Main VIX analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vix_historical (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL UNIQUE,
                    date_only TEXT NOT NULL,
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
                )
            ''')
            
            # Individual futures contracts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS futures_historical (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    days_to_expiration INTEGER NOT NULL,
                    expiration_date TEXT,
                    contract_order INTEGER,
                    FOREIGN KEY (timestamp) REFERENCES vix_historical(timestamp),
                    UNIQUE(timestamp, symbol)
                )
            ''')
            
            # Inversions tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inversions_historical (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    contract1 TEXT NOT NULL,
                    contract2 TEXT NOT NULL,
                    price1 REAL NOT NULL,
                    price2 REAL NOT NULL,
                    inversion_amount REAL NOT NULL,
                    inversion_type TEXT,
                    FOREIGN KEY (timestamp) REFERENCES vix_historical(timestamp)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vix_date ON vix_historical(date_only)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vix_timestamp ON vix_historical(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_futures_timestamp ON futures_historical(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_futures_symbol ON futures_historical(symbol)')
            
            conn.commit()
    
    def store_analysis(self, analysis_data: Dict, futures_data: pd.DataFrame) -> bool:
        """Store current analysis results in database."""
        try:
            timestamp = analysis_data['timestamp']
            date_only = timestamp[:10]  # Extract YYYY-MM-DD
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Extract data from analysis_data structure
                points_spreads = analysis_data.get('points_spreads', {})
                roll_carry = analysis_data.get('roll_carry', {})
                
                # Store main analysis data
                cursor.execute('''
                    INSERT OR REPLACE INTO vix_historical 
                    (timestamp, date_only, spot_vix, num_contracts, curve_shape, trading_signal,
                     roll_carry_pct, roll_carry_pts, synthetic_index, spot_to_front, front_to_second,
                     front_month_price, second_month_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, date_only, analysis_data['spot_vix'], analysis_data['num_contracts'],
                    analysis_data['curve_shape'], analysis_data['trading_signal'],
                    roll_carry.get('roll_pct', 0), roll_carry.get('roll_pts', 0),
                    roll_carry.get('synthetic_index', 0),
                    points_spreads.get('spot_to_front', 0), points_spreads.get('front_to_second', 0),
                    points_spreads.get('front_month', 0), points_spreads.get('second_month', 0)
                ))
                
                # Store futures contracts data
                cursor.execute('DELETE FROM futures_historical WHERE timestamp = ?', (timestamp,))
                
                for idx, (_, row) in enumerate(futures_data.iterrows()):
                    cursor.execute('''
                        INSERT INTO futures_historical 
                        (timestamp, symbol, price, days_to_expiration, expiration_date, contract_order)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp, row['symbol'], row['price'], row['days_to_expiration'],
                        str(row['expiration']) if 'expiration' in row else None, idx
                    ))
                
                # Store inversions data
                cursor.execute('DELETE FROM inversions_historical WHERE timestamp = ?', (timestamp,))
                
                inversions = analysis_data.get('inversions', [])
                for inversion in inversions:
                    cursor.execute('''
                        INSERT INTO inversions_historical 
                        (timestamp, contract1, contract2, price1, price2, inversion_amount, inversion_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp, inversion['contract1'], inversion['contract2'],
                        inversion['price1'], inversion['price2'], inversion['magnitude'],
                        inversion.get('type', 'unknown')
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Failed to store analysis data: {e}")
            return False
    
    def get_previous_day_data(self, target_date: str = None) -> Optional[Dict]:
        """Retrieve previous trading day's analysis data."""
        try:
            if target_date is None:
                target_date = datetime.now().strftime('%Y-%m-%d')
            
            # Convert to date object for calculations
            target_dt = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Look for previous trading days (up to 7 days back to handle weekends/holidays)
                for days_back in range(1, 8):
                    previous_date = target_dt - timedelta(days=days_back)
                    previous_date_str = previous_date.strftime('%Y-%m-%d')
                    
                    # Get main analysis data
                    cursor.execute('''
                        SELECT * FROM vix_historical 
                        WHERE date_only = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    ''', (previous_date_str,))
                    
                    main_data = cursor.fetchone()
                    if main_data:
                        # Convert to dict using column names
                        columns = [description[0] for description in cursor.description]
                        main_dict = dict(zip(columns, main_data))
                        
                        # Get futures data for this timestamp
                        cursor.execute('''
                            SELECT symbol, price, days_to_expiration, expiration_date, contract_order
                            FROM futures_historical 
                            WHERE timestamp = ?
                            ORDER BY contract_order
                        ''', (main_dict['timestamp'],))
                        
                        futures_rows = cursor.fetchall()
                        futures_data = []
                        for row in futures_rows:
                            futures_data.append({
                                'symbol': row[0],
                                'price': row[1],
                                'days_to_expiration': row[2],
                                'expiration': row[3],
                                'contract_order': row[4]
                            })
                        
                        # Get inversions data
                        cursor.execute('''
                            SELECT contract1, contract2, price1, price2, inversion_amount, inversion_type
                            FROM inversions_historical 
                            WHERE timestamp = ?
                        ''', (main_dict['timestamp'],))
                        
                        inversion_rows = cursor.fetchall()
                        inversions = []
                        for row in inversion_rows:
                            inversions.append({
                                'contract1': row[0],
                                'contract2': row[1],
                                'price1': row[2],
                                'price2': row[3],
                                'magnitude': row[4],
                                'type': row[5]
                            })
                        
                        return {
                            'main_data': main_dict,
                            'futures_data': futures_data,
                            'inversions': inversions,
                            'days_back': days_back
                        }
                
                return None
                
        except Exception as e:
            print(f"❌ Failed to retrieve previous day data: {e}")
            return None
    
    def calculate_changes(self, current_data: Dict, current_futures: pd.DataFrame, 
                         previous_data: Dict) -> Dict:
        """Calculate comprehensive changes between current and previous analysis."""
        try:
            if not previous_data:
                return {'has_previous_data': False, 'summary': 'No previous data available for comparison'}
            
            previous_main = previous_data['main_data']
            previous_futures = previous_data['futures_data']
            days_back = previous_data.get('days_back', 1)
            
            changes = {
                'has_previous_data': True,
                'days_since_previous': days_back,
                'previous_date': previous_main['date_only'],
                'spot_vix': self._calculate_numeric_change(
                    current_data['spot_vix'], previous_main['spot_vix']
                ),
                'curve_shape': {
                    'changed': current_data['curve_shape'] != previous_main['curve_shape'],
                    'from': previous_main['curve_shape'],
                    'to': current_data['curve_shape']
                },
                'trading_signal': {
                    'changed': current_data['trading_signal'] != previous_main['trading_signal'],
                    'from': previous_main['trading_signal'],
                    'to': current_data['trading_signal']
                },
                'roll_carry': self._calculate_numeric_change(
                    current_data.get('roll_carry', {}).get('roll_pct', 0),
                    previous_main['roll_carry_pct']
                ),
                'contracts': []
            }
            
            # Calculate contract-by-contract changes
            previous_contracts = {f['symbol']: f for f in previous_futures}
            
            for _, row in current_futures.iterrows():
                symbol = row['symbol']
                current_price = row['price']
                
                if symbol in previous_contracts:
                    previous_price = previous_contracts[symbol]['price']
                    contract_change = self._calculate_numeric_change(current_price, previous_price)
                    contract_change['symbol'] = symbol
                    contract_change['current_price'] = current_price
                    contract_change['previous_price'] = previous_price
                    changes['contracts'].append(contract_change)
            
            # Generate summary
            vix_change = changes['spot_vix']
            days_desc = "day" if days_back == 1 else f"{days_back} days"
            
            if vix_change['absolute'] == 0:
                summary = f"VIX unchanged at {current_data['spot_vix']:.2f} from {days_desc} ago"
            else:
                direction = "up" if vix_change['absolute'] > 0 else "down"
                summary = (f"VIX {direction} {abs(vix_change['absolute']):.2f} points "
                          f"({vix_change['percentage']:+.1f}%) from {days_desc} ago")
            
            # Add curve shape context
            if changes['curve_shape']['changed']:
                summary += f". Curve changed from {changes['curve_shape']['from']} to {changes['curve_shape']['to']}"
            else:
                summary += f". Curve remains in {current_data['curve_shape'].lower()}"
            
            changes['summary'] = summary
            
            return changes
            
        except Exception as e:
            print(f"❌ Failed to calculate changes: {e}")
            return {'has_previous_data': False, 'summary': f'Error calculating changes: {e}'}
    
    def _calculate_numeric_change(self, current: float, previous: float) -> Dict:
        """Calculate numeric change with absolute, percentage, and direction."""
        absolute_change = current - previous
        
        if previous != 0:
            percentage_change = (absolute_change / previous) * 100
        else:
            percentage_change = 0
        
        if absolute_change > 0:
            direction = "up"
        elif absolute_change < 0:
            direction = "down"
        else:
            direction = "unchanged"
        
        return {
            'absolute': round(absolute_change, 4),
            'percentage': round(percentage_change, 2),
            'direction': direction,
            'from': previous,
            'to': current
        }
    
    def get_date_range_data(self, start_date: str, end_date: str) -> List[Dict]:
        """Get historical data for specified date range."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY timestamp
                ''', (start_date, end_date))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            print(f"❌ Failed to retrieve date range data: {e}")
            return []
    
    def migrate_json_files(self, json_dir: str = "outputs/data") -> int:
        """Convert existing JSON files to database format."""
        migrated_count = 0
        
        if not Path(json_dir).exists():
            print(f"⚠️ JSON directory {json_dir} does not exist")
            return 0
        
        # Find all JSON analysis files
        json_pattern = f"{json_dir}/*_vix_*.json"
        json_files = glob.glob(json_pattern)
        
        print(f"🔄 Found {len(json_files)} JSON files to migrate")
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                # Skip if this is not a VIX analysis file
                if 'spot_vix' not in data or 'timestamp' not in data:
                    continue
                
                # Create empty futures DataFrame for files without futures data
                futures_df = pd.DataFrame()
                
                # Try to extract futures data from various possible locations
                if 'futures_data' in data and isinstance(data['futures_data'], list):
                    futures_df = pd.DataFrame(data['futures_data'])
                elif 'contracts' in data and isinstance(data['contracts'], list):
                    futures_df = pd.DataFrame(data['contracts'])
                
                # Store in database
                success = self.store_analysis(data, futures_df)
                if success:
                    migrated_count += 1
                    print(f"✅ Migrated: {os.path.basename(json_file)}")
                else:
                    print(f"❌ Failed to migrate: {os.path.basename(json_file)}")
                    
            except Exception as e:
                print(f"❌ Error migrating {os.path.basename(json_file)}: {e}")
                continue
        
        print(f"🎉 Migration complete: {migrated_count}/{len(json_files)} files migrated")
        return migrated_count
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the database contents."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count records in each table
                cursor.execute('SELECT COUNT(*) FROM vix_historical')
                main_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM futures_historical')
                futures_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM inversions_historical')
                inversions_count = cursor.fetchone()[0]
                
                # Get date range
                cursor.execute('SELECT MIN(date_only), MAX(date_only) FROM vix_historical')
                date_range = cursor.fetchone()
                
                # Get recent records
                cursor.execute('''
                    SELECT date_only, spot_vix, curve_shape 
                    FROM vix_historical 
                    ORDER BY timestamp DESC 
                    LIMIT 5
                ''')
                recent_records = cursor.fetchall()
                
                return {
                    'record_counts': {
                        'main_analyses': main_count,
                        'futures_contracts': futures_count,
                        'inversions': inversions_count
                    },
                    'date_range': {
                        'earliest': date_range[0],
                        'latest': date_range[1]
                    },
                    'recent_records': [
                        {'date': r[0], 'spot_vix': r[1], 'curve_shape': r[2]}
                        for r in recent_records
                    ]
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def calculate_statistical_context(self, current_values: Dict, lookback_days: int = 252) -> Dict:
        """
        Calculate statistical context for current values compared to historical data.
        
        Args:
            current_values: Dict with keys like 'spot_vix', 'roll_carry_pct', 'contango_pct'
            lookback_days: Number of days to look back for historical comparison (default 252 = 1 year)
            
        Returns:
            Dict with percentiles, z-scores, min/max, averages for each metric
        """
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                # Get historical data for the lookback period
                query = '''
                    SELECT date_only, spot_vix, roll_carry_pct, spot_to_front, front_to_second,
                           curve_shape, trading_signal
                    FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY timestamp
                '''
                df = pd.read_sql_query(query, conn, params=(start_date, end_date))
                
                if df.empty:
                    return {'error': 'No historical data available for statistical analysis'}
                
                # Calculate contango percentage (spot to front spread as % of spot)
                df['contango_pct'] = (df['spot_to_front'] / df['spot_vix']) * 100
                
                # Initialize results
                statistical_context = {}
                
                # Metrics to analyze
                metrics = {
                    'spot_vix': current_values.get('spot_vix'),
                    'roll_carry_pct': current_values.get('roll_carry_pct'),
                    'contango_pct': current_values.get('contango_pct'),
                    'spot_to_front': current_values.get('spot_to_front'),
                    'front_to_second': current_values.get('front_to_second')
                }
                
                for metric_name, current_value in metrics.items():
                    if current_value is None or metric_name not in df.columns:
                        continue
                    
                    # Get historical values
                    historical = df[metric_name].dropna()
                    
                    if len(historical) < 20:  # Need minimum data points
                        continue
                    
                    # Calculate statistics
                    mean = historical.mean()
                    std = historical.std()
                    
                    # Calculate percentile rank
                    percentile = stats.percentileofscore(historical, current_value, kind='mean')
                    
                    # Calculate z-score
                    z_score = (current_value - mean) / std if std > 0 else 0
                    
                    # Find min/max
                    hist_min = historical.min()
                    hist_max = historical.max()
                    
                    # Calculate moving averages
                    ma_30 = historical.tail(30).mean() if len(historical) >= 30 else mean
                    ma_60 = historical.tail(60).mean() if len(historical) >= 60 else mean
                    
                    # Determine regime (high/normal/low)
                    if percentile >= 80:
                        regime = "High"
                    elif percentile <= 20:
                        regime = "Low"
                    else:
                        regime = "Normal"
                    
                    # Store results
                    statistical_context[metric_name] = {
                        'current': round(current_value, 2),
                        'percentile': round(percentile, 1),
                        'z_score': round(z_score, 2),
                        'mean': round(mean, 2),
                        'std_dev': round(std, 2),
                        'min': round(hist_min, 2),
                        'max': round(hist_max, 2),
                        'ma_30': round(ma_30, 2),
                        'ma_60': round(ma_60, 2),
                        'regime': regime,
                        'samples': len(historical)
                    }
                
                # Add curve shape distribution
                if 'curve_shape' in df.columns:
                    shape_counts = df['curve_shape'].value_counts()
                    total_counts = shape_counts.sum()
                    shape_distribution = {
                        shape: round((count / total_counts) * 100, 1)
                        for shape, count in shape_counts.items()
                    }
                    statistical_context['curve_shape_distribution'] = shape_distribution
                    statistical_context['current_curve_shape'] = current_values.get('curve_shape')
                
                # Add lookback period info
                statistical_context['lookback_days'] = lookback_days
                statistical_context['data_points'] = len(df)
                statistical_context['date_range'] = {
                    'start': df.iloc[0]['date_only'] if not df.empty else start_date,
                    'end': df.iloc[-1]['date_only'] if not df.empty else end_date
                }
                
                return statistical_context
                
        except Exception as e:
            print(f"❌ Failed to calculate statistical context: {e}")
            return {'error': str(e)}
    
    def get_percentile_rankings(self, current_values: Dict, periods: List[int] = [30, 90, 252]) -> Dict:
        """
        Calculate percentile rankings for multiple time periods.
        
        Args:
            current_values: Current metric values
            periods: List of lookback periods in days
            
        Returns:
            Dict with percentile rankings for each period
        """
        rankings = {}
        
        for days in periods:
            period_label = self._get_period_label(days)
            context = self.calculate_statistical_context(current_values, lookback_days=days)
            
            if 'error' not in context:
                rankings[period_label] = {
                    metric: {
                        'percentile': data['percentile'],
                        'regime': data['regime']
                    }
                    for metric, data in context.items()
                    if isinstance(data, dict) and 'percentile' in data
                }
        
        return rankings
    
    def _get_period_label(self, days: int) -> str:
        """Convert days to human-readable period label."""
        if days <= 30:
            return "1_month"
        elif days <= 90:
            return "3_months"
        elif days <= 180:
            return "6_months"
        elif days <= 365:
            return "1_year"
        else:
            return f"{days}_days"
    
    def get_extreme_values(self, lookback_days: int = 252) -> Dict:
        """
        Get extreme values (records) from historical data.
        
        Returns:
            Dict with record highs/lows and when they occurred
        """
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get extreme VIX values
                cursor.execute('''
                    SELECT date_only, spot_vix 
                    FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY spot_vix DESC
                    LIMIT 1
                ''', (start_date, end_date))
                max_vix = cursor.fetchone()
                
                cursor.execute('''
                    SELECT date_only, spot_vix 
                    FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY spot_vix ASC
                    LIMIT 1
                ''', (start_date, end_date))
                min_vix = cursor.fetchone()
                
                # Get extreme roll carry
                cursor.execute('''
                    SELECT date_only, roll_carry_pct 
                    FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY roll_carry_pct DESC
                    LIMIT 1
                ''', (start_date, end_date))
                max_carry = cursor.fetchone()
                
                cursor.execute('''
                    SELECT date_only, roll_carry_pct 
                    FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY roll_carry_pct ASC
                    LIMIT 1
                ''', (start_date, end_date))
                min_carry = cursor.fetchone()
                
                # Get extreme contango
                cursor.execute('''
                    SELECT date_only, spot_to_front 
                    FROM vix_historical 
                    WHERE date_only BETWEEN ? AND ?
                    ORDER BY spot_to_front DESC
                    LIMIT 1
                ''', (start_date, end_date))
                max_contango = cursor.fetchone()
                
                return {
                    'vix': {
                        'highest': {'value': max_vix[1], 'date': max_vix[0]} if max_vix else None,
                        'lowest': {'value': min_vix[1], 'date': min_vix[0]} if min_vix else None
                    },
                    'roll_carry': {
                        'highest': {'value': max_carry[1], 'date': max_carry[0]} if max_carry else None,
                        'lowest': {'value': min_carry[1], 'date': min_carry[0]} if min_carry else None
                    },
                    'contango': {
                        'highest': {'value': max_contango[1], 'date': max_contango[0]} if max_contango else None
                    },
                    'lookback_days': lookback_days
                }
                
        except Exception as e:
            print(f"❌ Failed to get extreme values: {e}")
            return {'error': str(e)}


# Global instance for easy access
historical_data = VIXHistoricalData()


def initialize_historical_data() -> VIXHistoricalData:
    """Initialize and return historical data manager."""
    return historical_data


if __name__ == "__main__":
    # Test the historical data system
    print("=== VIX Historical Data System Test ===")
    
    hd = VIXHistoricalData()
    
    # Show database stats
    stats = hd.get_database_stats()
    print("\n📊 Database Statistics:")
    print(f"  Main analyses: {stats.get('record_counts', {}).get('main_analyses', 0)}")
    print(f"  Futures contracts: {stats.get('record_counts', {}).get('futures_contracts', 0)}")
    print(f"  Inversions: {stats.get('record_counts', {}).get('inversions', 0)}")
    
    if stats.get('date_range', {}).get('earliest'):
        print(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    
    # Try migration if no data exists
    if stats.get('record_counts', {}).get('main_analyses', 0) == 0:
        print("\n🔄 No data found, attempting migration...")
        migrated = hd.migrate_json_files()
        print(f"✅ Migrated {migrated} records")
    
    # Test previous day lookup
    print("\n🔍 Testing previous day lookup...")
    previous = hd.get_previous_day_data()
    if previous:
        print(f"✅ Found previous data from {previous['days_back']} days ago")
        print(f"  Date: {previous['main_data']['date_only']}")
        print(f"  VIX: {previous['main_data']['spot_vix']}")
    else:
        print("❌ No previous data found")