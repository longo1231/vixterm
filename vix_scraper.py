"""
Simple VIX scraper using only the CBOE VIX futures page.
Gets both VIX spot and futures from one source.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time


class VIXDataProvider:
    """Fetches all VIX data from single CBOE page."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.url = "https://www.cboe.com/tradable_products/vix/vix_futures/"
        self.driver = None
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Initialize Chrome driver."""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def get_vix_data(self) -> Tuple[Optional[float], Optional[pd.DataFrame]]:
        """Get both VIX spot and futures from CBOE page."""
        try:
            print("🌐 Fetching VIX data from CBOE...")
            
            self.driver = self._setup_driver()
            self.driver.get(self.url)
            
            # Wait for page to load and JavaScript to execute
            wait = WebDriverWait(self.driver, 30)
            
            print("⏳ Waiting for page content to load...")
            time.sleep(10)  # Give extra time for dynamic content
            
            # Get VIX spot price
            spot_vix = self._extract_spot_vix(wait)
            
            # Get VIX futures table
            futures_data = self._extract_futures_table(wait)
            
            return spot_vix, futures_data
            
        except Exception as e:
            print(f"❌ Error fetching VIX data: {e}")
            return None, None
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_spot_vix(self, wait) -> Optional[float]:
        """Extract VIX spot price from the futures table."""
        try:
            # The VIX spot is in the table as symbol "VIX"
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        symbol = cells[0].text.strip()
                        if symbol == "VIX":
                            # VIX spot is in the LAST column (index 2)
                            last_price = self._parse_price(cells[2].text.strip())
                            if last_price:
                                print(f"✅ VIX Spot: {last_price:.2f}")
                                return last_price
            
            print("❌ Could not find VIX spot price in table")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting VIX spot: {e}")
            return None
    
    def _extract_futures_table(self, wait) -> Optional[pd.DataFrame]:
        """Extract VIX futures from Market Data table."""
        try:
            print("📊 Looking for Market Data table...")
            
            # Wait specifically for table content to be populated
            try:
                # Wait for any table with VIX-related content
                wait.until(EC.presence_of_element_located((By.XPATH, "//td[contains(text(), 'VX')]")))
                print("✅ Found VIX data in tables")
            except:
                print("⏳ VIX table data not yet loaded, continuing anyway...")
            
            # More specific selectors for settlement data
            table_selectors = [
                "//table[contains(.//th, 'Settlement') or contains(.//th, 'Last')]",
                "//table[contains(.//th, 'Symbol')]",
                "//table[contains(.//td, 'VX')]",  # Table containing VX symbols
                "//div[contains(@class, 'market-data')]//table",
                "//div[contains(text(), 'Market Data')]/following::table[1]",
                "//table[contains(@class, 'data-table')]",
                "//table[tbody//td[starts-with(text(), 'VX')]]",
                "//table"
            ]
            
            futures_data = []
            
            for selector in table_selectors:
                try:
                    tables = self.driver.find_elements(By.XPATH, selector)
                    
                    for table in tables:
                        # Get all rows
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        
                        if len(rows) < 2:  # Need at least header + data
                            continue
                        
                        # Look for header row with expected columns
                        header_found = False
                        for row in rows[:3]:  # Check first few rows for header
                            cells = row.find_elements(By.TAG_NAME, "th")
                            if not cells:
                                cells = row.find_elements(By.TAG_NAME, "td")
                            
                            header_text = " ".join([cell.text.strip().lower() for cell in cells])
                            if any(word in header_text for word in ['symbol', 'last', 'price']):
                                header_found = True
                                break
                        
                        if not header_found:
                            continue
                        
                        print(f"📋 Found table with {len(rows)} rows")
                        
                        # First, print the table structure for debugging
                        if rows:
                            print(f"🔍 Table structure analysis:")
                            header_row = rows[0]
                            header_cells = header_row.find_elements(By.TAG_NAME, "th")
                            if not header_cells:
                                header_cells = header_row.find_elements(By.TAG_NAME, "td")
                            
                            headers = [cell.text.strip() for cell in header_cells]
                            print(f"  Headers: {headers}")
                            
                            # Show first few data rows for debugging
                            for i, row in enumerate(rows[1:4]):  # First 3 data rows
                                cells = row.find_elements(By.TAG_NAME, "td")
                                cell_texts = [cell.text.strip() for cell in cells]
                                print(f"  Row {i+1}: {cell_texts}")
                        
                        # Extract data rows - more robust approach
                        settlement_col = -1
                        symbol_col = -1
                        
                        # Find column indices
                        if rows:
                            header_row = rows[0]
                            header_cells = header_row.find_elements(By.TAG_NAME, "th")
                            if not header_cells:
                                header_cells = header_row.find_elements(By.TAG_NAME, "td")
                            
                            for idx, cell in enumerate(header_cells):
                                header_text = cell.text.strip().lower()
                                if 'symbol' in header_text:
                                    symbol_col = idx
                                elif any(word in header_text for word in ['settlement', 'last', 'price']):
                                    settlement_col = idx
                            
                            print(f"  📍 Symbol column: {symbol_col}, Settlement column: {settlement_col}")
                        
                        # Extract futures data
                        for row_idx, row in enumerate(rows[1:]):  # Skip header
                            cells = row.find_elements(By.TAG_NAME, "td")
                            
                            if len(cells) >= 2:
                                # Try to find VIX symbol in any column if symbol_col not found
                                symbol_text = None
                                price = None
                                
                                if symbol_col >= 0 and len(cells) > symbol_col:
                                    symbol_text = cells[symbol_col].text.strip()
                                else:
                                    # Search all columns for VIX symbol
                                    for cell in cells:
                                        text = cell.text.strip()
                                        if text.startswith('VX') and len(text) >= 4:
                                            symbol_text = text
                                            break
                                
                                if symbol_text and symbol_text.startswith('VX') and symbol_text != 'VIX':
                                    # Filter out weekly contracts (e.g., VX30/Q5, VX31/Q5)
                                    # Only keep monthly contracts (e.g., VX/Q5, VX/U5)
                                    if self._is_monthly_contract(symbol_text):
                                        # Use settlement price (more reliable than last)
                                        if settlement_col >= 0 and len(cells) > settlement_col:
                                            price = self._parse_price(cells[settlement_col].text.strip())
                                        else:
                                            # Fallback to searching for price
                                            for cell in cells:
                                                potential_price = self._parse_price(cell.text.strip())
                                                if potential_price:
                                                    price = potential_price
                                                    break
                                        
                                        if price and price > 0:
                                            # Try to get expiration from the EXPIRATION column first
                                            expiration = None
                                            if len(cells) > 1:  # Check if EXPIRATION column exists
                                                exp_text = cells[1].text.strip()
                                                if exp_text and exp_text != '-':
                                                    try:
                                                        expiration = datetime.strptime(exp_text, '%m/%d/%Y').date()
                                                    except:
                                                        pass
                                            
                                            # Fallback to symbol parsing
                                            if not expiration:
                                                expiration = self._parse_new_symbol_format(symbol_text)
                                            
                                            if expiration:
                                                days_to_exp = (expiration - datetime.now().date()).days
                                                
                                                if days_to_exp > 0:  # Only future contracts
                                                    futures_data.append({
                                                        'symbol': symbol_text,
                                                        'price': price,
                                                        'expiration': expiration,
                                                        'days_to_expiration': days_to_exp
                                                    })
                                                    print(f"  📈 {symbol_text}: {price:.2f} ({days_to_exp} days)")
                                                else:
                                                    print(f"  ⏰ {symbol_text}: {price:.2f} (expired)")
                                            else:
                                                print(f"  ❓ {symbol_text}: {price:.2f} (could not parse expiration)")
                                        else:
                                            print(f"  💰 {symbol_text}: no valid price found")
                                    else:
                                        print(f"  🗓️ {symbol_text}: skipped (weekly contract)")
                        
                        if futures_data:
                            break
                    
                    if futures_data:
                        break
                        
                except Exception as e:
                    print(f"  Error with selector {selector}: {e}")
                    continue
            
            if futures_data:
                df = pd.DataFrame(futures_data)
                df = df.sort_values('days_to_expiration').reset_index(drop=True)
                print(f"✅ Found {len(df)} VIX futures contracts")
                return df
            else:
                print("❌ No VIX futures data found")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting futures table: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float."""
        try:
            # Remove common formatting
            clean_text = price_text.replace('$', '').replace(',', '').strip()
            
            # Extract numeric part
            numeric_chars = ''.join(c for c in clean_text if c.isdigit() or c == '.')
            
            if numeric_chars:
                price = float(numeric_chars)
                if 5 < price < 100:  # Reasonable VIX futures range
                    return price
            
            return None
            
        except (ValueError, AttributeError):
            return None
    
    def _is_monthly_contract(self, symbol: str) -> bool:
        """Check if this is a monthly contract (not a weekly)."""
        try:
            # Monthly contracts have format: VX/Q5, VX/U5, etc.
            # Weekly contracts have format: VX30/Q5, VX31/Q5, etc.
            if '/' in symbol:
                prefix = symbol.split('/')[0]
                # If prefix is just "VX", it's a monthly contract
                # If prefix has numbers after VX (like VX30, VX31), it's weekly
                if prefix == 'VX':
                    return True
                elif prefix.startswith('VX') and len(prefix) > 2:
                    # Check if characters after VX are digits
                    suffix = prefix[2:]
                    return not suffix.isdigit()
            
            # For other formats like VXH25, VXQ25 (traditional monthly)
            if len(symbol) >= 4 and symbol.startswith('VX'):
                # Traditional format: VX + letter + numbers
                third_char = symbol[2]
                return third_char.isalpha()
            
            return False
            
        except:
            return False
    
    def _parse_new_symbol_format(self, symbol: str) -> Optional[datetime.date]:
        """Parse new CBOE symbol format like VX/Q5, VX35/U5."""
        try:
            month_codes = {
                'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
                'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12
            }
            
            # Handle formats like VX/Q5, VX35/U5
            if '/' in symbol:
                parts = symbol.split('/')
                if len(parts) == 2:
                    month_year = parts[1]  # Q5, U5, etc.
                    if len(month_year) >= 2:
                        month_code = month_year[0]
                        year_suffix = month_year[1:]
                        
                        if month_code in month_codes:
                            month = month_codes[month_code]
                            # Handle 2-digit year: 25 = 2025, not 2005
                            year_num = int(year_suffix)
                            if year_num < 50:  # Assume 00-49 means 20xx
                                year = 2000 + year_num
                            else:  # 50-99 means 19xx (unlikely for futures)
                                year = 1900 + year_num
                            
                            return self._get_third_wednesday(year, month)
            
            return None
            
        except (ValueError, IndexError):
            return None
    
    def _parse_expiration_date(self, symbol: str) -> Optional[datetime.date]:
        """Parse VIX futures symbol to get expiration date."""
        try:
            month_codes = {
                'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
                'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12
            }
            
            # Symbol format: VX + month code + year (e.g., VXF25)
            if len(symbol) >= 5 and symbol.startswith('VX'):
                month_code = symbol[2]
                year_suffix = symbol[3:]
                
                if month_code in month_codes:
                    month = month_codes[month_code]
                    year = 2000 + int(year_suffix)
                    
                    # VIX futures expire on third Wednesday
                    return self._get_third_wednesday(year, month)
            
            return None
            
        except (ValueError, IndexError):
            return None
    
    def _get_third_wednesday(self, year: int, month: int) -> datetime.date:
        """Calculate third Wednesday of given month/year."""
        first_day = datetime(year, month, 1).date()
        days_ahead = 2 - first_day.weekday()  # Wednesday is 2
        if days_ahead < 0:
            days_ahead += 7
        first_wednesday = first_day + timedelta(days=days_ahead)
        return first_wednesday + timedelta(days=14)  # Third Wednesday


# Compatibility wrapper
class VIXScraper:
    def __init__(self, headless: bool = True):
        self.provider = VIXDataProvider(headless)
    
    def get_spot_vix(self) -> Optional[float]:
        spot, _ = self.provider.get_vix_data()
        return spot
    
    def get_vix_futures(self) -> Optional[pd.DataFrame]:
        _, futures = self.provider.get_vix_data()
        return futures


def create_fake_data() -> pd.DataFrame:
    """Fallback fake data for testing."""
    import numpy as np
    
    base_vix = 20.0
    contracts = []
    
    for i in range(6):
        days = 30 + (i * 30)
        price = base_vix + (i * 0.3) + np.random.normal(0, 0.2)
        
        contracts.append({
            'symbol': f'VX{chr(70+i)}25',
            'price': round(price, 2),
            'days_to_expiration': days,
            'expiration': datetime.now().date() + timedelta(days=days)
        })
    
    return pd.DataFrame(contracts)


# Test the scraper
if __name__ == "__main__":
    provider = VIXDataProvider(headless=False)  # Show browser for debugging
    
    print("=== Testing CBOE VIX Data Scraper ===")
    spot_vix, futures_data = provider.get_vix_data()
    
    print(f"\n📊 VIX Spot: {spot_vix}")
    
    if futures_data is not None and not futures_data.empty:
        print(f"\n📈 VIX Futures ({len(futures_data)} contracts):")
        print(futures_data[['symbol', 'price', 'days_to_expiration']].to_string(index=False))
    else:
        print("\n❌ No futures data found")