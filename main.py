import os
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Configuring the logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_psws_status(station_id):
    """
    Checks the PSWS API for files posted yesterday.
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # API Parameters
    base_url = "https://pswsnetwork.eng.ua.edu/observations/downloadapi/"
    params = {
        'station_id': station_id,
        'start_date': yesterday,
        'end_date': yesterday
    }
    
    try:
        logging.info(f"Checking PSWS data for {station_id} on {yesterday}...")
        response = requests.get(base_url, params=params, timeout=30)
        
        if response.status_status == 200:
            return f"✅ Success! Data files were found and are available for {yesterday}."
        elif response.status_code == 404:
            return f"⚪ No observations were found for {yesterday}."
        else:
            return f"⚠️ API returned status code: {response.status_code}"
            
    except Exception as e:
        logging.error(f"API Request failed: {str(e)}")
        return "❌ Failed to connect to the PSWS Network API."

def send_email(email_config, psws_report):
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = email_config['receiver_email']
        msg['Subject'] = f"PSWS Daily Update - {yesterday_str}"
        
        body = (
            f"Hello!\n\n"
            f"Here is the daily update from the Personal Space Weather Station Network.\n\n"
            f"--- Report for {yesterday_str} ---\n"
            f"Station ID: {email_config['station_id']}\n"
            f"Status: {psws_report}\n\n"
            f"System check performed at: {current_time}.\n"
            "— Your GitHub Bot"
        )
        
        msg.attach(MIMEText(body, 'plain')) 
      
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'], timeout=15)
        server.starttls() 
        
        with server:
            server.login(email_config['sender_email'], email_config['smtp_password']) 
            server.send_message(msg)
            logging.info("Email sent successfully")
          
    except Exception as e: 
        logging.error(f"Failed to send email: {str(e)}")
        raise

def validate_config(config):
    required_keys = ['sender_email', 'receiver_email', 'smtp_server', 'smtp_port', 'smtp_password', 'station_id']
    missing = [key for key in required_keys if not config.get(key) or str(config.get(key)).strip() == ""]

    if missing:
        logging.error(f"Missing configuration: {', '.join(missing)}")
        raise ValueError("Missing environment variables")

if __name__ == "__main__":
    try:
        config = {
            'sender_email': os.getenv('SENDER_EMAIL'),
            'receiver_email': os.getenv('RECEIVER_EMAIL'),
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': os.getenv('SMTP_PORT'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'station_id': os.getenv('STATION_ID', 'S000028') # Default to a test ID if not set
        }

        validate_config(config)
        
        # 1. Fetch the data status first
        report = fetch_psws_status(config['station_id'])
        
        # 2. Send the email with the report included
        send_email(config, report)
            
    except Exception as e:
        logging.error(f"Major failure: {str(e)}")
        raise
