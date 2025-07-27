"""
File management utilities for VIX term structure monitor.
Handles organized output directory structure and timestamped filenames.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class VIXFileManager:
    """Manages file paths and directory structure for VIX monitor outputs."""
    
    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = Path(base_dir)
        self.charts_dir = self.base_dir / "charts"
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"
        
        # Create all directories
        self._create_directories()
    
    def _create_directories(self):
        """Create all necessary output directories."""
        directories = [self.base_dir, self.charts_dir, self.data_dir, self.logs_dir]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_timestamp_string(self, format_type: str = "filename") -> str:
        """Get formatted timestamp string."""
        now = datetime.now()
        
        if format_type == "filename":
            return now.strftime("%Y-%m-%d_%H%M%S")
        elif format_type == "readable":
            return now.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "iso":
            return now.isoformat()
        else:
            return now.strftime("%Y%m%d_%H%M%S")
    
    def get_chart_path(self, chart_type: str = "term_structure", 
                      test_mode: bool = False) -> str:
        """Get path for chart files."""
        timestamp = self.get_timestamp_string()
        prefix = "test_" if test_mode else ""
        filename = f"{prefix}{timestamp}_vix_{chart_type}.png"
        return str(self.charts_dir / filename)
    
    def get_dashboard_path(self, test_mode: bool = False) -> str:
        """Get path for dashboard chart."""
        timestamp = self.get_timestamp_string()
        prefix = "test_" if test_mode else ""
        filename = f"{prefix}{timestamp}_vix_dashboard.png"
        return str(self.charts_dir / filename)
    
    def get_data_path(self, data_type: str = "analysis", 
                     test_mode: bool = False) -> str:
        """Get path for data files."""
        timestamp = self.get_timestamp_string()
        prefix = "test_" if test_mode else ""
        filename = f"{prefix}{timestamp}_vix_{data_type}.json"
        return str(self.data_dir / filename)
    
    def get_log_path(self, log_type: str = "alerts") -> str:
        """Get path for log files."""
        filename = f"vix_{log_type}_history.json"
        return str(self.logs_dir / filename)
    
    def get_daily_report_paths(self, test_mode: bool = False) -> Tuple[str, str, str]:
        """Get paths for daily report files (chart, dashboard, data)."""
        chart_path = self.get_chart_path("term_structure", test_mode)
        dashboard_path = self.get_dashboard_path(test_mode)
        data_path = self.get_data_path("analysis", test_mode)
        
        return chart_path, dashboard_path, data_path
    
    def cleanup_old_files(self, days_to_keep: int = 30):
        """Clean up files older than specified days."""
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for directory in [self.charts_dir, self.data_dir]:
            for file_path in directory.glob("*.png"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
            
            for file_path in directory.glob("*.json"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
    
    def list_recent_files(self, file_type: str = "all", limit: int = 10) -> list:
        """List recent files of specified type."""
        files = []
        
        if file_type in ["all", "charts"]:
            files.extend(self.charts_dir.glob("*.png"))
        
        if file_type in ["all", "data"]:
            files.extend(self.data_dir.glob("*.json"))
        
        if file_type in ["all", "logs"]:
            files.extend(self.logs_dir.glob("*.json"))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return [str(f) for f in files[:limit]]
    
    def get_file_info(self) -> dict:
        """Get information about output directories and file counts."""
        info = {
            "directories": {
                "base": str(self.base_dir),
                "charts": str(self.charts_dir),
                "data": str(self.data_dir),
                "logs": str(self.logs_dir)
            },
            "file_counts": {
                "charts": len(list(self.charts_dir.glob("*.png"))),
                "data": len(list(self.data_dir.glob("*.json"))),
                "logs": len(list(self.logs_dir.glob("*.json")))
            },
            "total_size_mb": self._calculate_directory_size()
        }
        
        return info
    
    def _calculate_directory_size(self) -> float:
        """Calculate total size of output directories in MB."""
        total_size = 0
        
        for directory in [self.charts_dir, self.data_dir, self.logs_dir]:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        
        return round(total_size / (1024 * 1024), 2)


# Global file manager instance
file_manager = VIXFileManager()