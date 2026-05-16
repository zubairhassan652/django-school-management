# school_management/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base class with created and updated timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Profile(TimeStampedModel):
    """Extended user profile with role"""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('employee', 'Employee'),
        ('admin', 'Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='school_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    class Meta: # type: ignore[override]
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['user', 'role']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"


class Department(TimeStampedModel):
    """Academic departments"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        limit_choices_to={'school_profile__role': 'teacher'}
    )

    class Meta: # type: ignore[override]
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Class(TimeStampedModel):
    """Classes/Grades"""
    name = models.CharField(max_length=50)
    grade = models.CharField(max_length=10)
    section = models.CharField(max_length=5)
    academic_year = models.CharField(max_length=9)  # e.g., "2024-2025"
    class_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teaching_classes',
        limit_choices_to={'school_profile__role': 'teacher'}
    )
    max_students = models.IntegerField(default=40)

    class Meta: # type: ignore[override]
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        unique_together = ['grade', 'section', 'academic_year']
        ordering = ['grade', 'section']

    def __str__(self):
        return f"Grade {self.grade} - {self.section} ({self.academic_year})"

    @property
    def student_count(self):
        return self.students.count()


class Student(TimeStampedModel):
    """Student information"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    student_id = models.CharField(max_length=20, unique=True)
    current_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        related_name='students'
    )
    admission_date = models.DateField()
    guardian_name = models.CharField(max_length=100)
    guardian_phone = models.CharField(max_length=15)
    guardian_email = models.EmailField(blank=True)
    emergency_contact = models.CharField(max_length=15)
    blood_group = models.CharField(max_length=5, blank=True)
    medical_conditions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta: # type: ignore[override]
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['student_id']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['current_class', 'is_active']),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name()}"


class Teacher(TimeStampedModel):
    """Teacher information"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='teachers'
    )
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200)
    joining_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta: # type: ignore[override]
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department', 'is_active']),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


class Subject(TimeStampedModel):
    """Subjects taught in school"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    credits = models.IntegerField(default=1)
    description = models.TextField(blank=True)

    class Meta: # type: ignore[override]
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class ClassSubject(TimeStampedModel):
    """Subjects assigned to classes with teachers"""
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='class_subjects'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='subject_classes'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_subjects'
    )
    schedule = models.CharField(max_length=100, blank=True)  # e.g., "Mon-Wed-Fri 10:00-11:00"

    class Meta:  # type: ignore[override]
        verbose_name = 'Class Subject'
        verbose_name_plural = 'Class Subjects'
        unique_together = ['class_obj', 'subject']

    def __str__(self):
        return f"{self.class_obj} - {self.subject}"


class Attendance(TimeStampedModel):
    """Daily attendance records"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='marked_attendance'
    )

    class Meta: # type: ignore[override]
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ['student', 'date']
        ordering = ['-date', 'student']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['student', 'date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.date} ({self.get_status_display()})"


class Exam(TimeStampedModel):
    """Examinations"""
    EXAM_TYPE_CHOICES = [
        ('midterm', 'Mid Term'),
        ('final', 'Final'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
    ]

    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='exams'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exams'
    )
    date = models.DateField()
    max_marks = models.IntegerField(default=100)
    passing_marks = models.IntegerField(default=40)
    duration_minutes = models.IntegerField(default=60)

    class Meta: # type: ignore[override]
        verbose_name = 'Exam'
        verbose_name_plural = 'Exams'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'class_obj']),
        ]

    def __str__(self):
        return f"{self.name} - {self.class_obj} - {self.subject}"


class Result(TimeStampedModel):
    """Exam results"""
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='results'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='results'
    )
    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    grade = models.CharField(max_length=2, blank=True)
    remarks = models.TextField(blank=True)

    class Meta: # type: ignore[override]
        verbose_name = 'Result'
        verbose_name_plural = 'Results'
        unique_together = ['exam', 'student']
        ordering = ['-exam__date', '-marks_obtained']

    def __str__(self):
        return f"{self.student} - {self.exam} - {self.marks_obtained}/{self.exam.max_marks}"

    def save(self, *args, **kwargs):
        """Auto-calculate grade"""
        percentage = (self.marks_obtained / self.exam.max_marks) * 100
        if percentage >= 90:
            self.grade = 'A+'
        elif percentage >= 80:
            self.grade = 'A'
        elif percentage >= 70:
            self.grade = 'B'
        elif percentage >= 60:
            self.grade = 'C'
        elif percentage >= 50:
            self.grade = 'D'
        else:
            self.grade = 'F'
        super().save(*args, **kwargs)


class Fee(TimeStampedModel):
    """Fee structure"""
    FEE_TYPE_CHOICES = [
        ('tuition', 'Tuition Fee'),
        ('admission', 'Admission Fee'),
        ('exam', 'Examination Fee'),
        ('transport', 'Transport Fee'),
        ('library', 'Library Fee'),
        ('lab', 'Laboratory Fee'),
        ('other', 'Other'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='fees'
    )
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    class Meta: # type: ignore[override]
        verbose_name = 'Fee'
        verbose_name_plural = 'Fees'
        ordering = ['-due_date']
        indexes = [
            models.Index(fields=['student', 'paid']),
            models.Index(fields=['due_date', 'paid']),
        ]

    def __str__(self):
        status = "Paid" if self.paid else "Pending"
        return f"{self.student} - {self.get_fee_type_display()} - {status}"


class Employee(TimeStampedModel):
    """Non-teaching staff"""
    EMPLOYEE_TYPE_CHOICES = [
        ('admin', 'Administrative Staff'),
        ('support', 'Support Staff'),
        ('it', 'IT Staff'),
        ('maintenance', 'Maintenance'),
        ('security', 'Security'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True)
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    joining_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta: # type: ignore[override]
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"