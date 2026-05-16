# school_management/permissions.py

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class RolePermissionManager:
    """Manage role-based permissions"""

    @staticmethod
    def get_user_role(user):
        """Get user role from profile"""
        try:
            return user.school_profile.role
        except:
            return None

    @staticmethod
    def setup_role_permissions():
        """Setup default permissions for each role"""
        from .models import (
            Student, Teacher, Class, Subject, Attendance,
            Exam, Result, Fee, Employee, Department, Profile
        )

        # Student permissions
        student_perms = {
            'view': [Student, Result, Attendance, Fee, Class, Subject],
        }

        # Teacher permissions
        teacher_perms = {
            'view': [Student, Teacher, Class, Subject, Attendance, Exam, Result, Department],
            'add': [Attendance, Exam, Result],
            'change': [Attendance, Result],
        }

        # Employee permissions
        employee_perms = {
            'view': [Student, Teacher, Employee, Class, Department],
            'add': [Student],
            'change': [Student],
        }

        # Admin gets all permissions (handled by Django superuser)

        return {
            'student': student_perms,
            'teacher': teacher_perms,
            'employee': employee_perms,
        }


def has_role_permission(user, model, action):
    """
    Check if user has permission based on role
    
    Args:
        user: Django User object
        model: Model class
        action: 'view', 'add', 'change', 'delete'
    """
    role = RolePermissionManager.get_user_role(user)
    
    if not role:
        return False
    
    # Admins have all permissions
    if role == 'admin' or user.is_superuser:
        return True
    
    permissions = RolePermissionManager.setup_role_permissions()
    role_perms = permissions.get(role, {})
    
    allowed_models = role_perms.get(action, [])
    
    return model in allowed_models