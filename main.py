import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

# Configuring the logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def send_email(email_config):
    try:
        # Get current datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        msg = MIMEMultipart()
        msg['From'] = email_config['sender_email']
        msg['To'] = email_config['receiver_email']
        msg['Subject'] = f"Daily Notification - {current_time}"
        
        body = (
            "Hello!\n\n"
            f"This is your daily automated message. The current system time is: {current_time}.\n\n"
            "Everything is running smoothly! 🚀\n"
            "— Your GitHub Bot"
        )
        
        msg.attach(MIMEText(body, 'plain')) 
      
        # --- NEW CONNECTION LOGIC FOR GMAIL (PORT 587) ---
        # Initialize connection
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'], timeout=15)
        
        # Upgrade the connection to secure TLS
        server.starttls() 
        
        with server:
            # Log in using the 16-character App Password
            server.login(email_config['sender_email'], email_config['smtp_password']) 
            server.send_message(msg)
            logging.info("Email sent successfully")
        # ------------------------------------------------
          
    except (smtplib.SMTPException, Exception) as e: 
        logging.error(f"Failed to send email: {str(e)}")
        raise

def validate_config(config):
    required_keys = ['sender_email', 'receiver_email', 'smtp_server', 'smtp_port', 'smtp_password']
    missing = [key for key in required_keys if not config.get(key) or str(config.get(key)).strip() == ""]

    if missing:
        logging.error(f"Missing configuration: {', '.join(missing)}")
        raise ValueError("Missing environment variables")

    try:
        config['smtp_port'] = int(config['smtp_port'])
    except ValueError:
        logging.error("Invalid SMTP_PORT value")
        raise
      
if __name__ == "__main__":
    try:
        config = {
            'sender_email': os.getenv('SENDER_EMAIL'),
            'receiver_email': os.getenv('RECEIVER_EMAIL'),
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': os.getenv('SMTP_PORT'),
            'smtp_password': os.getenv('SMTP_PASSWORD')
        }

        validate_config(config)
        logging.info("Configuration validated successfully")
      
        send_email(config)
            
    except Exception as e:
        logging.error(f"Major failure: {str(e)}")
        raise
