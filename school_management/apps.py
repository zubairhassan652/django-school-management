# school_management/apps.py

from django.apps import AppConfig


class SchoolManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'school_management'
    verbose_name = 'School Management System'

    def ready(self):
        """Import signals when app is ready"""
        import school_management.signals  # noqa