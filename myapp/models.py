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

POSITIONS = [
    ('President', 'President'),
    ('Vice President', 'Vice President'),
    ('Senator', 'Senator'),
    ('Governor', 'Governor'),
]

class Candidate(models.Model):
    academic_year = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    section = models.CharField(max_length=50)
    tupc_id = models.CharField(max_length=40)
    position = models.CharField(max_length=20, choices=POSITIONS)
    photo = models.ImageField(upload_to='candidate_photos/')

    def __str__(self):
        return f"{self.name} - {self.position}"
    
    class Meta:
        db_table = 'candidate'
        
class Violation(models.Model):
    VIOLATION_TYPES = [
    ("Disturbance", "Causing Disturbance During Class Hours"),
    ("Proper Uniform", "Not Wearing Proper Uniform and ID"),
    ("Cross Dressing", "Cross Dressing in Uniform and Wash Days"),
    ("Facial Hair", "Unwanted Facial Hair"),
    ("Earrings", "Wearing of Earrings or Multiple Earrings"),
    ("Caps", "Wearing of Caps or Hats inside Covered Facilities"),
    ("Entering Classroom", "Entering Classrooms without Permission from Instructor"),
    ("Leaving Classroom", "Leaving Classrooms without Permission from Instructor"),
    ("Attempt Fraternity", "Attempting to Join a Fraternity"),
    ("Posting Materials", "Unauthorized Posting Printed Materials"),
    ("Use of University Facilities", "Unauthorized Use of University Facilities"),
    ("Official Notices", "Unauthorized Removal of Official Notices and Posters"),
    ("Gambling", "Possession of Gambling Paraphernalia"),
    ("Devices", "Unauthorized Use of Devices during Class"),
    ("Resources", "Irresponsible Use of Water and Electricity within University"),
    ("Harrassment", "Making Lewd Gestures and Lustful Words to a Student"),
    ("Property Damage", "Accidental Damage of University Property"),
    ("PDA", "Public Display of Physical Intimacy or Affection"),
    ("Cigarette", "Possession of Any type of Cigarette or Tobacco inside University"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    first_name = models.CharField(max_length=50, blank=False)
    middle_initial = models.CharField(max_length=10, blank=True)
    extension_name = models.CharField(max_length=10, blank=True)
    last_name = models.CharField(max_length=50, blank=False)
    student_id = models.CharField(max_length=20, blank=False)
    program_course = models.CharField(max_length=100, blank=False)
    violation_date = models.DateField(blank=False)
    violation_time = models.TimeField(blank=False)
    violation_type = models.CharField(max_length=150, choices=VIOLATION_TYPES, blank=False)
    guard_name = models.CharField(max_length=100, blank=False)
    evidence_1 = models.ImageField(upload_to='evidence/', null=False, blank=False)
    evidence_2 = models.ImageField(upload_to='evidence/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.violation_type} ({self.status})"
    class Meta:
        db_table = 'violation'


class ViolationSettlement(models.Model):
    violation = models.OneToOneField(
        Violation,
        on_delete=models.CASCADE,
        related_name='settlement'
    )
    settlement_type = models.CharField(
        max_length=50,
        choices=[
            ('Apology Letter', 'Apology Letter'),
            ('Community Service', 'Community Service'),
        ]
    )
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'violation_settlement'

    def __str__(self):
        return f"{self.violation.student_id} - {self.settlement_type} - {'Settled' if self.is_settled else 'Unsettled'}"
        
class Scholarship(models.Model):
    CATEGORY_CHOICES = [
        ('Internal', 'Internal'),
        ('External Govt', 'External (Govt)'),
        ('External Private', 'External (Private)'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    posted_date = models.DateField(auto_now_add=True)
    deadline_date = models.DateField()

    attachment_1 = models.FileField(upload_to='scholarship_attachments/', blank=True, null=True)
    attachment_2 = models.FileField(upload_to='scholarship_attachments/', blank=True, null=True)
    attachment_3 = models.FileField(upload_to='scholarship_attachments/', blank=True, null=True)
    attachment_4 = models.FileField(upload_to='scholarship_attachments/', blank=True, null=True)
    attachment_5 = models.FileField(upload_to='scholarship_attachments/', blank=True, null=True)

    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'scholarship'
        
class LostAndFound(models.Model):
    description = models.TextField()
    image = models.ImageField(upload_to='lostandfound_images/', blank=True, null=True)
    posted_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lost & Found ({self.posted_date.date()})"
    
    class Meta:
        db_table = 'lostandfound'

class GoodMoralRequest(models.Model):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    surname = models.CharField(max_length=50)
    ext = models.CharField(max_length=10, blank=True)
    sex = models.CharField(max_length=10)
    student_id = models.CharField(max_length=20)
    program = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    date_graduated = models.DateField(null=True, blank=True)
    inclusive_years = models.CharField(max_length=20, blank=True)
    date_admission = models.DateField(null=True, blank=True)
    purpose = models.CharField(max_length=100)
    requester_name = models.CharField(max_length=100)
    requester_email = models.EmailField()
    requester_contact = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50)

    # New
    document_type = models.CharField(max_length=30, default='unknown')
    uploaded_file = models.FileField(upload_to='uploads/goodmoral/', default='uploads/goodmoral/default.pdf')

    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.surname} - {self.student_id}"
    
    class Meta:
        db_table = 'goodmoral'
        
class StudentAssistantshipRequirement(models.Model):
    content = models.TextField("Requirements Text")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Student Assistantship Requirements"
    
    class Meta:
        db_table = 'studentassistant'
        
class ACSORequirement(models.Model):
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ACSO Requirement (Last updated: {self.last_updated})"
    
    class Meta:
        db_table = 'acso'