"""
VIX term structure visualization components.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import seaborn as sns


class VIXVisualizer:
    """Creates visualizations for VIX term structure analysis."""
    
    def __init__(self, style: str = 'seaborn-v0_8'):
        """Initialize with plotting style."""
        plt.style.use('default')  # Use default style
        sns.set_palette("husl")
        self.fig_size = (12, 8)
    
    def plot_term_structure(self, 
                          spot_vix: float,
                          futures_data: pd.DataFrame,
                          save_path: Optional[str] = None,
                          show_plot: bool = True) -> plt.Figure:
        """Plot VIX term structure curve."""
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.fig_size, height_ratios=[3, 1])
        
        if futures_data.empty:
            ax1.text(0.5, 0.5, 'No futures data available', 
                    ha='center', va='center', transform=ax1.transAxes)
            return fig
        
        # Main term structure plot
        days = futures_data['days_to_expiration'].values
        prices = futures_data['price'].values
        
        # Add spot VIX at day 0
        all_days = np.concatenate([[0], days])
        all_prices = np.concatenate([[spot_vix], prices])
        
        # Plot the curve
        ax1.plot(all_days, all_prices, 'bo-', linewidth=2, markersize=8, 
                label='VIX Term Structure')
        
        # Highlight spot VIX
        ax1.plot(0, spot_vix, 'ro', markersize=12, label=f'VIX Spot: {spot_vix:.2f}')
        
        # Add contract labels
        for i, (day, price, symbol) in enumerate(zip(days, prices, futures_data['symbol'])):
            ax1.annotate(symbol, (day, price), textcoords="offset points", 
                        xytext=(0,10), ha='center', fontsize=9)
        
        # Formatting
        ax1.set_xlabel('Days to Expiration')
        ax1.set_ylabel('VIX Level')
        ax1.set_title(f'VIX Term Structure - {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Add horizontal line at spot level
        ax1.axhline(y=spot_vix, color='red', linestyle='--', alpha=0.5)
        
        # Price difference subplot
        if len(futures_data) > 0:
            front_month = futures_data.iloc[0]['price']
            price_diffs = prices - spot_vix
            
            bars = ax2.bar(days, price_diffs, alpha=0.7, 
                          color=['green' if x > 0 else 'red' for x in price_diffs])
            
            ax2.set_xlabel('Days to Expiration')
            ax2.set_ylabel('Premium to Spot')
            ax2.set_title('Futures Premium/Discount to Spot VIX')
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.8)
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if show_plot:
            plt.show()
        
        return fig
    
    def plot_historical_comparison(self,
                                 current_data: pd.DataFrame,
                                 historical_data: List[pd.DataFrame],
                                 save_path: Optional[str] = None) -> plt.Figure:
        """Plot current term structure vs historical curves."""
        
        fig, ax = plt.subplots(figsize=self.fig_size)
        
        # Plot historical curves in light gray
        for i, hist_data in enumerate(historical_data):
            if not hist_data.empty:
                ax.plot(hist_data['days_to_expiration'], hist_data['price'], 
                       color='lightgray', alpha=0.5, linewidth=1)
        
        # Plot current curve prominently
        if not current_data.empty:
            ax.plot(current_data['days_to_expiration'], current_data['price'], 
                   'bo-', linewidth=3, markersize=8, label='Current Structure')
        
        ax.set_xlabel('Days to Expiration')
        ax.set_ylabel('VIX Level')
        ax.set_title('Current vs Historical Term Structures')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_comprehensive_dashboard(self, 
                                     spot_vix: float,
                                     futures_data: pd.DataFrame,
                                     analysis_results: Dict,
                                     save_path: Optional[str] = None) -> plt.Figure:
        """Create comprehensive dashboard with expanded term structure."""
        
        fig = plt.figure(figsize=(20, 14))
        
        # Top left: Points Spreads
        ax1 = plt.subplot2grid((2, 2), (0, 0))
        points_data = analysis_results['points_spreads']
        
        bars = ax1.bar(['Spot to Front', 'Front to Second'], 
                      [points_data['spot_to_front'], points_data['front_to_second']],
                      color=['skyblue', 'lightcoral'])
        ax1.set_title('Points Spreads', fontsize=14, fontweight='bold')
        ax1.set_ylabel('VIX Points')
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax1.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold')
        
        # Top right: Inversions
        ax2 = plt.subplot2grid((2, 2), (0, 1))
        inversions = analysis_results['inversions']
        
        if inversions:
            inversion_labels = []
            inversion_magnitudes = []
            for inv in inversions:
                inversion_labels.append(f"{inv['contract1']} > {inv['contract2']}")
                inversion_magnitudes.append(inv['magnitude'])
            
            bars = ax2.barh(inversion_labels, inversion_magnitudes, color='red', alpha=0.7)
            ax2.set_title('Term Structure Inversions', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Magnitude (Points)')
            
            # Add value labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax2.annotate(f'{width:.2f}',
                            xy=(width, bar.get_y() + bar.get_height() / 2),
                            xytext=(3, 0),
                            textcoords="offset points",
                            ha='left', va='center', fontweight='bold')
        else:
            ax2.text(0.5, 0.5, '✅ No Inversions\nClean Term Structure', 
                    ha='center', va='center', transform=ax2.transAxes,
                    fontsize=12, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen"))
            ax2.set_title('Term Structure Inversions', fontsize=14, fontweight='bold')
        
        ax2.grid(True, alpha=0.3)
        
        # Bottom half: Expanded Term Structure Chart
        ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=2)
        
        if not futures_data.empty:
            days = futures_data['days_to_expiration'].values
            prices = futures_data['price'].values
            
            # Add spot VIX at day 0
            all_days = np.concatenate([[0], days])
            all_prices = np.concatenate([[spot_vix], prices])
            
            # Plot the curve
            ax3.plot(all_days, all_prices, 'bo-', linewidth=3, markersize=8, 
                    label='VIX Term Structure')
            
            # Highlight spot VIX
            ax3.plot(0, spot_vix, 'ro', markersize=12, label=f'VIX Spot: {spot_vix:.2f}')
            
            # Add contract labels for ALL contracts with prices
            for i, (day, price, symbol) in enumerate(zip(days, prices, futures_data['symbol'])):
                ax3.annotate(f'{symbol}\n{price:.2f}', (day, price), 
                           textcoords="offset points", xytext=(0,10), 
                           ha='center', fontsize=9, fontweight='bold')
            
            # Add roll carry analysis box in top right corner of chart
            roll_data = analysis_results['roll_carry']
            roll_text = f"Roll Carry Analysis\n"
            roll_text += f"Synthetic Index: {roll_data['synthetic_index']:.2f}\n"
            roll_text += f"Roll Points: {roll_data['roll_pts']:.4f}\n"
            roll_text += f"Roll Carry: {roll_data['roll_pct']:.2f}%"
            
            # Determine box color based on roll carry sign
            if roll_data['roll_pct'] > 0:
                box_color = '#e8f5e8'  # Light green for positive carry
            elif roll_data['roll_pct'] < 0:
                box_color = '#ffebee'  # Light red for negative carry
            else:
                box_color = '#f5f5f5'  # Light gray for neutral
            
            ax3.text(0.98, 0.02, roll_text, transform=ax3.transAxes, 
                    fontsize=11, verticalalignment='bottom', horizontalalignment='right',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor=box_color, alpha=0.8))
        
        ax3.set_xlabel('Days to Expiration', fontsize=12)
        ax3.set_ylabel('VIX Level', fontsize=12)
        ax3.set_title('VIX Term Structure', fontsize=16, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend(fontsize=10)
        
        # Overall title
        plt.suptitle(f'VIX Term Structure Analysis - {analysis_results["timestamp"][:10]}', 
                    fontsize=18, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def _plot_gauge(self, ax, value: float, title: str, 
                   range_min: float = -10, range_max: float = 10):
        """Create a gauge-style plot for a single metric."""
        
        # Create semicircle
        theta = np.linspace(0, np.pi, 100)
        radius = 1
        
        # Background arc
        ax.plot(radius * np.cos(theta), radius * np.sin(theta), 
               'lightgray', linewidth=20)
        
        # Value position on arc
        if range_max != range_min:
            value_norm = (value - range_min) / (range_max - range_min)
        else:
            value_norm = 0.5
        
        value_norm = max(0, min(1, value_norm))  # Clamp to [0,1]
        value_theta = np.pi * (1 - value_norm)
        
        # Value indicator
        ax.plot([0, radius * np.cos(value_theta)], 
               [0, radius * np.sin(value_theta)], 
               'red', linewidth=4)
        
        # Value text
        ax.text(0, -0.3, f'{value:.1f}', ha='center', va='center', 
               fontsize=14, fontweight='bold')
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.5, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title)
    
    def create_daily_report(self,
                          spot_vix: float,
                          futures_data: pd.DataFrame,
                          analysis_results: Dict,
                          save_path: str = None) -> plt.Figure:
        """Create comprehensive daily monitoring report."""
        
        fig = plt.figure(figsize=(16, 12))
        
        # Term structure plot (top half)
        ax1 = plt.subplot2grid((3, 2), (0, 0), colspan=2)
        
        if not futures_data.empty:
            days = futures_data['days_to_expiration'].values
            prices = futures_data['price'].values
            
            # Add spot at day 0
            all_days = np.concatenate([[0], days])
            all_prices = np.concatenate([[spot_vix], prices])
            
            ax1.plot(all_days, all_prices, 'bo-', linewidth=2, markersize=8)
            ax1.plot(0, spot_vix, 'ro', markersize=12)
            
            # Contract labels
            for day, price, symbol in zip(days, prices, futures_data['symbol']):
                ax1.annotate(symbol, (day, price), textcoords="offset points", 
                           xytext=(0,10), ha='center', fontsize=9)
        
        ax1.set_title(f'VIX Term Structure - {datetime.now().strftime("%Y-%m-%d")}')
        ax1.set_xlabel('Days to Expiration')
        ax1.set_ylabel('VIX Level')
        ax1.grid(True, alpha=0.3)
        
        # Key metrics (middle row)
        ax2 = plt.subplot2grid((3, 2), (1, 0))
        contango_info = analysis_results['contango_backwardation']
        ax2.text(0.1, 0.8, f"Status: {contango_info['status']}", fontsize=12)
        ax2.text(0.1, 0.6, f"Percentage: {contango_info['percentage']:.2f}%", fontsize=12)
        ax2.text(0.1, 0.4, f"Spot VIX: {spot_vix:.2f}", fontsize=12)
        ax2.text(0.1, 0.2, f"Front Month: {contango_info.get('front_month', 'N/A')}", fontsize=12)
        ax2.set_title('Contango/Backwardation')
        ax2.axis('off')
        
        ax3 = plt.subplot2grid((3, 2), (1, 1))
        trading_signal = analysis_results['trading_signal']
        curve_shape = analysis_results['curve_shape']
        ax3.text(0.1, 0.7, f"Signal: {trading_signal}", fontsize=11, weight='bold')
        ax3.text(0.1, 0.5, f"Shape: {curve_shape}", fontsize=11)
        
        roll_yield = analysis_results.get('roll_yield_pct')
        if roll_yield is not None:
            ax3.text(0.1, 0.3, f"Roll Yield: {roll_yield:.1f}%", fontsize=11)
        
        ax3.set_title('Trading Analysis')
        ax3.axis('off')
        
        # Inversions (bottom row)
        ax4 = plt.subplot2grid((3, 2), (2, 0), colspan=2)
        inversions = analysis_results['inversions']
        
        if inversions:
            inv_text = "INVERSIONS DETECTED:\n"
            for inv in inversions:
                inv_text += f"• {inv['contract1']} ({inv['price1']:.2f}) > {inv['contract2']} ({inv['price2']:.2f}) by {inv['magnitude']:.2f}\n"
            ax4.text(0.05, 0.95, inv_text, fontsize=10, va='top', 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
        else:
            ax4.text(0.5, 0.5, 'No inversions detected', fontsize=12, 
                    ha='center', va='center')
        
        ax4.set_title('Curve Inversions')
        ax4.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig