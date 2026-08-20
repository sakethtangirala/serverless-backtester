import boto3
import os
import time
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

load_dotenv()

def clear_s3_bucket(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    try:
        print(f"Emptying bucket '{bucket_name}' to prevent file conflict errors...")
        bucket.objects.all().delete()
        print(f"Bucket '{bucket_name}' successfully cleared.")
        return True
    except ClientError as e:
        print(f"Error clearing bucket {bucket_name}: {e}")
        return False
    except NoCredentialsError:
        print("Credentials not available.")
        return False

def upload_to_s3(local_file, bucket_name, s3_file_key):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(local_file, bucket_name, s3_file_key)
        print(f"Upload Successful: {s3_file_key}")
        return True
    except FileNotFoundError:
        print(f"The local file '{local_file}' was not found.")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

def pull_from_s3(s3_file_name, bucket_name, local_destination_dir=".", silent=False):
    s3 = boto3.client('s3')
    s3_file_key = f"{s3_file_name}"
    clean_local_filename = os.path.basename(s3_file_name)
    local_file_path = os.path.join(local_destination_dir, clean_local_filename)
    try:
        if local_destination_dir and not os.path.exists(local_destination_dir):
            os.makedirs(local_destination_dir, exist_ok=True)
        s3.download_file(bucket_name, s3_file_key, local_file_path)
        print(f"Download Successful! Saved locally to: {local_file_path}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            if not silent:
                print(f"Error: The file '{s3_file_key}' was not found in bucket '{bucket_name}'.")
        else:
            print(f"AWS S3 Error: {e}")
        return False
    except NoCredentialsError:
        print("Credentials not available.")
        return False

if __name__ == "__main__":
    INPUT_BUCKET = os.environ.get("INPUT_BUCKET_NAME")
    OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET_NAME")
    if not INPUT_BUCKET or not OUTPUT_BUCKET:
        raise ValueError("Bucket names could not be loaded. Ensure your .env file is configured correctly.")

    clear_s3_bucket(INPUT_BUCKET)
    clear_s3_bucket(OUTPUT_BUCKET)
    
    time.sleep(1)
    
    upload_to_s3(
        local_file="data/data.csv", 
        bucket_name=INPUT_BUCKET, 
        s3_file_key="data/data.csv"
    )
    
    print("Waiting for AWS Lambda backtest calculations to settle...")
    
    download_success = False
    for attempt in range(30):
        time.sleep(0.5)
        if pull_from_s3("results/data_results.json", OUTPUT_BUCKET, local_destination_dir="results", silent=True):
            download_success = True
            break
            
    if not download_success:
        print("\n[ERROR] Polling timed out. The backtest results file was never generated.")
