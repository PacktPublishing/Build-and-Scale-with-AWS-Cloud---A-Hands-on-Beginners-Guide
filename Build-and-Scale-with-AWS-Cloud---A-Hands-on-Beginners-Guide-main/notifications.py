import boto3
import os
from botocore.exceptions import NoCredentialsError

# Initialize the SNS client
sns_client = boto3.client(
    'sns',
    region_name=os.getenv('AWS_REGION')  # Optional, depending on your region
)

# SNS Topic ARN (replace with your actual SNS Topic ARN)
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')

# Ensure that SNS_TOPIC_ARN is set
if not SNS_TOPIC_ARN:
    raise ValueError("SNS_TOPIC_ARN is not set or is invalid.")

def send_sns_notification(user_name, user_position, resume_url, user_experience, user_ctc, user_expected_ctc, user_phone_number):
    """
    Sends a notification to an SNS Topic with the provided user details.
    """
    # Construct the SNS message body
    sns_message_body = f"A new profile has been uploaded. You can view the profile at: {resume_url}\n\nDetails:\n" \
        f"Name: {user_name}\nPosition Applied: {user_position}\nExperience: {user_experience}\nCTC: {user_ctc}\n" \
        f"Expected CTC: {user_expected_ctc}\nPhone Number: {user_phone_number}"

    # Construct the SNS message subject
    sns_subject = f"{user_name} has applied for {user_position}"

    try:
        # Publish the message to SNS
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=sns_message_body,
            Subject=sns_subject
        )
        print(f"Notification sent to SNS for {user_name} applying for {user_position}")
    except NoCredentialsError:
        print("No AWS credentials found. Unable to send SNS notification.")
    except Exception as e:
        print(f"An error occurred while sending SNS notification: {str(e)}")
