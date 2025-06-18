from flask import Blueprint, render_template, request
import boto3
import os
from datetime import datetime
import psycopg2
from psycopg2 import sql
from botocore.exceptions import NoCredentialsError, ClientError
import time
import json

# Import the send_sns_notification function from notifications.py
from notifications import send_sns_notification

# Initialize the S3 client
s3_client = boto3.client(
    's3',
    region_name=os.getenv('AWS_REGION')  # Optional, depending on your region
)

# S3 bucket name
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Initialize RDS connection (using IAM Role for credentials)
rds_host = os.getenv('RDS_HOST')  # RDS endpoint URL
rds_db_name = 'thinknyx'
rds_user = os.getenv('RDS_USER')  # Postgres username
rds_port = '5432'  # Default PostgreSQL port
secret_name = os.getenv('SECRET_NAME') # Secret to Read postgres password from

# Initialize Secrets Manager client
secrets_client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION'))

# Function to get RDS password from Secrets Manager
def get_rds_password():
    try:
        get_secret_value_response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        secret_dict = json.loads(secret)
        return secret_dict['password']
    except ClientError as e:
        print(f"Error retrieving secret from Secrets Manager: {e}")
        return None

# Get the RDS password from Secrets Manager
rds_password = get_rds_password()

if not rds_password:
    raise Exception("Unable to retrieve RDS password from Secrets Manager.")

# Establish connection with the retrieved RDS password
conn = psycopg2.connect(
    host=rds_host,
    database=rds_db_name,
    user=rds_user,
    password=rds_password,
    port=rds_port,
    sslmode='require'  # SSL is recommended for RDS connections
)

# Create the table if it doesn't exist and add new columns if they don't exist
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS careers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255),
        experience INT,
        position VARCHAR(255),
        ctc INT,
        resume_url VARCHAR(255),
        phone_number VARCHAR(20),
        expected_ctc INT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Add new columns if they don't exist
cursor.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='careers' AND column_name='phone_number') THEN
            ALTER TABLE careers ADD COLUMN phone_number VARCHAR(20);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='careers' AND column_name='expected_ctc') THEN
            ALTER TABLE careers ADD COLUMN expected_ctc INT;
        END IF;
    END $$;
""")
conn.commit()

careers_blueprint = Blueprint('careers', __name__)

@careers_blueprint.route('', methods=['GET', 'POST'])
def careers():
    if request.method == 'POST':
        # Get the user inputs from the form
        user_name = request.form.get('name')
        user_experience = request.form.get('experience')
        user_position = request.form.get('position')
        user_ctc = request.form.get('ctc')
        user_phone_number = request.form.get('phone')
        user_expected_ctc = request.form.get('expected_ctc')

        # Handle file upload
        if 'file' not in request.files:
            return "No file part", 400

        file = request.files['file']

        if file.filename == '':
            return "No selected file", 400

        # Extract file extension and create the file name
        file_extension = os.path.splitext(file.filename)[1]  # Get the file extension
        file_name = f"{user_name}{file_extension}"  # Combine user name with the file extension

        # Get the current date in ddmmyyyy format
        current_date = datetime.now().strftime('%d%m%Y')

        # Create the S3 folder path based on the current date
        s3_folder = f"{current_date}/{file_name}"

        try:
            # Upload file to S3 within the folder structure
            s3_client.upload_fileobj(file, S3_BUCKET_NAME, s3_folder)

            # Store form data in the RDS PostgreSQL database
            resume_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_folder}"

            # Insert the data into the 'careers' table
            insert_query = sql.SQL("""
                INSERT INTO careers (name, experience, position, ctc, resume_url, phone_number, expected_ctc)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """)
            cursor.execute(insert_query, (user_name, user_experience, user_position, user_ctc, resume_url, user_phone_number, user_expected_ctc))
            conn.commit()

            # Call the function to send the SNS notification
            send_sns_notification(
                user_name, 
                user_position, 
                resume_url, 
                user_experience, 
                user_ctc, 
                user_expected_ctc, 
                user_phone_number
            )

            # Return success message
            return f"File '{file_name}' uploaded successfully to S3 and your application has been submitted."

        except NoCredentialsError:
            return "Credentials not available", 400
        except Exception as e:
            return f"An error occurred: {str(e)}", 500

    # Render the careers page template
    return render_template('careers.html')
