"""
Alert system for VIX term structure anomalies.
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
import logging
from file_manager import file_manager


class VIXAlertSystem:
    """Handles alerts for VIX term structure events."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load alert configuration."""
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': '',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'recipients': []
            },
            'thresholds': {
                'inversion_alert': True,
                'extreme_contango': 3.0,  # points threshold (spot to front)
                'extreme_backwardation': -3.0,  # points threshold (spot to front)
                'high_roll_yield': 30.0,  # % threshold for roll carry
                'vix_spike': 30.0  # VIX level threshold
            },
            'console_alerts': True
        }
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except FileNotFoundError:
                pass
        
        return default_config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for alerts."""
        logger = logging.getLogger('vix_alerts')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def check_alerts(self, analysis_results: Dict) -> List[Dict]:
        """Check analysis results against alert thresholds."""
        alerts = []
        thresholds = self.config['thresholds']
        
        # Check for inversions
        if thresholds['inversion_alert'] and analysis_results['inversions']:
            alerts.append({
                'type': 'INVERSION',
                'severity': 'HIGH',
                'message': f"Term structure inversion detected: {len(analysis_results['inversions'])} inversions",
                'details': analysis_results['inversions']
            })
        
        # Check extreme point spreads (spot to front month)
        points_data = analysis_results.get('points_spreads', {})
        spot_to_front = points_data.get('spot_to_front', 0)
        
        if spot_to_front >= thresholds['extreme_contango']:
            alerts.append({
                'type': 'EXTREME_CONTANGO',
                'severity': 'MEDIUM', 
                'message': f"Extreme contango detected: {spot_to_front:.2f} points",
                'details': points_data
            })
        
        if spot_to_front <= thresholds['extreme_backwardation']:
            alerts.append({
                'type': 'EXTREME_BACKWARDATION',
                'severity': 'HIGH',
                'message': f"Extreme backwardation detected: {spot_to_front:.2f} points",
                'details': points_data
            })
        
        # Check VIX spike
        spot_vix = analysis_results['spot_vix']
        if spot_vix >= thresholds['vix_spike']:
            alerts.append({
                'type': 'VIX_SPIKE',
                'severity': 'HIGH',
                'message': f"VIX spike detected: {spot_vix:.2f}",
                'details': {'vix_level': spot_vix}
            })
        
        # Check roll carry
        roll_carry_data = analysis_results.get('roll_carry', {})
        roll_pct = roll_carry_data.get('roll_pct', 0)
        if abs(roll_pct) >= thresholds['high_roll_yield']:
            alerts.append({
                'type': 'HIGH_ROLL_CARRY',
                'severity': 'MEDIUM',
                'message': f"High roll carry detected: {roll_pct:.2f}%",
                'details': roll_carry_data
            })
        
        return alerts
    
    def send_alerts(self, alerts: List[Dict], analysis_results: Dict):
        """Send alerts via configured channels."""
        if not alerts:
            return
        
        # Console alerts
        if self.config['console_alerts']:
            self._send_console_alerts(alerts)
        
        # Email alerts
        if self.config['email']['enabled']:
            self._send_email_alerts(alerts, analysis_results)
    
    def _send_console_alerts(self, alerts: List[Dict]):
        """Print alerts to console."""
        print("\n" + "="*60)
        print("🚨 VIX TERM STRUCTURE ALERTS")
        print("="*60)
        
        for alert in alerts:
            severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            emoji = severity_emoji.get(alert['severity'], "ℹ️")
            
            print(f"\n{emoji} {alert['severity']} - {alert['type']}")
            print(f"   {alert['message']}")
            
            if self.config.get('verbose_alerts', False):
                print(f"   Details: {alert['details']}")
        
        print("\n" + "="*60)
    
    def _send_email_alerts(self, alerts: List[Dict], analysis_results: Dict):
        """Send email alerts."""
        try:
            email_config = self.config['email']
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"VIX Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Email body
            body = self._create_email_body(alerts, analysis_results)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            
            text = msg.as_string()
            server.sendmail(email_config['username'], email_config['recipients'], text)
            server.quit()
            
            self.logger.info(f"Email alerts sent to {len(email_config['recipients'])} recipients")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alerts: {e}")
    
    def _create_email_body(self, alerts: List[Dict], analysis_results: Dict) -> str:
        """Create HTML email body."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert-high {{ background-color: #ffebee; border-left: 4px solid #f44336; padding: 10px; margin: 10px 0; }}
                .alert-medium {{ background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 10px; margin: 10px 0; }}
                .alert-low {{ background-color: #e8f5e8; border-left: 4px solid #4caf50; padding: 10px; margin: 10px 0; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <h2>VIX Term Structure Alert - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>
            
            <div class="summary">
                <h3>Market Summary</h3>
                <p><strong>VIX Spot:</strong> {analysis_results['spot_vix']:.2f}</p>
                <p><strong>Spot to Front:</strong> {analysis_results.get('points_spreads', {}).get('spot_to_front', 'N/A')} points</p>
                <p><strong>Front to Second:</strong> {analysis_results.get('points_spreads', {}).get('front_to_second', 'N/A')} points</p>
                <p><strong>Roll Carry:</strong> {analysis_results.get('roll_carry', {}).get('roll_pct', 'N/A')}%</p>
                <p><strong>Curve Shape:</strong> {analysis_results['curve_shape']}</p>
                <p><strong>Trading Signal:</strong> {analysis_results['trading_signal']}</p>
            </div>
            
            <h3>Alerts ({len(alerts)})</h3>
        """
        
        for alert in alerts:
            severity_class = f"alert-{alert['severity'].lower()}"
            html += f"""
            <div class="{severity_class}">
                <strong>{alert['severity']} - {alert['type']}</strong><br>
                {alert['message']}
            </div>
            """
        
        html += """
            <p><em>This is an automated alert from the VIX Term Structure Monitor.</em></p>
        </body>
        </html>
        """
        
        return html
    
    def log_alert_history(self, alerts: List[Dict], analysis_results: Dict):
        """Log alerts to file for historical tracking."""
        try:
            alert_entry = {
                'timestamp': datetime.now().isoformat(),
                'alerts': alerts,
                'vix_spot': analysis_results['spot_vix'],
                'spot_to_front_pts': analysis_results.get('points_spreads', {}).get('spot_to_front', 0),
                'roll_carry_pct': analysis_results.get('roll_carry', {}).get('roll_pct', 0),
                'num_inversions': len(analysis_results['inversions'])
            }
            
            # Append to log file
            log_path = file_manager.get_log_path('alerts')
            with open(log_path, 'a') as f:
                f.write(json.dumps(alert_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to log alert history: {e}")


def create_sample_config() -> Dict:
    """Create a sample configuration file."""
    return {
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "your_email@gmail.com",
            "password": "your_app_password",
            "recipients": ["trader@example.com"]
        },
        "thresholds": {
            "inversion_alert": True,
            "extreme_contango": 2.5,
            "extreme_backwardation": -2.5,
            "high_roll_yield": 25.0,
            "vix_spike": 28.0
        },
        "console_alerts": True,
        "verbose_alerts": True
    }