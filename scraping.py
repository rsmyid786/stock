import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL for NSE Stock Watch
url = 'https://www.nseindia.com/live_market/dynaContent/live_watch/stock_watch/niftyStockWatch.htm'

# Request headers to mimic a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Fetch the webpage content
response = requests.get(url, headers=headers)

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Find the table containing the stock symbols
table = soup.find('table', {'class': 'stockTable'})

# Extract stock symbols from the table
symbols = []
for row in table.find_all('tr')[1:]:
    cols = row.find_all('td')
    symbol = cols[0].text.strip()  # Assuming symbol is in the first column
    symbols.append(symbol)

# Save symbols to a CSV file
symbols_df = pd.DataFrame(symbols, columns=["Symbol"])
symbols_df.to_csv('nse_stock_symbols.csv', index=False)

print("CSV file created with NSE stock symbols.")
