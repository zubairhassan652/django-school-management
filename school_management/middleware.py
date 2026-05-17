# school_management/middleware.py

from django.utils.deprecation import MiddlewareMixin
from .utils.kafka_logger import kafka_logger
import logging

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Middleware to log user activity"""

    def process_request(self, request):
        """Log request information"""
        if request.user.is_authenticated:
            # Log important actions
            if request.method in ['POST', 'PUT', 'DELETE']:
                try:
                    kafka_logger.log_event(
                        event_type='http_request',
                        user=request.user,
                        action=f"{request.method} {request.path}",
                        details={
                            'ip_address': self.get_client_ip(request),
                            'user_agent': request.META.get('HTTP_USER_AGENT', '')
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log activity: {e}")

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip