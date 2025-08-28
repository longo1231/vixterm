#!/usr/bin/env python3
"""
VIX Term Structure Monitor - Main execution script.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict
import pandas as pd

from vix_scraper import VIXScraper, create_fake_data
from term_structure import TermStructureAnalyzer
from visualizer import VIXVisualizer
from alerts import VIXAlertSystem
from file_manager import file_manager
from historical_data import initialize_historical_data


def create_readable_summary(analysis_results: Dict, futures_data: pd.DataFrame) -> str:
    """Create a human-readable summary report with historical context."""
    
    timestamp = analysis_results['timestamp']
    date_str = timestamp[:10]
    time_str = timestamp[11:16]
    
    spot_vix = analysis_results['spot_vix']
    points_spreads = analysis_results.get('points_spreads', {})
    roll_carry = analysis_results.get('roll_carry', {})
    inversions = analysis_results.get('inversions', [])
    
    # Check for historical context
    has_historical = analysis_results.get('has_previous_data', False)
    changes = analysis_results.get('changes', {})
    previous = analysis_results.get('previous', {})
    
    # Create the summary with enhanced header
    if has_historical:
        vix_change = changes.get('spot_vix', {})
        change_text = ""
        if vix_change.get('absolute', 0) != 0:
            direction_symbol = "↗" if vix_change['direction'] == 'up' else "↘" if vix_change['direction'] == 'down' else "→"
            change_text = f" {direction_symbol} {vix_change['absolute']:+.2f} ({vix_change['percentage']:+.1f}%)"
        
        days_desc = f"{changes.get('days_since_previous', 1)} day" + ("s" if changes.get('days_since_previous', 1) > 1 else "")
        summary = f"""VIX Term Structure Summary - {date_str} {time_str}
{'=' * 50}

MARKET OVERVIEW
VIX Spot: {spot_vix:.2f}{change_text} from {days_desc} ago
Previous VIX: {previous.get('spot_vix', 'N/A')} on {previous.get('date', 'N/A')}
Number of Contracts: {len(futures_data)}
Curve Shape: {analysis_results.get('curve_shape', 'N/A')}
Trading Signal: {analysis_results.get('trading_signal', 'N/A')}

HISTORICAL CONTEXT
{changes.get('summary', 'No historical comparison available')}
"""
    else:
        summary = f"""VIX Term Structure Summary - {date_str} {time_str}
{'=' * 50}

MARKET OVERVIEW
VIX Spot: {spot_vix:.2f}
Number of Contracts: {len(futures_data)}
Curve Shape: {analysis_results.get('curve_shape', 'N/A')}
Trading Signal: {analysis_results.get('trading_signal', 'N/A')}

HISTORICAL CONTEXT
{changes.get('summary', 'No previous data available for comparison')}
"""

    # Points analysis section
    summary += f"""
POINTS ANALYSIS
Spot to Front Month: {points_spreads.get('spot_to_front', 0):.2f} points
Front to Second Month: {points_spreads.get('front_to_second', 0):.2f} points
"""

    # Add contango/backwardation status with historical context
    spot_to_front = points_spreads.get('spot_to_front', 0)
    if spot_to_front > 0:
        summary += f"Status: CONTANGO (+{spot_to_front:.2f} pts)\n"
    elif spot_to_front < 0:
        summary += f"Status: BACKWARDATION ({spot_to_front:.2f} pts)\n"
    else:
        summary += "Status: FLAT\n"

    # Roll carry section with historical comparison
    summary += f"""
ROLL CARRY ANALYSIS
Synthetic 30-Day Index: {roll_carry.get('synthetic_index', 0):.2f}
Roll Points: {roll_carry.get('roll_pts', 0):.4f}
Roll Carry: {roll_carry.get('roll_pct', 0):.2f}%"""
    
    if has_historical:
        roll_change = changes.get('roll_carry', {})
        if roll_change.get('absolute', 0) != 0:
            direction_symbol = "↗" if roll_change['direction'] == 'up' else "↘" if roll_change['direction'] == 'down' else "→"
            summary += f" {direction_symbol} {roll_change['absolute']:+.2f}% from previous"
    summary += "\n"

    # Contract changes section (if historical data available)
    if has_historical and changes.get('contracts'):
        summary += f"\nCONTRACT CHANGES\n"
        for contract in changes['contracts']:
            symbol = contract['symbol']
            current = contract['current_price']
            previous = contract['previous_price']
            change = contract['absolute']
            pct = contract['percentage']
            direction_symbol = "↗" if contract['direction'] == 'up' else "↘" if contract['direction'] == 'down' else "→"
            summary += f"{symbol:<8} {current:>7.2f} {direction_symbol} {change:+6.2f} ({pct:+5.1f}%) from {previous:.2f}\n"

    # Inversions section
    if inversions:
        summary += f"\nINVERSIONS DETECTED ({len(inversions)})\n"
        for i, inv in enumerate(inversions, 1):
            summary += f"{i}. {inv['contract1']} ({inv['price1']:.2f}) > {inv['contract2']} ({inv['price2']:.2f}) by {inv['magnitude']:.2f} pts\n"
    else:
        summary += "\nINVERSIONS\nNone - Clean term structure\n"

    # Futures contracts section
    summary += f"\nFUTURES CONTRACTS\n"
    for _, row in futures_data.iterrows():
        summary += f"{row['symbol']:<8} {row['price']:>7.2f}  ({row['days_to_expiration']:>3d} days)\n"

    summary += f"\n{'=' * 50}\nGenerated by VIX Term Structure Monitor\n"
    
    return summary


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='VIX Term Structure Monitor')
    parser.add_argument('--fake-data', action='store_true', 
                       help='Use fake data for testing instead of scraping')
    parser.add_argument('--no-plot', action='store_true',
                       help='Skip plotting (useful for automated runs)')
    parser.add_argument('--save-plots', action='store_true',
                       help='Save plots to organized output directories')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Path to configuration file')
    parser.add_argument('--save-data', action='store_true',
                       help='Save analysis results to organized output directories')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--info', action='store_true',
                       help='Show information about output files and directories')
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Clean up files older than DAYS (default: no cleanup)')
    parser.add_argument('--no-historical', action='store_true',
                       help='Disable historical context and database features')
    parser.add_argument('--migrate-data', action='store_true',
                       help='Migrate existing JSON files to historical database')
    
    args = parser.parse_args()
    
    # Initialize historical data system (unless disabled)
    historical_enabled = not args.no_historical
    historical_db = None
    
    if historical_enabled:
        try:
            historical_db = initialize_historical_data()
            print("📚 Historical database initialized")
        except Exception as e:
            print(f"⚠️ Historical database initialization failed: {e}")
            historical_enabled = False
    
    # Handle special options
    if args.migrate_data:
        if historical_db:
            print("🔄 Starting data migration...")
            migrated = historical_db.migrate_json_files()
            print(f"✅ Migration complete: {migrated} files migrated")
        else:
            print("❌ Cannot migrate data: historical database not available")
        return
    
    if args.info:
        info = file_manager.get_file_info()
        print("📁 VIX Monitor File Information")
        print("=" * 40)
        print(f"Base directory: {info['directories']['base']}")
        print(f"Charts: {info['file_counts']['charts']} files")
        print(f"Data: {info['file_counts']['data']} files") 
        print(f"Logs: {info['file_counts']['logs']} files")
        print(f"Total size: {info['total_size_mb']} MB")
        
        # Show historical database stats if available
        if historical_db:
            db_stats = historical_db.get_database_stats()
            print(f"\n📊 Historical Database")
            print("=" * 40)
            if 'error' in db_stats:
                print(f"Error: {db_stats['error']}")
            else:
                print(f"Analyses: {db_stats.get('record_counts', {}).get('main_analyses', 0)}")
                print(f"Futures: {db_stats.get('record_counts', {}).get('futures_contracts', 0)}")
                print(f"Inversions: {db_stats.get('record_counts', {}).get('inversions', 0)}")
                date_range = db_stats.get('date_range', {})
                if date_range.get('earliest'):
                    print(f"Date range: {date_range['earliest']} to {date_range['latest']}")
        
        print("\nRecent files:")
        for file_path in file_manager.list_recent_files(limit=5):
            print(f"  {file_path}")
        return
    
    if args.cleanup:
        print(f"🧹 Cleaning up files older than {args.cleanup} days...")
        file_manager.cleanup_old_files(args.cleanup)
        print("✅ Cleanup complete!")
        return
    
    print("🔍 VIX Term Structure Monitor")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get data
        if args.fake_data:
            print("📊 Using fake data for testing...")
            spot_vix = 22.5
            futures_data = create_fake_data()
        else:
            print("🌐 Scraping live data from CBOE...")
            scraper = VIXScraper(headless=args.headless)
            
            # Get spot VIX
            spot_vix = scraper.get_spot_vix()
            if spot_vix is None:
                print("❌ Failed to get VIX spot price")
                sys.exit(1)
            
            # Get futures data
            futures_data = scraper.get_vix_futures()
            if futures_data is None or futures_data.empty:
                print("❌ Failed to get VIX futures data")
                sys.exit(1)
        
        print(f"✅ VIX Spot: {spot_vix:.2f}")
        print(f"✅ Futures contracts: {len(futures_data)}")
        
        # Analyze term structure with historical context
        print("\n📈 Analyzing term structure...")
        analyzer = TermStructureAnalyzer(spot_vix, futures_data, enable_historical=historical_enabled)
        analysis_results = analyzer.get_term_structure_summary()
        
        # Display key results with historical context
        print(f"\n📋 Analysis Results:")
        points_spreads = analysis_results.get('points_spreads', {})
        roll_carry = analysis_results.get('roll_carry', {})
        print(f"   Spot to Front: {points_spreads.get('spot_to_front', 'N/A')} points")
        print(f"   Front to Second: {points_spreads.get('front_to_second', 'N/A')} points") 
        print(f"   Roll Carry: {roll_carry.get('roll_pct', 'N/A')}%")
        print(f"   Curve Shape: {analysis_results['curve_shape']}")
        print(f"   Trading Signal: {analysis_results['trading_signal']}")
        
        # Display historical context if available
        if analysis_results.get('has_previous_data', False):
            changes = analysis_results.get('changes', {})
            days_back = analysis_results.get('days_since_previous', 1)
            days_desc = f"{days_back} day" + ("s" if days_back > 1 else "")
            print(f"\n📅 Historical Context ({days_desc} ago):")
            print(f"   Previous VIX: {analysis_results.get('previous', {}).get('spot_vix', 'N/A')}")
            print(f"   Change: {changes.get('spot_vix', {}).get('absolute', 'N/A'):+.2f} pts ({changes.get('spot_vix', {}).get('percentage', 'N/A'):+.1f}%)")
            print(f"   Summary: {changes.get('summary', 'N/A')}")
        elif historical_enabled:
            print(f"\n📅 Historical Context: No previous data available")
        
        if analysis_results['inversions']:
            print(f"   ⚠️  Inversions: {len(analysis_results['inversions'])}")
        
        # Check alerts
        alert_system = VIXAlertSystem(args.config if Path(args.config).exists() else None)
        alerts = alert_system.check_alerts(analysis_results)
        
        if alerts:
            alert_system.send_alerts(alerts, analysis_results)
            alert_system.log_alert_history(alerts, analysis_results)
        else:
            print("\n✅ No alerts triggered")
        
        # Create visualizations
        if not args.no_plot:
            print("\n📊 Creating comprehensive dashboard...")
            visualizer = VIXVisualizer()
            
            # Determine save paths
            if args.save_plots:
                dashboard_path = file_manager.get_dashboard_path(test_mode=args.fake_data)
                show_plot = False
            else:
                dashboard_path = None
                show_plot = True
            
            # Create comprehensive dashboard with all metrics and term structure
            fig = visualizer.create_comprehensive_dashboard(
                spot_vix, futures_data, analysis_results,
                save_path=dashboard_path
            )
            
            if show_plot:
                fig.show()
            
            # Save dashboard if requested
            if args.save_plots:
                print(f"💾 Dashboard saved:")
                print(f"   📊 Dashboard: {dashboard_path}")
        
        # Save human-readable summary
        if args.save_data:
            # Change extension from .json to .txt for summary
            data_path = file_manager.get_data_path("summary", test_mode=args.fake_data)
            data_path = data_path.replace('.json', '.txt')
            
            summary_text = create_readable_summary(analysis_results, futures_data)
            with open(data_path, 'w') as f:
                f.write(summary_text)
            print(f"💾 Summary report saved to: {data_path}")
        
        print("\n✅ Analysis complete!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def run_daily_monitor():
    """Run daily monitoring with organized file output."""
    
    try:
        # Get organized file paths
        _, dashboard_path, data_path = file_manager.get_daily_report_paths(test_mode=False)
        
        # Run analysis
        scraper = VIXScraper(headless=True)
        spot_vix = scraper.get_spot_vix()
        futures_data = scraper.get_vix_futures()
        
        if spot_vix is None or futures_data is None:
            print("Failed to get market data")
            return False
        
        analyzer = TermStructureAnalyzer(spot_vix, futures_data)
        results = analyzer.get_term_structure_summary()
        
        # Create visualizations
        visualizer = VIXVisualizer()
        visualizer.create_comprehensive_dashboard(spot_vix, futures_data, results, dashboard_path)
        
        # Check alerts
        alert_system = VIXAlertSystem()
        alerts = alert_system.check_alerts(results)
        alert_system.send_alerts(alerts, results)
        alert_system.log_alert_history(alerts, results)
        
        # Save results  
        data_path = data_path.replace('.json', '.txt')
        summary_text = create_readable_summary(results, futures_data)
        with open(data_path, 'w') as f:
            f.write(summary_text)
        
        print(f"Daily monitoring complete. Files saved:")
        print(f"  📊 Dashboard: {dashboard_path}")
        print(f"  📄 Data: {data_path}")
        return True
        
    except Exception as e:
        print(f"Daily monitoring failed: {e}")
        return False


if __name__ == "__main__":
    main()