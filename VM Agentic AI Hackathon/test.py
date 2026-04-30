import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def call_claude():
    try:
        # Create Bedrock Runtime client
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1",
            verify=False
        )

        # Model ID (update if needed based on console)
        # model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        # model_id ="global.anthropic.claude-sonnet-4-6"
        model_id = "openai.gpt-oss-120b-1:0"
        # model_id = "arn:aws:bedrock:us-east-1:410311316284:inference-profile/anthropic.claude-sonnet-4-6"

        # Call using Converse API (LATEST)
        response = client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": "Explain microservices in simple terms"}
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 200,
                "temperature": 0.5
            }
        )

        # Extract and print response
        # output_text = response["output"]["message"]["content"][0]["text"]
        output_text = response["output"]["message"]["content"][1]["text"]
        print("\nClaude Response:\n")
        print(output_text)

    except NoCredentialsError:
        print("❌ AWS credentials not found. Check environment variables.")

    except ClientError as e:
        print("❌ AWS Client Error:")
        print(e.response["Error"]["Message"])

    except Exception as e:
        print("❌ Unexpected error:", str(e))


if __name__ == "__main__":
    call_claude()