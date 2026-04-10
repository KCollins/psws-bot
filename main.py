import os
import smtplib
import logging
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Configuring the logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_psws_file_list(station_id):
    """
    Scrapes the PSWS Observation List page for filenames from yesterday.
    """
    # Calculate "Yesterday"
    yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Construct the URL with filters
    # Note: station_id can be left blank for 'all stations'
    base_url = "https://pswsnetwork.eng.ua.edu/observations/observation_list/"
    query_url = (
        f"{base_url}?station={station_id}"
        f"&startDate__gte={yesterday_date}"
        f"&endDate__lte={yesterday_date}"
    )
    
    files = []
    try:
        logging.info(f"Scraping file list from: {query_url}")
        response = requests.get(query_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Finding the filenames. 
        # Based on the PSWS site structure, we look for text containing 'OBS' or links ending in '.zip'
        for link in soup.find_all('a'):
            href = link.get('href', '')
            text = link.get_text().strip()
            
            if "OBS" in text and ".zip" in text:
                files.append(text)
        
        # Deduplicate and return
        return sorted(list(set(files)))

    except Exception as e:
        logging.error(f"Scraping failed: {str(e)}")
        return None

def send_email(email_config, file_list):
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = email_config['receiver_email']
        msg['Subject'] = f"PSWS Update: {len(file_list)} files found for {yesterday_str}"
        
        # Format the list of files for the email body
        if file_list:
            file_section = "\n".join([f"• {f}" for f in file_list])
            status_msg = f"The following {len(file_list)} files were posted yesterday:"
        else:
            file_section = "No files found for this period."
            status_msg = "The network was quiet yesterday."

        body = (
            f"Hello!\n\n"
            f"--- Daily Report for {yesterday_str} ---\n"
            f"{status_msg}\n\n"
            f"{file_section}\n\n"
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
    required_keys = ['sender_email', 'receiver_email', 'smtp_server', 'smtp_port', 'smtp_password']
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

if __name__ == "__main__":
    try:
        config = {
            'sender_email': os.getenv('SENDER_EMAIL'),
            'receiver_email': os.getenv('RECEIVER_EMAIL'),
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': os.getenv('SMTP_PORT'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'station_id': os.getenv('STATION_ID', '') # Default to empty for all stations
        }

        validate_config(config)
        
        # 1. Scrape the filenames
        file_list = fetch_psws_file_list(config['station_id'])
        
        # 2. Handle potential scrap failure
        if file_list is None:
            file_list = [] # Treat as empty if error occurred
        
        # 3. Send the email
        send_email(config, file_list)
            
    except Exception as e:
        logging.error(f"Major failure: {str(e)}")
        raise
