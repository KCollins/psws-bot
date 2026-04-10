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

def fetch_psws_summary():
    """
    Scrapes all pages of the PSWS Observation List for yesterday's data.
    """
    yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    base_url = "https://pswsnetwork.eng.ua.edu/observations/observation_list/"
    
    all_observations = []
    page_num = 1
    max_pages = 15 # Safety cap to prevent hitting rate limits too hard

    while page_num <= max_pages:
        # Build URL with the current page number
        query_url = (
            f"{base_url}?station=&startDate__gte={yesterday_date}"
            f"&endDate__lte={yesterday_date}&page={page_num}"
        )
        
        try:
            logging.info(f"Scraping Page {page_num}...")
            response = requests.get(query_url, timeout=30)
            
            # If a page doesn't exist (e.g., page 99), the server usually 
            # returns a 404 or redirects. We stop if that happens.
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'obsTable'})
            
            if not table:
                break

            rows = table.find('tbody').find_all('tr')
            if not rows:
                break
            
            # Extract data from the current page
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    station = cols[2].get_text(strip=True)
                    obs_id = cols[5].get_text(strip=True)
                    all_observations.append(f"{station}: {obs_id}")

            # Check if there's a "Next" page in the pagination UI
            # We look for a link that points to the next page number
            pagination = soup.find('ul', {'class': 'pagination'})
            next_page_str = f"page={page_num + 1}"
            
            if not pagination or next_page_str not in str(pagination):
                logging.info("No more pages found. Stopping.")
                break
                
            page_num += 1

        except Exception as e:
            logging.error(f"Error on page {page_num}: {str(e)}")
            break
            
    return all_observations

def send_email(email_config, observations):
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = email_config['receiver_email']
        msg['Subject'] = f"PSWS Network Overview: {yesterday_str}"
        
        if observations:
            count = len(observations)
            # Create a clean list for the email
            obs_list_text = "\n".join([f"• {item}" for item in observations[:50]]) # Limit to first 50 for readability
            if count > 50:
                obs_list_text += f"\n\n... and {count - 50} more observations."
            
            body_content = f"Yesterday, the network recorded {count} observations:\n\n{obs_list_text}"
        else:
            body_content = "No observations were recorded on the network yesterday."

        body = (
            f"Hello!\n\n"
            f"--- PSWS Daily Network Report ({yesterday_str}) ---\n\n"
            f"{body_content}\n\n"
            f"System check performed at: {current_time} UTC.\n"
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

if __name__ == "__main__":
    try:
        # Load config from environment variables
        config = {
            'sender_email': os.getenv('SENDER_EMAIL'),
            'receiver_email': os.getenv('RECEIVER_EMAIL'),
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': os.getenv('SMTP_PORT'),
            'smtp_password': os.getenv('SMTP_PASSWORD')
        }

        # Validate config
        if not all(config.values()):
            raise ValueError("Missing one or more environment variables.")

        # 1. Scrape the network overview
        obs_data = fetch_psws_summary()
        
        # 2. Send the email
        send_email(config, obs_data if obs_data is not None else [])
            
    except Exception as e:
        logging.error(f"Critical Bot Failure: {str(e)}")
        raise
