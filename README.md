this project utilizes AWS S3 and lambda functions to create a serverless backtester. 

process:
- set up your AWS credentials (access key, secret access key, default region and bucket names), preferably in a .env file.
- make a folder called data and inside it load your tickers & time information in a csv called data.csv
- make sure you have the following route: local to s3 to lambda back to local
- the lambda function should be triggered automatically within AWS and have your backtesting code.
- assuming your setup is proper and you have the libraries in requirements.txt installed (please use a virtual environment), you'll have your metrics in results/data_results.json.

this project, while small, deliberately relies on external processing power for scalability. 
it is often important to find suitable space to host your projects, but sometimes that space isn't on your personal computer.
firms often host their models on the cloud as well for this very reason. their software is powerful and their expansive storage can still be inadequate.

relevant skills:
- s3 buckets
- lambda functions and layers
- cloudwatch logs
- iam users and policies

frameworks:
- boto3
- backtesting (py library)
- json
- dotenv
- io

the get_values.py file is the substance of this project's lambda function. feel free to use it with your own enhancements!
