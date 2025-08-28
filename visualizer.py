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
        
        fig = plt.figure(figsize=(20, 12))  # Simplified single chart layout
        
        # Single main chart: VIX Term Structure
        ax = plt.subplot(1, 1, 1)
        
        if not futures_data.empty:
            days = futures_data['days_to_expiration'].values
            prices = futures_data['price'].values
            
            # Add spot VIX at day 0
            all_days = np.concatenate([[0], days])
            all_prices = np.concatenate([[spot_vix], prices])
            
            # Check for historical data and plot previous curve first (so it's in background)
            has_historical = analysis_results.get('has_previous_data', False)
            if has_historical:
                previous_data = analysis_results.get('previous', {})
                changes = analysis_results.get('changes', {})
                contract_changes = {c['symbol']: c for c in changes.get('contracts', [])}
                
                # Create previous day data points
                previous_spot = previous_data.get('spot_vix', spot_vix)
                previous_days = []
                previous_prices = []
                
                # Add previous spot at day 0
                previous_days.append(0)
                previous_prices.append(previous_spot)
                
                # Add previous futures prices (use current days, previous prices)
                for i, (day, symbol) in enumerate(zip(days, futures_data['symbol'])):
                    if symbol in contract_changes:
                        previous_prices.append(contract_changes[symbol]['previous_price'])
                        previous_days.append(day)
                    else:
                        # If no historical data for this contract, use current price
                        previous_prices.append(prices[i])
                        previous_days.append(day)
                
                # Plot previous day's curve in light gray dotted line
                ax.plot(previous_days, previous_prices, 'o--', color='lightgray', 
                       linewidth=2, markersize=6, alpha=0.7,
                       label=f'Previous ({changes.get("days_since_previous", 1)} day ago)')
            
            # Plot current curve (on top)
            current_label = 'Current VIX Term Structure'
            if has_historical:
                current_label = 'Current (Today)'
            
            ax.plot(all_days, all_prices, 'bo-', linewidth=3, markersize=8, 
                    label=current_label)
            
            # Highlight spot VIX with color based on change
            spot_color = 'red'
            if has_historical:
                vix_change = analysis_results.get('changes', {}).get('spot_vix', {})
                if vix_change.get('direction') == 'up':
                    spot_color = 'darkgreen'
                elif vix_change.get('direction') == 'down':
                    spot_color = 'red'
                else:
                    spot_color = 'orange'
            
            ax.plot(0, spot_vix, 'o', color=spot_color, markersize=12, 
                   label=f'VIX Spot: {spot_vix:.2f}')
            
            # Add spot VIX label with change if available
            spot_label = f'VIX Spot\n{spot_vix:.2f}'
            if has_historical:
                vix_change = analysis_results.get('changes', {}).get('spot_vix', {})
                if vix_change.get('absolute', 0) != 0:
                    direction_symbol = "↗" if vix_change['direction'] == 'up' else "↘" if vix_change['direction'] == 'down' else "→"
                    spot_label += f'\n{direction_symbol}{vix_change["absolute"]:+.2f}'
            
            ax.annotate(spot_label, (0, spot_vix), 
                       textcoords="offset points", xytext=(0,10), 
                       ha='center', fontsize=9, fontweight='bold')
            
            # Add contract labels for ALL contracts with prices and changes
            for i, (day, price, symbol) in enumerate(zip(days, prices, futures_data['symbol'])):
                label_text = f'{symbol}\n{price:.2f}'
                
                # Add change indicators if historical data available
                if has_historical and symbol in contract_changes:
                    change_info = contract_changes[symbol]
                    change = change_info['absolute']
                    if abs(change) >= 0.01:  # Only show significant changes
                        direction_symbol = "↗" if change > 0 else "↘" if change < 0 else "→"
                        label_text += f'\n{direction_symbol}{change:+.2f}'
                        
                        # Add subtle change indicator arrow
                        if change > 0:
                            ax.annotate('↗', (day, price), textcoords="offset points", 
                                       xytext=(15, 15), ha='center', fontsize=12, 
                                       color='darkgreen', fontweight='bold')
                        elif change < 0:
                            ax.annotate('↘', (day, price), textcoords="offset points", 
                                       xytext=(15, 15), ha='center', fontsize=12, 
                                       color='darkred', fontweight='bold')
                
                ax.annotate(label_text, (day, price), 
                           textcoords="offset points", xytext=(0,10), 
                           ha='center', fontsize=9, fontweight='bold')
            
            # Add enlarged roll carry analysis box in top right corner of chart
            roll_data = analysis_results['roll_carry']
            
            # Determine colors based on roll carry sign
            if roll_data['roll_pct'] > 0:
                box_color = '#e8f5e8'  # Light green for positive carry
                pct_color = 'darkgreen'
            elif roll_data['roll_pct'] < 0:
                box_color = '#ffebee'  # Light red for negative carry
                pct_color = 'darkred'
            else:
                box_color = '#f5f5f5'  # Light gray for neutral
                pct_color = 'black'
            
            # Create larger, more prominent roll carry box
            ax.text(0.98, 0.15, "ROLL CARRY ANALYSIS", transform=ax.transAxes, 
                   fontsize=14, fontweight='bold', ha='right', va='bottom')
            ax.text(0.98, 0.11, f"Synthetic 30-Day Index: {roll_data['synthetic_index']:.2f}", 
                   transform=ax.transAxes, fontsize=12, ha='right', va='bottom')
            ax.text(0.98, 0.07, f"Roll Points: {roll_data['roll_pts']:.4f}", 
                   transform=ax.transAxes, fontsize=12, ha='right', va='bottom')
            ax.text(0.98, 0.02, f"ROLL CARRY: {roll_data['roll_pct']:.2f}%", 
                   transform=ax.transAxes, fontsize=16, fontweight='bold', 
                   ha='right', va='bottom', color=pct_color,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=box_color, alpha=0.9))
        
        ax.set_ylabel('VIX Level', fontsize=12)
        # Remove the bottom x-axis label since we now have expiry dates on top
        ax.set_xlabel('')
        ax.set_title('VIX Term Structure', fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        # Add secondary x-axis with actual expiry dates if we have futures data
        if not futures_data.empty:
            # Create secondary x-axis for dates
            ax2 = ax.twiny()
            
            # Use actual expiration dates as labels
            tick_positions = all_days
            tick_labels = ['Spot']
            
            # Format expiration dates as MM/DD
            for _, row in futures_data.iterrows():
                exp_date = row['expiration']
                if hasattr(exp_date, 'strftime'):
                    tick_labels.append(exp_date.strftime('%m/%d'))
                else:
                    # Fallback to symbol if date format issue
                    tick_labels.append(row['symbol'].replace('/', ''))
            
            ax2.set_xlim(ax.get_xlim())
            ax2.set_xticks(tick_positions)
            ax2.set_xticklabels(tick_labels, fontsize=9, rotation=45, ha='left')
            ax2.set_xlabel('Expiry Dates', fontsize=11, labelpad=10)
        
        # Add concise text rows below the chart for contango % and differences
        if not futures_data.empty and len(futures_data) > 1:
            # Calculate from spot to first future, then between futures
            all_prices = np.concatenate([[spot_vix], prices])
            
            # Calculate differences and percentages (starting from index 1)
            contango_pcts = []
            differences = []
            
            for i in range(1, len(all_prices)):
                diff = all_prices[i] - all_prices[i-1]
                pct = (diff / all_prices[i]) * 100 if all_prices[i] != 0 else 0
                contango_pcts.append(pct)
                differences.append(diff)
            
            # Create aligned text that matches the contract positions on the chart
            # Position text under each contract based on days to expiration
            x_positions = all_days[1:]  # Skip spot (position 0), start from first contract
            symbols = ['VIX Spot'] + list(futures_data['symbol'])
            pair_labels = [f"{symbols[i][:3]}→{symbols[i+1][:6]}" for i in range(len(symbols)-1)]
            
            for i, (x_pos, pct, diff, label) in enumerate(zip(x_positions, contango_pcts, differences, pair_labels)):
                # Convert days to normalized chart coordinates
                x_norm = (x_pos - min(all_days)) / (max(all_days) - min(all_days))
                
                # Add percentage and difference text aligned under each contract
                # Add extra spacing for the first column to prevent smooshing with label
                x_offset = 0.05 if i == 0 else 0  # Extra spacing for first column only
                ax.text(x_norm + x_offset, -0.12, f"{pct:+.1f}%", transform=ax.transAxes, 
                       fontsize=11, fontfamily='monospace', ha='center', fontweight='bold')
                ax.text(x_norm + x_offset, -0.16, f"{diff:+.2f}", transform=ax.transAxes, 
                       fontsize=11, fontfamily='monospace', ha='center')
            
            # Add row labels on the left with extra spacing for first column
            ax.text(0.02, -0.12, "Contango %:", transform=ax.transAxes, 
                   fontsize=12, fontweight='bold')
            ax.text(0.02, -0.16, "Differences:", transform=ax.transAxes, 
                   fontsize=12, fontweight='bold')
        
        # Add trading signal and commentary at the bottom
        curve_shape = analysis_results.get('curve_shape', 'N/A')
        trading_signal = analysis_results.get('trading_signal', 'N/A')
        inversions = analysis_results.get('inversions', [])
        
        # Create comprehensive commentary
        if inversions:
            inversion_text = f"⚠️ {len(inversions)} INVERSIONS DETECTED"
            signal_color = 'red'
        else:
            inversion_text = "✅ Clean Term Structure"
            signal_color = 'darkgreen'
        
        commentary = f"{inversion_text} | Curve: {curve_shape} | Signal: {trading_signal}"
        
        ax.text(0.5, -0.22, commentary, transform=ax.transAxes, 
               fontsize=12, fontweight='bold', ha='center', 
               bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.8),
               color=signal_color)
        
        # Enhanced title with historical context
        title = f'VIX Term Structure Analysis - {analysis_results["timestamp"][:10]}'
        if has_historical:
            changes = analysis_results.get('changes', {})
            vix_change = changes.get('spot_vix', {})
            if vix_change.get('absolute', 0) != 0:
                direction_symbol = "↗" if vix_change['direction'] == 'up' else "↘"
                title += f'   |   VIX {direction_symbol} {vix_change["absolute"]:+.2f} ({vix_change["percentage"]:+.1f}%)'
        
        plt.suptitle(title, fontsize=18, fontweight='bold')
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