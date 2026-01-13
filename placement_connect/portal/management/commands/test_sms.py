"""
Management command to test Twilio SMS configuration.
Usage: python manage.py test_sms --phone +919876543210
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from portal.utils import send_sms, validate_twilio_credentials, format_phone_e164
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test Twilio SMS configuration and send a test message'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Phone number to send test SMS to (e.g., +919876543210 or 9876543210)'
        )

    def handle(self, *args, **options):
        phone = options['phone']
        
        self.stdout.write(self.style.WARNING('Testing Twilio SMS Configuration...'))
        self.stdout.write('-' * 60)
        
        # Step 1: Validate credentials
        self.stdout.write('Step 1: Validating credentials...')
        is_valid, error_msg = validate_twilio_credentials()
        
        if not is_valid:
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            return
        
        self.stdout.write(self.style.SUCCESS('✓ Credentials are configured'))
        self.stdout.write(f'  Account SID: {getattr(settings, "TWILIO_ACCOUNT_SID", "")[:10]}...')
        self.stdout.write(f'  Twilio Number: {getattr(settings, "TWILIO_PHONE_NUMBER", "")}')
        
        # Step 2: Format phone number
        self.stdout.write('\nStep 2: Formatting phone number...')
        formatted_phone = format_phone_e164(phone)
        self.stdout.write(self.style.SUCCESS(f'✓ Formatted: {formatted_phone}'))
        
        # Step 3: Send test SMS
        self.stdout.write('\nStep 3: Sending test SMS...')
        try:
            result = send_sms(
                formatted_phone,
                f"Test message from Placement Portal. Time: {__import__('datetime').datetime.now().isoformat()}"
            )
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('✓ SMS sent successfully!'))
                self.stdout.write(f'  Message ID: {result["message_id"]}')
                self.stdout.write(f'  To: {result["to"]}')
            else:
                self.stdout.write(self.style.ERROR(f'❌ SMS failed: {result.get("error")}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error sending SMS: {str(e)}'))
            logger.exception("Test SMS error")
        
        self.stdout.write('-' * 60)
        self.stdout.write(self.style.SUCCESS('Test complete!'))
