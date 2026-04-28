import os
import certifi
import boto3

os.environ["AWS_CA_BUNDLE"] = certifi.where()

s3 = boto3.client("s3", region_name="us-east-1",
                  verify=False
                  )

response = s3.list_objects_v2(Bucket="vm-kendra-chatbot-db-to-be-deleted")

for obj in response.get("Contents", []):
    print(obj["Key"])