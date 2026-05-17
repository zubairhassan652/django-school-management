# school_management/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Attendance, Result, Fee, Profile
from .utils.kafka_logger import kafka_logger
from .utils.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Attendance)
def log_attendance_event(sender, instance, created, **kwargs):
    """Log attendance events to Kafka"""
    if created:
        try:
            kafka_logger.log_attendance(
                user=instance.marked_by,
                student=instance.student,
                status=instance.status,
                date=instance.date
            )
        except Exception as e:
            logger.error(f"Failed to log attendance event: {e}")


@receiver(post_save, sender=Result)
def log_result_event(sender, instance, created, **kwargs):
    """Log result entry to Kafka"""
    if created:
        try:
            kafka_logger.log_result(
                user=instance.exam.class_obj.class_teacher,
                student=instance.student,
                exam=instance.exam,
                marks=instance.marks_obtained
            )
        except Exception as e:
            logger.error(f"Failed to log result event: {e}")


@receiver(post_save, sender=Fee)
def log_fee_payment(sender, instance, created, **kwargs):
    """Log fee payment to Kafka"""
    if instance.paid and not created:
        try:
            kafka_logger.log_fee_payment(
                user=instance.student.user,
                student=instance.student,
                amount=instance.amount,
                payment_method=instance.payment_method
            )
        except Exception as e:
            logger.error(f"Failed to log fee payment: {e}")


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Create profile when user is created"""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=Attendance)
def invalidate_attendance_cache(sender, instance, **kwargs):
    """Invalidate Redis cache when attendance is updated"""
    try:
        cache_key = f"attendance:student:{instance.student.id}:month:{instance.date.strftime('%Y-%m')}"
        redis_client.delete(cache_key)
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")