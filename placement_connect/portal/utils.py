import os
import time
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings

logger = logging.getLogger(__name__)

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)


def format_phone_e164(phone_number):
    """
    Convert phone number to E.164 format (e.g., +91767619xxxx).
    
    Args:
        phone_number (str): Phone number in any format
        
    Returns:
        str: Phone number in E.164 format
    """
    if not phone_number:
        return None
        
    phone = str(phone_number).strip().replace(' ', '').replace('-', '')
    
    if phone.startswith('+'):
        return phone
    
    # Remove leading zeros
    phone = phone.lstrip('0')
    
    # If it starts with 91 and is 12 chars, it's already country code + 10-digit number
    if phone.startswith('91') and len(phone) == 12:
        return f"+{phone}"
    
    # If it's 10 digits, assume Indian number
    if len(phone) == 10:
        return f"+91{phone}"
    
    # If it starts with 91, add the +
    if phone.startswith('91'):
        return f"+{phone}"
    
    # Fallback: add country code
    country_code = getattr(settings, 'SMS_DEFAULT_COUNTRY_CODE', '+91')
    return f"{country_code}{phone}"


def validate_twilio_credentials():
    """
    Validate that all required Twilio credentials are configured.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '').strip()
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '').strip()
    twilio_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '').strip()
    
    if not all([account_sid, auth_token, twilio_number]):
        missing = []
        if not account_sid:
            missing.append('TWILIO_ACCOUNT_SID')
        if not auth_token:
            missing.append('TWILIO_AUTH_TOKEN')
        if not twilio_number:
            missing.append('TWILIO_PHONE_NUMBER')
        
        error_msg = f"Missing Twilio credentials: {', '.join(missing)}. Please configure these in your .env file."
        logger.error(error_msg)
        return False, error_msg
    
    return True, None


def send_sms(to_number, message_body, retry_count=0):
    """
    Sends an SMS using Twilio with E.164 formatted phone numbers.
    Includes retry logic for transient failures.
    
    Args:
        to_number (str): Recipient phone number
        message_body (str): Message content
        retry_count (int): Current retry attempt (internal use)
        
    Returns:
        dict: Success status and message details
        
    Raises:
        Exception: If SMS sending fails after retries
    """
    
    # Check if SMS is enabled
    if not getattr(settings, 'SMS_ENABLED', True):
        logger.info("SMS is disabled. Message not sent.")
        return {
            'success': False,
            'error': 'SMS is disabled',
            'message_id': None
        }
    
    # Validate credentials
    is_valid, error_msg = validate_twilio_credentials()
    if not is_valid:
        logger.warning(f"SMS credentials not configured - Running in demo mode: {error_msg}")
        logger.info(f"[DEMO MODE] Would send SMS to {to_number}: {message_body}")
        return {
            'success': True,
            'message_id': 'DEMO_MODE_' + __import__('uuid').uuid4().hex[:12].upper(),
            'to': format_phone_e164(to_number),
            'mode': 'demo'
        }
    
    # Get credentials
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN')
    twilio_number = getattr(settings, 'TWILIO_PHONE_NUMBER')
    
    # Format recipient number
    formatted_number = format_phone_e164(to_number)
    if not formatted_number:
        error_msg = "Invalid recipient phone number"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Sending SMS to {formatted_number} (attempt {retry_count + 1})")
    
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=twilio_number,
            to=formatted_number
        )
        
        logger.info(f"SMS sent successfully. SID: {message.sid}, To: {formatted_number}")
        return {
            'success': True,
            'message_id': message.sid,
            'to': formatted_number,
            'timestamp': message.date_sent
        }
        
    except TwilioRestException as e:
        error_msg = f"Twilio Error {e.code}: {e.msg}"
        logger.error(error_msg)
        
        # Retry logic for specific error codes (transient failures)
        max_retries = getattr(settings, 'SMS_RETRY_ATTEMPTS', 3)
        retry_delay = getattr(settings, 'SMS_RETRY_DELAY', 5)
        
        # Retry on rate limiting (429) or server errors (5xx)
        if (e.code in [429, 500, 502, 503, 504] and retry_count < max_retries):
            logger.warning(f"Retrying SMS after {retry_delay} seconds... (Attempt {retry_count + 1}/{max_retries})")
            time.sleep(retry_delay)
            return send_sms(to_number, message_body, retry_count + 1)
        
        raise Exception(f"Twilio Error {e.code}: {e.msg}")
        
    except Exception as e:
        error_msg = f"SMS Error: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def send_sms_bulk(recipients, message_body):
    """
    Sends SMS to multiple recipients with batch processing.
    
    Args:
        recipients (list): List of phone numbers
        message_body (str): Message content
        
    Returns:
        dict: Summary of sent/failed messages
    """
    results = {
        'sent': [],
        'failed': [],
        'total': len(recipients)
    }
    
    batch_size = getattr(settings, 'SMS_BATCH_SIZE', 10)
    
    for i, phone_number in enumerate(recipients):
        try:
            result = send_sms(phone_number, message_body)
            if result['success']:
                results['sent'].append(phone_number)
            else:
                results['failed'].append({'phone': phone_number, 'reason': result.get('error')})
        except Exception as e:
            results['failed'].append({'phone': phone_number, 'reason': str(e)})
        
        # Add delay between batches to avoid rate limiting
        if (i + 1) % batch_size == 0 and (i + 1) < len(recipients):
            logger.info(f"Batch complete. Waiting before next batch...")
            time.sleep(1)
    
    logger.info(f"Bulk SMS Summary - Sent: {len(results['sent'])}, Failed: {len(results['failed'])}, Mode: {results.get('mode', 'production')}")
    return results


def notify_student_approval(student_profile):
    """
    Sends approval notification to a student.
    
    Args:
        student_profile (StudentProfile): Student profile object
        
    Returns:
        dict: SMS send result
    """
    message = (
        f"Congratulations! Your Placement Portal account has been approved. "
        f"You can now view and apply for job opportunities. Good luck!"
    )
    
    try:
        result = send_sms(student_profile.phone, message)
        if result.get('mode') == 'demo':
            logger.info(f"[DEMO] Approval notification for {student_profile.user.username}")
        return result
    except Exception as e:
        logger.error(f"Failed to notify student {student_profile.user.username}: {str(e)}")
        raise


def notify_student_rejection(student_profile):
    """
    Sends rejection notification to a student.
    
    Args:
        student_profile (StudentProfile): Student profile object
        
    Returns:
        dict: SMS send result
    """
    message = (
        f"Unfortunately, your registration has been rejected. "
        f"Please contact the placement office for more information."
    )
    
    try:
        result = send_sms(student_profile.phone, message)
        if result.get('mode') == 'demo':
            logger.info(f"[DEMO] Rejection notification for {student_profile.user.username}")
        return result
    except Exception as e:
        logger.error(f"Failed to notify rejection for student {student_profile.user.username}: {str(e)}")
        raise


def notify_application_update(application):
    """
    Sends application status update to student.
    
    Args:
        application (Application): Application object
        
    Returns:
        dict: SMS send result
    """
    message = (
        f"Application Update: Your status for {application.job.company} has been "
        f"updated to '{application.status}'. Check the portal for details."
    )
    
    try:
        result = send_sms(application.student.phone, message)
        if result.get('mode') == 'demo':
            logger.info(f"[DEMO] Status update notification for {application.student.user.username}")
        return result
    except Exception as e:
        logger.error(f"Failed to notify {application.student.user.username}: {str(e)}")
        raise


def notify_new_job_posting(job_posting, recipient_phones):
    """
    Notifies eligible students about a new job posting.
    
    Args:
        job_posting (JobPosting): Job posting object
        recipient_phones (list): List of student phone numbers
        
    Returns:
        dict: Bulk SMS results
    """
    message = (
        f"New Opportunity! {job_posting.company} is hiring for {job_posting.title}. "
        f"Package: {job_posting.package_range}. Apply now on the portal!"
    )
    
    try:
        return send_sms_bulk(recipient_phones, message)
    except Exception as e:
        logger.error(f"Failed to notify about job posting {job_posting.id}: {str(e)}")
        raise
