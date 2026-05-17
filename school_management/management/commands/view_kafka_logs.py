# school_management/management/commands/view_kafka_logs.py

from django.core.management.base import BaseCommand
from kafka import KafkaConsumer
from django.conf import settings
import json
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)


class Command(BaseCommand):
    help = 'View Kafka logs in real-time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-beginning',
            action='store_true',
            help='Read all messages from the beginning'
        )
        parser.add_argument(
            '--event-type',
            type=str,
            help='Filter by event type (e.g., attendance, result, auth)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by username'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of messages to display'
        )

    def handle(self, *args, **options):
        kafka_config = getattr(settings, 'KAFKA_CONFIG', {
            'bootstrap_servers': ['localhost:9092'],
        })
        topic = getattr(settings, 'KAFKA_TOPIC', 'school-management-logs')

        self.stdout.write(
            self.style.SUCCESS(f'🎯 Connecting to Kafka: {kafka_config["bootstrap_servers"]}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📝 Topic: {topic}\n')
        )

        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                auto_offset_reset='earliest' if options['from_beginning'] else 'latest',
                enable_auto_commit=True,
                group_id='django-log-viewer'
            )

            self.stdout.write(
                self.style.SUCCESS('✅ Connected! Listening for logs...\n')
            )
            self.stdout.write('=' * 80 + '\n')

            count = 0
            for message in consumer:
                # Check limit
                if options['limit'] and count >= options['limit']:
                    break

                log_data = message.value
                event_type = message.key

                # Filter by event type
                if options['event_type'] and event_type != options['event_type']:
                    continue

                # Filter by user
                if options['user'] and log_data.get('user') != options['user']:
                    continue

                # Display the log
                self.display_log(log_data, event_type)
                count += 1

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n\n👋 Stopped viewing logs.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )

    def display_log(self, log_data, event_type):
        """Display formatted log entry"""
        
        # Color code by event type
        colors = {
            'attendance': Fore.GREEN,
            'result': Fore.BLUE,
            'auth': Fore.CYAN,
            'fee': Fore.YELLOW,
            'http_request': Fore.MAGENTA,
        }
        color = colors.get(event_type, Fore.WHITE)

        # Format timestamp
        timestamp = log_data.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass

        # Print log
        print(f"{color}[{timestamp}] {event_type.upper()}{Style.RESET_ALL}")
        print(f"  User: {log_data.get('user', 'N/A')}")
        print(f"  Action: {log_data.get('action', 'N/A')}")
        
        # Print details
        details = log_data.get('details', {})
        if details:
            print("  Details:")
            for key, value in details.items():
                print(f"    {key}: {value}")
        
        print('-' * 80)