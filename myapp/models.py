from django.db import models
import random
import string

class Student(models.Model):
    tupc_id = models.CharField(max_length=50, unique=True)
    program = models.CharField(max_length=50)
    last_name = models.CharField(max_length=128)
    first_name = models.CharField(max_length=128)
    middle_initial = models.CharField(max_length=5, blank=True, null=True)
    extension = models.CharField(max_length=10, blank=True, null=True)
    email = models.EmailField(unique=True)
    
    class Meta:
        db_table = 'student_record'

    def __str__(self):
        return f"{self.tupc_id} - {self.last_name}, {self.first_name}"

class UserAccount(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('comselec', 'COMSELEC'),
        ('guard', 'Security Guard'),
        ('scholarship', 'Scholarship Coordinator'),
    ]

    full_name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # You can hash this
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'user_accounts'
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
class OTPVerification(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    full_name = models.CharField(max_length=128)
    role = models.CharField(max_length=20)
    password = models.CharField(max_length=128)  # store temporarily
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    class Meta:
        db_table = 'OTPVerification'
    def __str__(self):
        return f"{self.email} - OTP: {self.otp}"
    
class Archived_Account(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6, blank=True, null=True)  # Optional if no longer needed
    full_name = models.CharField(max_length=128)
    role = models.CharField(max_length=20)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = 'archive_account'

    def __str__(self):
        return f"{self.email} ({'Active' if self.is_active else 'Deactivated'})"
