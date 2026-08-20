import json
import urllib.parse
import io
import boto3
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

s3 = boto3.client('s3')

class SimpleMovingAverageCrossover(Strategy):
    def init(self):
        close = self.data.Close
        self.ma1 = self.I(lambda x: pd.Series(x).rolling(50).mean(), close)
        self.ma2 = self.I(lambda x: pd.Series(x).rolling(200).mean(), close)

    def next(self):
        if crossover(self.ma1, self.ma2):
            self.buy()
        elif crossover(self.ma2, self.ma1):
            self.position.close()


def lambda_handler(event, context):
    output_bucket = 'backtester-output-416648267136-us-east-2-an'
    
    input_bucket = event['Records'][0]['s3']['bucket']['name']
    input_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    try:
        response = s3.get_object(Bucket=input_bucket, Key=input_key)
        csv_bytes = response['Body'].read()
        
        raw_df = pd.read_csv(io.BytesIO(csv_bytes), header=[0, 1], index_col=0)
        raw_df.index = pd.to_datetime(raw_df.index)
        raw_df.index = raw_df.index.tz_localize(None)
        
        tickers = sorted(list(set([col[1] for col in raw_df.columns if col[1] and "Unnamed" not in col[1]])))
        print(f"Discovered tickers in file structure: {tickers}")
        
        all_results = {}
        
        for ticker in tickers:
            print(f"Processing calculations for ticker: {ticker}")
            
            try:
                asset_df = raw_df.xs(ticker, level=1, axis=1).copy()
                
                # Standardize column naming conventions
                asset_df.columns = [col.capitalize() for col in asset_df.columns]
                asset_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
                
                # Turn columns into pure numeric floats so the backtester doesn't crash
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col in asset_df.columns:
                        asset_df[col] = pd.to_numeric(asset_df[col], errors='coerce')
                
                asset_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
                
                if len(asset_df) < 200:
                    print(f"Skipping {ticker}: Only {len(asset_df)} data points. Need 200 minimum.")
                    continue
                
                # Run the backtest engine
                bt = Backtest(asset_df, SimpleMovingAverageCrossover, cash=10000, commission=0.0)
                stats = bt.run()
                
                def safe_float(val):
                    if pd.isnull(val) or isinstance(val, str) or val is None:
                        return 0.0
                    try:
                        return float(val)
                    except:
                        return 0.0

                all_results[ticker] = {
                    "Return_Percent": safe_float(stats.get('Return [%]')),
                    "Buy_And_Hold_Return_Percent": safe_float(stats.get('Buy & Hold Return [%]')),
                    "Max_Drawdown_Percent": safe_float(stats.get('Max. Drawdown [%]')),
                    "Sharpe_Ratio": safe_float(stats.get('Sharpe Ratio')),
                    "Win_Rate_Percent": safe_float(stats.get('Win Rate [%]')),
                    "Total_Trades": int(stats.get('# Trades', 0)) if pd.notnull(stats.get('# Trades')) else 0
                }
                
            except Exception as inner_error:
                print(f"Skipping ticker asset {ticker} due to runtime calculation failure: {inner_error}")
                continue
                
        final_payload = {
            "source_file": input_key,
            "strategy": "Long-Window 50/200 SMA Crossover",
            "results": all_results
        }
        
        raw_filename = input_key.split('/')[-1]
        output_key = f"results/{raw_filename.replace('.csv', '_results.json')}"
        
        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=json.dumps(final_payload, indent=4),
            ContentType='application/json'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps(f"Processed multi-index columns successfully! Saved to {output_key}")
        }

    except Exception as e:
        print(f"Error handling multi-ticker processing: {str(e)}")
        raise e
