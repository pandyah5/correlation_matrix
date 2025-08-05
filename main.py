from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import json

app = FastAPI()

origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

TICKERS = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "TSX": "^GSPTSE",
    "EURO STOXX 50": "^STOXX50E",
    "Nifty 50": "^NSEI",
    "Shanghai": "000001.SS"
}


@app.get("/correlation")
def get_correlation_matrix() -> dict:
    """
    Fetches historical prices and computes correlation matrix between assets.

    Returns:
        dict: Correlation matrix as nested dictionary using descriptive names.
    """
    series_list = []

    for name, symbol in TICKERS.items():
        try:
            df_full = yf.download(symbol, period="5y", interval="1d", progress=False)

            if 'Adj Close' in df_full.columns:
                df = df_full['Adj Close']
            elif 'Close' in df_full.columns:
                print(f"⚠️ 'Adj Close' not found for {name} ({symbol}); using 'Close'.")
                df = df_full['Close']
            else:
                print(f"❌ No valid price column for {name} ({symbol}).")
                continue

            if df.empty:
                print(f"❌ Data for {name} ({symbol}) is empty.")
                continue

            df.name = symbol # Use the symbol as the name for the series, to be renamed later
            series_list.append(df)

        except Exception as e:
            print(f"❌ Failed to download {name} ({symbol}): {e}")

    if not series_list:
        print("❌ No data fetched.")
        return {}

    # Combine all Series into one DataFrame by date
    combined_df = pd.concat(series_list, axis=1)
    
    # Explicitly rename the columns of the DataFrame using the descriptive names
    # This is the key fix to ensure the correlation matrix has the correct labels
    combined_df.rename(columns={symbol: name for name, symbol in TICKERS.items()}, inplace=True)
    
    # Calculate daily returns and drop NaNs
    returns = combined_df.pct_change().dropna()

    # Compute correlation
    correlation_df = returns.corr()
    
    # Build the final dictionary
    output_dict = {}
    for name in TICKERS.keys():
        if name in correlation_df.columns:
            output_dict[name] = {col: correlation_df.loc[name, col] for col in correlation_df.columns}

    return output_dict

