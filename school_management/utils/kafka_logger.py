# school_management/utils/kafka_logger.py

from kafka import KafkaProducer
from django.conf import settings
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class KafkaLogger:
    """Kafka logger for system events"""

    def __init__(self):
        self.producer = None
        self.topic = getattr(settings, 'KAFKA_TOPIC', 'school-management-logs')
        self._connect()

    def _connect(self):
        """Connect to Kafka"""
        try:
            kafka_config = getattr(settings, 'KAFKA_CONFIG', {
                'bootstrap_servers': ['localhost:9092'],
            })

            self.producer = KafkaProducer(
                bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
            )

            logger.info("Kafka producer initialized successfully")

        except Exception as e:
            logger.error(f"Kafka connection failed: {e}")
            self.producer = None

    def log_event(self, event_type, user, action, details=None):
        """
        Log event to Kafka

        Args:
            event_type: Type of event (e.g., 'login', 'attendance', 'exam')
            user: User object or username
            action: Action performed
            details: Additional details (dict)
        """
        try:
            if not self.producer:
                logger.warning("Kafka producer not available, skipping log")
                return False

            username = user.username if hasattr(user, 'username') else str(user)

            log_data = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'user': username,
                'action': action,
                'details': details or {}
            }

            # Send to Kafka
            future = self.producer.send(
                self.topic,
                key=event_type,
                value=log_data
            )

            # Wait for send to complete (with timeout)
            future.get(timeout=10)
            logger.info(f"Event logged to Kafka: {event_type} - {action}")
            return True

        except Exception as e:
            logger.error(f"Kafka logging error: {e}")
            return False

    def log_attendance(self, user, student, status, date):
        """Log attendance marking"""
        return self.log_event(
            event_type='attendance',
            user=user,
            action='mark_attendance',
            details={
                'student_id': student.student_id,
                'student_name': student.user.get_full_name(),
                'status': status,
                'date': str(date)
            }
        )

    def log_result(self, user, student, exam, marks):
        """Log result entry"""
        return self.log_event(
            event_type='result',
            user=user,
            action='enter_result',
            details={
                'student_id': student.student_id,
                'exam': str(exam),
                'marks': str(marks)
            }
        )

    def log_login(self, user, ip_address=None):
        """Log user login"""
        return self.log_event(
            event_type='auth',
            user=user,
            action='login',
            details={
                'ip_address': ip_address
            }
        )

    def log_fee_payment(self, user, student, amount, payment_method):
        """Log fee payment"""
        return self.log_event(
            event_type='fee',
            user=user,
            action='payment',
            details={
                'student_id': student.student_id,
                'amount': str(amount),
                'payment_method': payment_method
            }
        )

    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()


# Singleton instance
kafka_logger = KafkaLogger()