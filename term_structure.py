"""
VIX term structure analysis and calculations with historical context.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class TermStructureAnalyzer:
    """Analyzes VIX futures term structure for trading signals with historical context."""
    
    def __init__(self, spot_vix: float, futures_data: pd.DataFrame, enable_historical: bool = True):
        self.spot_vix = spot_vix
        self.futures_data = futures_data.copy()
        self.enable_historical = enable_historical
        self.historical_data = None
        
        if enable_historical:
            try:
                from historical_data import historical_data
                self.historical_data = historical_data
            except ImportError:
                print("⚠️ Historical data module not available, continuing without historical context")
                self.enable_historical = False
        
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare and sort futures data by expiration."""
        if not self.futures_data.empty:
            self.futures_data = self.futures_data.sort_values('days_to_expiration')
            self.futures_data = self.futures_data.reset_index(drop=True)
    
    def calculate_points_spreads(self) -> Dict[str, float]:
        """Calculate point spreads between contracts."""
        if self.futures_data.empty:
            return {'spot_to_front': 0.0, 'front_to_second': 0.0}
        
        front_month_price = self.futures_data.iloc[0]['price']
        spot_to_front = round(front_month_price - self.spot_vix, 2)
        
        front_to_second = 0.0
        if len(self.futures_data) >= 2:
            second_month_price = self.futures_data.iloc[1]['price']
            front_to_second = round(second_month_price - front_month_price, 2)
        
        return {
            'spot_to_front': spot_to_front,
            'front_to_second': front_to_second,
            'spot_vix': self.spot_vix,
            'front_month': front_month_price,
            'second_month': self.futures_data.iloc[1]['price'] if len(self.futures_data) >= 2 else None
        }
    
    def calculate_roll_carry(self, dt: int = 1) -> Dict[str, float]:
        """Calculate roll carry using VIX methodology."""
        if len(self.futures_data) < 2:
            return {'roll_pts': 0.0, 'synthetic_index': 0.0, 'roll_pct': 0.0}
        
        # Variables
        F1 = self.futures_data.iloc[0]['price']  # Front future
        F2 = self.futures_data.iloc[1]['price']  # Second future  
        T1 = self.futures_data.iloc[0]['days_to_expiration']  # Days to F1 expiry
        T2 = self.futures_data.iloc[1]['days_to_expiration']  # Days to F2 expiry
        
        if T2 - T1 == 0:
            return {'roll_pts': 0.0, 'synthetic_index': 0.0, 'roll_pct': 0.0}
        
        # Roll carry in points (per rebalance interval)
        roll_pts = -(dt / (T2 - T1)) * (F2 - F1)
        
        # Synthetic 30-day index level
        I = ((T2 - 30) / (T2 - T1)) * F1 + ((30 - T1) / (T2 - T1)) * F2
        
        # Roll carry as a percent of the index
        roll_pct = (roll_pts / I) * 100 if I != 0 else 0.0
        
        return {
            'roll_pts': round(roll_pts, 4),
            'synthetic_index': round(I, 2),
            'roll_pct': round(roll_pct, 2),
            'dt': dt,
            'contracts_used': f"{self.futures_data.iloc[0]['symbol']} to {self.futures_data.iloc[1]['symbol']}"
        }
    
    def detect_inversions(self) -> List[Dict]:
        """Detect inversions in the term structure."""
        inversions = []
        
        if len(self.futures_data) < 2:
            return inversions
        
        for i in range(len(self.futures_data) - 1):
            current = self.futures_data.iloc[i]
            next_contract = self.futures_data.iloc[i + 1]
            
            if current['price'] > next_contract['price']:
                inversion = {
                    'type': 'futures_inversion',
                    'contract1': current['symbol'],
                    'contract2': next_contract['symbol'],
                    'price1': current['price'],
                    'price2': next_contract['price'],
                    'magnitude': round(current['price'] - next_contract['price'], 2)
                }
                inversions.append(inversion)
        
        # Check spot vs front month inversion
        if not self.futures_data.empty:
            front_month = self.futures_data.iloc[0]
            if self.spot_vix > front_month['price']:
                inversions.append({
                    'type': 'spot_inversion',
                    'contract1': 'VIX Spot',
                    'contract2': front_month['symbol'],
                    'price1': self.spot_vix,
                    'price2': front_month['price'],
                    'magnitude': round(self.spot_vix - front_month['price'], 2)
                })
        
        return inversions
    
    def get_term_structure_summary(self, include_historical: bool = None) -> Dict:
        """Get comprehensive term structure analysis with optional historical context."""
        if include_historical is None:
            include_historical = self.enable_historical
            
        points_info = self.calculate_points_spreads()
        roll_carry_info = self.calculate_roll_carry()
        inversions = self.detect_inversions()
        
        base_analysis = {
            'timestamp': datetime.now().isoformat(),
            'spot_vix': self.spot_vix,
            'num_contracts': len(self.futures_data),
            'points_spreads': points_info,
            'roll_carry': roll_carry_info,
            'inversions': inversions,
            'curve_shape': self._classify_curve_shape(),
            'trading_signal': self._generate_signal()
        }
        
        # Add historical context if enabled and available
        if include_historical and self.historical_data:
            try:
                # Store current analysis first
                self.historical_data.store_analysis(base_analysis, self.futures_data)
                
                # Get historical context
                historical_context = self.get_historical_context()
                if historical_context:
                    base_analysis.update(historical_context)
                    
            except Exception as e:
                print(f"⚠️ Historical context failed: {e}")
                base_analysis['historical_error'] = str(e)
        
        return base_analysis
    
    def _classify_curve_shape(self) -> str:
        """Classify the overall shape of the term structure."""
        if len(self.futures_data) < 3:
            return 'Insufficient data'
        
        slopes = []
        for i in range(len(self.futures_data) - 1):
            curr = self.futures_data.iloc[i]['price']
            next_price = self.futures_data.iloc[i + 1]['price']
            slopes.append(next_price - curr)
        
        if all(s > 0 for s in slopes):
            return 'Steep Contango'
        elif all(s < 0 for s in slopes):
            return 'Steep Backwardation'
        elif sum(s > 0 for s in slopes) > len(slopes) / 2:
            return 'Mild Contango'
        elif sum(s < 0 for s in slopes) > len(slopes) / 2:
            return 'Mild Backwardation'
        else:
            return 'Mixed/Kinked'
    
    def _generate_signal(self) -> str:
        """Generate simple trading signal based on structure."""
        points_info = self.calculate_points_spreads()
        inversions = self.detect_inversions()
        
        if inversions:
            return 'ALERT: Curve Inversion Detected'
        elif points_info['spot_to_front'] > 2:
            return 'Strong Contango - Consider Short Vol'
        elif points_info['spot_to_front'] < -2:
            return 'Strong Backwardation - Consider Long Vol'
        else:
            return 'Neutral Structure'
    
    def get_historical_context(self) -> Optional[Dict]:
        """Get historical context by comparing with previous day's data."""
        if not self.historical_data:
            return None
            
        try:
            # Get previous day's data
            previous_data = self.historical_data.get_previous_day_data()
            if not previous_data:
                return {
                    'has_previous_data': False,
                    'changes': {'summary': 'No previous data available for comparison'}
                }
            
            # Calculate changes
            current_analysis = {
                'spot_vix': self.spot_vix,
                'curve_shape': self._classify_curve_shape(),
                'trading_signal': self._generate_signal(),
                'roll_carry': self.calculate_roll_carry()
            }
            
            changes = self.historical_data.calculate_changes(
                current_analysis, self.futures_data, previous_data
            )
            
            # Structure the response according to the plan
            return {
                'previous': {
                    'date': previous_data['main_data']['date_only'],
                    'spot_vix': previous_data['main_data']['spot_vix'],
                    'curve_shape': previous_data['main_data']['curve_shape'],
                    'trading_signal': previous_data['main_data']['trading_signal'],
                    'roll_carry': {'roll_pct': previous_data['main_data']['roll_carry_pct']}
                },
                'changes': changes,
                'days_since_previous': changes.get('days_since_previous', 1),
                'has_previous_data': changes.get('has_previous_data', False)
            }
            
        except Exception as e:
            print(f"❌ Error getting historical context: {e}")
            return {
                'has_previous_data': False,
                'changes': {'summary': f'Error retrieving historical context: {e}'}
            }
    
    def store_current_analysis(self) -> bool:
        """Manually store current analysis to database."""
        if not self.historical_data:
            return False
            
        try:
            analysis = self.get_term_structure_summary(include_historical=False)
            return self.historical_data.store_analysis(analysis, self.futures_data)
        except Exception as e:
            print(f"❌ Error storing analysis: {e}")
            return False


def calculate_term_structure_metrics(spot_vix: float, futures_df: pd.DataFrame) -> Dict:
    """Helper function to calculate all term structure metrics."""
    analyzer = TermStructureAnalyzer(spot_vix, futures_df)
    return analyzer.get_term_structure_summary()