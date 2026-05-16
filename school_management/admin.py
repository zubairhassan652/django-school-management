# school_management/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import (
    Profile, Department, Class, Student, Teacher, Subject,
    ClassSubject, Attendance, Exam, Result, Fee, Employee
)
from .permissions import has_role_permission, RolePermissionManager


class RoleBasedAdminMixin:
    """Mixin to filter admin based on user role"""

    def has_module_permission(self, request):
        """Check if user can see this module in admin"""
        if request.user.is_superuser:
            return True
        
        role = RolePermissionManager.get_user_role(request.user)
        if role == 'admin':
            return True
        
        return has_role_permission(request.user, self.model, 'view')

    def has_view_permission(self, request, obj=None):
        """Check view permission"""
        if request.user.is_superuser:
            return True
        return has_role_permission(request.user, self.model, 'view')

    def has_add_permission(self, request):
        """Check add permission"""
        if request.user.is_superuser:
            return True
        return has_role_permission(request.user, self.model, 'add')

    def has_change_permission(self, request, obj=None):
        """Check change permission"""
        if request.user.is_superuser:
            return True
        return has_role_permission(request.user, self.model, 'change')

    def has_delete_permission(self, request, obj=None):
        """Check delete permission"""
        if request.user.is_superuser:
            return True
        return has_role_permission(request.user, self.model, 'delete')

    def get_queryset(self, request):
        """Filter queryset based on role"""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        role = RolePermissionManager.get_user_role(request.user)
        
        # Students can only see their own data
        if role == 'student':
            if hasattr(self.model, 'student'):
                return qs.filter(student__user=request.user)
            elif self.model.__name__ == 'Student':
                return qs.filter(user=request.user)
        
        # Teachers can see their classes and subjects
        elif role == 'teacher':
            if self.model.__name__ == 'Class':
                return qs.filter(class_teacher=request.user)
            elif self.model.__name__ == 'Student':
                # Teachers can see students in their classes
                return qs.filter(
                    current_class__class_teacher=request.user
                )
        
        return qs


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'School Profile'
    fields = ['role', 'phone_number', 'address', 'date_of_birth']


class CustomUserAdmin(BaseUserAdmin):
    """Custom User Admin with autocomplete support"""
    inlines = [ProfileInline]
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'school_profile__role']
    
    # CRITICAL: Add search_fields for autocomplete
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    def get_role(self, obj):
        try:
            return obj.school_profile.get_role_display()
        except:
            return '-'
    get_role.short_description = 'Role'
    
    # IMPORTANT: Override permission for autocomplete
    def has_view_permission(self, request, obj=None):
        """
        Allow view permission for autocomplete requests
        This fixes the PermissionDenied error
        """
        # Always allow superusers
        if request.user.is_superuser:
            return True
        
        # Allow admin role users
        role = RolePermissionManager.get_user_role(request.user)
        if role == 'admin':
            return True
        
        # Allow staff users to view for autocomplete
        if request.user.is_staff:
            return True
        
        # Default: check parent permission
        return super().has_view_permission(request, obj)
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        if request.path == "/admin/autocomplete/":

            # app_label = request.GET.get("app_label")
            model_name = request.GET.get("model_name")
            field_name = request.GET.get("field_name")

            # Student admin → only student users
            if model_name == "student" and field_name == "user":
                queryset = queryset.filter(
                    school_profile__role="student"
                )

            # Teacher admin → only teacher users
            elif model_name == "teacher" and field_name == "user":
                queryset = queryset.filter(
                    school_profile__role="teacher"
                )

            # Employee admin → only employee users
            elif model_name == "employee" and field_name == "user":
                queryset = queryset.filter(
                    school_profile__role="employee"
                )

        return queryset, use_distinct


# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Profile)
class ProfileAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'role', 'phone_number', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Department)
class DepartmentAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'head', 'teacher_count', 'created_at']
    search_fields = ['name', 'code', 'description']
    list_filter = ['created_at']
    
    def teacher_count(self, obj):
        return obj.teachers.count()
    teacher_count.short_description = 'Teachers'


@admin.register(Class)
class ClassAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['class_name', 'class_teacher', 'get_student_count', 'max_students', 'academic_year']
    list_filter = ['grade', 'academic_year', 'created_at']
    search_fields = ['name', 'grade', 'section', 'academic_year']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'grade', 'section', 'academic_year')
        }),
        ('Assignment', {
            'fields': ('class_teacher', 'max_students')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

    def class_name(self, obj):
        return str(obj)
    
    class_name.short_description = 'Class'

    def get_student_count(self, obj):
        return obj.students.count()

    get_student_count.short_description = "Students"

@admin.register(Student)
class StudentAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'student_id', 'get_full_name', 'current_class',
        'guardian_name', 'admission_date', 'status_badge'
    ]
    list_filter = ['current_class', 'is_active', 'admission_date', 'blood_group']
    search_fields = [
        'student_id', 'user__first_name', 'user__last_name',
        'user__email', 'user__username', 'guardian_name', 'guardian_phone'
    ]
    
    # Now autocomplete will work
    autocomplete_fields = ['user']
    raw_id_fields = ['current_class']
    
    date_hierarchy = 'admission_date'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('user', 'student_id', 'current_class', 'admission_date', 'is_active')
        }),
        ('Guardian Information', {
            'fields': ('guardian_name', 'guardian_phone', 'guardian_email', 'emergency_contact')
        }),
        ('Medical Information', {
            'fields': ('blood_group', 'medical_conditions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Name'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                'Active'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'Inactive'
        )
    status_badge.short_description = 'Status'


@admin.register(Teacher)
class TeacherAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'employee_id', 'get_full_name', 'department',
        'specialization', 'joining_date', 'status_badge'
    ]
    list_filter = ['department', 'is_active', 'joining_date']
    search_fields = [
        'employee_id', 'user__first_name', 'user__last_name',
        'user__username', 'specialization', 'qualification'
    ]
    autocomplete_fields = ['user']
    raw_id_fields = ['department']
    date_hierarchy = 'joining_date'
    
    fieldsets = (
        ('Teacher Information', {
            'fields': ('user', 'employee_id', 'department', 'specialization', 'qualification')
        }),
        ('Employment Details', {
            'fields': ('joining_date', 'salary', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Name'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                'Active'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'Inactive'
        )
    status_badge.short_description = 'Status'


@admin.register(Subject)
class SubjectAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'credits']
    list_filter = ['department', 'credits']
    search_fields = ['name', 'code', 'description']
    raw_id_fields = ['department']


@admin.register(ClassSubject)
class ClassSubjectAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['class_obj', 'subject', 'teacher', 'schedule']
    list_filter = ['class_obj__grade', 'subject__department']
    search_fields = ['class_obj__name', 'subject__name', 'teacher__user__first_name']
    raw_id_fields = ['class_obj', 'subject', 'teacher']


@admin.register(Attendance)
class AttendanceAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = ['student', 'date', 'status_badge', 'marked_by', 'created_at']
    list_filter = ['status', 'date', 'student__current_class']
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name']
    date_hierarchy = 'date'
    raw_id_fields = ['student', 'marked_by']
    
    def status_badge(self, obj):
        colors = {
            'present': '#28a745',
            'absent': '#dc3545',
            'late': '#ffc107',
            'excused': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Auto-set marked_by to current user"""
        if not obj.pk:
            obj.marked_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Exam)
class ExamAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'name', 'exam_type', 'class_obj', 'subject',
        'date', 'max_marks', 'duration_minutes'
    ]
    list_filter = ['exam_type', 'date', 'class_obj__grade']
    search_fields = ['name', 'class_obj__name', 'subject__name']
    date_hierarchy = 'date'
    raw_id_fields = ['class_obj', 'subject']


@admin.register(Result)
class ResultAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'student', 'exam', 'marks_obtained', 'max_marks',
        'grade_badge', 'created_at'
    ]
    list_filter = ['exam__exam_type', 'grade', 'exam__date']
    search_fields = [
        'student__student_id', 'student__user__first_name',
        'exam__name'
    ]
    raw_id_fields = ['student', 'exam']
    
    def max_marks(self, obj):
        return obj.exam.max_marks
    max_marks.short_description = 'Max Marks'
    
    def grade_badge(self, obj):
        colors = {
            'A+': '#28a745',
            'A': '#28a745',
            'B': '#17a2b8',
            'C': '#ffc107',
            'D': '#fd7e14',
            'F': '#dc3545',
        }
        color = colors.get(obj.grade, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.grade
        )
    grade_badge.short_description = 'Grade'


@admin.register(Fee)
class FeeAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'student', 'fee_type', 'amount', 'due_date',
        'payment_status', 'payment_date'
    ]
    list_filter = ['fee_type', 'paid', 'due_date']
    search_fields = [
        'student__student_id', 'student__user__first_name',
        'transaction_id'
    ]
    date_hierarchy = 'due_date'
    raw_id_fields = ['student']
    
    def payment_status(self, obj):
        if obj.paid:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                'Paid'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'Pending'
        )
    payment_status.short_description = 'Status'


@admin.register(Employee)
class EmployeeAdmin(RoleBasedAdminMixin, admin.ModelAdmin):
    list_display = [
        'employee_id', 'get_full_name', 'employee_type',
        'designation', 'joining_date', 'status_badge'
    ]
    list_filter = ['employee_type', 'is_active', 'joining_date']
    search_fields = [
        'employee_id', 'user__first_name', 'user__last_name',
        'user__username', 'designation', 'department'
    ]
    autocomplete_fields = ['user']
    date_hierarchy = 'joining_date'
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Name'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                'Active'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            'Inactive'
        )
    status_badge.short_description = 'Status'


# Customize admin site
admin.site.site_header = 'School Management System'
admin.site.site_title = 'School Admin'
admin.site.index_title = 'Welcome to School Management System'