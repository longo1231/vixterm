"""
Email notification system for VIX Term Structure Monitor.
Sends daily analysis results with chart and data attachments.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import glob
from typing import Optional, List, Tuple


class VIXEmailSender:
    """Handles email notifications for VIX analysis results."""
    
    def __init__(self):
        """Initialize email configuration from environment variables."""
        self.smtp_host = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_PORT', '587'))
        self.username = os.getenv('EMAIL_USER')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.recipient = os.getenv('RECIPIENT_EMAIL')
        
        if not all([self.username, self.password, self.recipient]):
            raise ValueError("Missing required email configuration. Check environment variables.")
    
    def find_latest_files(self) -> Tuple[Optional[str], Optional[str]]:
        """Find the most recent chart and data files."""
        
        # Find latest chart file
        chart_files = glob.glob('outputs/charts/*_vix_dashboard.png')
        latest_chart = max(chart_files, key=os.path.getctime) if chart_files else None
        
        # Find latest data file
        data_files = glob.glob('outputs/data/*_vix_summary.txt')
        latest_data = max(data_files, key=os.path.getctime) if data_files else None
        
        return latest_chart, latest_data
    
    def read_summary_data(self, data_file: str) -> dict:
        """Extract key metrics from summary file for email body with historical and statistical context."""
        metrics = {}
        statistical_insights = []
        
        try:
            with open(data_file, 'r') as f:
                content = f.read()
                
                # Extract key information
                lines = content.split('\n')
                in_statistical_section = False
                
                for line in lines:
                    if 'VIX Spot:' in line:
                        # Enhanced to capture change info
                        parts = line.split(':', 1)[1].strip()
                        metrics['spot_vix'] = parts.split(' ')[0]  # Just the number
                        if '↗' in line or '↘' in line:
                            metrics['spot_vix_full'] = parts  # Full text with change
                            metrics['has_historical'] = True
                        else:
                            metrics['spot_vix_full'] = parts
                            metrics['has_historical'] = False
                    elif 'Previous VIX:' in line:
                        metrics['previous_vix'] = line.split(':')[1].strip()
                    elif 'Curve Shape:' in line:
                        metrics['curve_shape'] = line.split(':')[1].strip()
                    elif 'Trading Signal:' in line:
                        metrics['trading_signal'] = line.split(':')[1].strip()
                    elif 'Roll Carry:' in line and 'ANALYSIS' not in line:
                        metrics['roll_carry'] = line.split(':')[1].strip()
                    elif 'Status:' in line and ('CONTANGO' in line or 'BACKWARDATION' in line):
                        metrics['contango_status'] = line.split(':')[1].strip()
                    elif line.startswith('HISTORICAL CONTEXT'):
                        # Skip the header
                        continue
                    elif line.strip() and 'VIX up' in line and 'points' in line:
                        # Capture historical summary
                        metrics['historical_summary'] = line.strip()
                    elif 'STATISTICAL CONTEXT' in line:
                        in_statistical_section = True
                    elif in_statistical_section and '📊' in line:
                        statistical_insights.append(line.strip())
                    elif in_statistical_section and ('percentile' in line.lower() or '%ile' in line):
                        # Capture percentile information
                        if 'VIX:' in line and 'percentile' in line:
                            metrics['vix_percentile'] = line.split('percentile')[0].split()[-1]
                        elif 'Contango:' in line and 'percentile' in line:
                            metrics['contango_percentile'] = line.split('percentile')[0].split()[-1]
                        elif 'Roll' in line and 'percentile' in line:
                            metrics['roll_percentile'] = line.split('percentile')[0].split()[-1]
                
                if statistical_insights:
                    metrics['statistical_insights'] = statistical_insights[:3]  # Top 3 insights
                    
        except Exception as e:
            print(f"⚠️ Warning: Could not parse summary file: {e}")
            
        return metrics
    
    def create_email_body(self, metrics: dict, chart_file: str, data_file: str) -> str:
        """Create HTML email body with analysis summary."""
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M EST')
        
        # Determine market sentiment emoji and color
        signal = metrics.get('trading_signal', '').lower()
        if 'strong contango' in signal:
            sentiment_emoji = "🔴"
            sentiment_color = "#dc3545"
        elif 'contango' in signal:
            sentiment_emoji = "🟡" 
            sentiment_color = "#ffc107"
        elif 'backwardation' in signal:
            sentiment_emoji = "🟢"
            sentiment_color = "#28a745"
        else:
            sentiment_emoji = "⚪"
            sentiment_color = "#6c757d"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; display: flex; align-items: center;">
                    📈 VIX Term Structure Monitor
                </h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{timestamp}</p>
            </div>
            
            <div style="border: 1px solid #dee2e6; border-top: none; padding: 25px; border-radius: 0 0 10px 10px;">
                <div style="background: {sentiment_color}; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="margin: 0; display: flex; align-items: center;">
                        {sentiment_emoji} Market Signal: {metrics.get('trading_signal', 'N/A')}
                    </h2>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff;">
                        <h3 style="margin: 0 0 5px 0; color: #007bff;">VIX Spot</h3>
                        <p style="margin: 0; font-size: 24px; font-weight: bold;">{metrics.get('spot_vix', 'N/A')}</p>
                        {f'<p style="margin: 5px 0 0 0; font-size: 14px; color: #666;">{metrics.get("spot_vix_full", "").replace(metrics.get("spot_vix", ""), "").strip()}</p>' if metrics.get('has_historical', False) else ''}
                        {f'<p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;"><strong>{metrics.get("vix_percentile", "N/A")}th percentile</strong> (1yr)</p>' if metrics.get('vix_percentile') else ''}
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                        <h3 style="margin: 0 0 5px 0; color: #28a745;">Roll Carry</h3>
                        <p style="margin: 0; font-size: 24px; font-weight: bold;">{metrics.get('roll_carry', 'N/A')}</p>
                        {f'<p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;"><strong>{metrics.get("roll_percentile", "N/A")}th percentile</strong> (1yr)</p>' if metrics.get('roll_percentile') else ''}
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0;">Market Structure</h3>
                    <p><strong>Curve Shape:</strong> {metrics.get('curve_shape', 'N/A')}</p>
                    <p style="margin: 5px 0 0 0;"><strong>Status:</strong> {metrics.get('contango_status', 'N/A')}</p>
                </div>
                
                {f'''<div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0; color: #856404;">📅 Daily Comparison</h3>
                    <p style="margin: 0; font-style: italic;">{metrics.get('historical_summary', 'Historical context not available')}</p>
                    {f'<p style="margin: 5px 0 0 0;"><strong>Previous VIX:</strong> {metrics.get("previous_vix", "N/A")}</p>' if metrics.get('previous_vix') else ''}
                </div>''' if metrics.get('has_historical', False) else ''}
                
                {f'''<div style="background: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 4px solid #4caf50; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0; color: #2e7d32;">📊 Statistical Context (1-Year)</h3>
                    {'<br>'.join([f'<p style="margin: 5px 0;">{insight}</p>' for insight in metrics.get('statistical_insights', [])])}
                </div>''' if metrics.get('statistical_insights') else ''}
                
                <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; border-left: 4px solid #0066cc;">
                    <h3 style="margin: 0 0 10px 0; color: #0066cc;">📎 Attachments</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>📊 <strong>VIX Term Structure Chart</strong> ({os.path.basename(chart_file)})</li>
                        <li>📋 <strong>Analysis Summary</strong> ({os.path.basename(data_file)})</li>
                    </ul>
                </div>
                
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #dee2e6;">
                
                <p style="margin: 0; color: #6c757d; font-size: 12px; text-align: center;">
                    Generated automatically by VIX Term Structure Monitor<br>
                    📧 Daily delivery via GitHub Actions
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def attach_file(self, msg: MIMEMultipart, file_path: str) -> None:
        """Attach a file to the email message."""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(file_path)}'
            )
            msg.attach(part)
            print(f"✅ Attached: {os.path.basename(file_path)}")
            
        except Exception as e:
            print(f"❌ Failed to attach {file_path}: {e}")
    
    def send_daily_report(self) -> bool:
        """Send daily VIX analysis report via email."""
        try:
            print("📧 Preparing daily VIX report email...")
            
            # Find latest files
            chart_file, data_file = self.find_latest_files()
            
            if not chart_file or not data_file:
                print("❌ Missing required files for email")
                return False
            
            print(f"📊 Chart: {chart_file}")
            print(f"📋 Data: {data_file}")
            
            # Read summary data
            metrics = self.read_summary_data(data_file)
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = self.recipient
            
            # Enhanced dynamic subject with historical context
            signal = metrics.get('trading_signal', 'Analysis Complete')
            spot_vix = metrics.get('spot_vix', 'N/A')
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Add change info to subject if available
            subject = f"VIX Monitor {date_str} - Spot {spot_vix}"
            if metrics.get('has_historical', False):
                spot_full = metrics.get('spot_vix_full', '')
                change_info = spot_full.replace(spot_vix, '').strip()
                if change_info:
                    subject += f" ({change_info})"
            subject += f" - {signal}"
            
            msg['Subject'] = subject
            
            # Create email body
            html_body = self.create_email_body(metrics, chart_file, data_file)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach files
            self.attach_file(msg, chart_file)
            self.attach_file(msg, data_file)
            
            # Send email
            print("📤 Sending email...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            print(f"✅ Email sent successfully to {self.recipient}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False


def main():
    """Main function to send daily report."""
    try:
        sender = VIXEmailSender()
        success = sender.send_daily_report()
        
        if not success:
            exit(1)  # Exit with error code for GitHub Actions
            
    except Exception as e:
        print(f"❌ Email sender failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()