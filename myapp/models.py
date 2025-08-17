from django.db import models
import random
import string
from django.core.validators import RegexValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.db.models.functions import Now
from django.utils import timezone
from django.db import transaction

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
    # --- constants/choices
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
        
        ("Liquor/Drugs", "Liquor and Prohibited Drugs"),
        ("Illegal Assembly", "Unauthorized Activities/ Illegal Assemblies"),
        ("Weapons", "Deadly and Dangerous Weapons"),
        ("Threats/Coercion", "Threats/Coercion"),
        ("Swindling", "Swindling"),
        ("Funds Misuse", "Misuse of/ Failure to Account Funds"),
        ("Assault/Injury", "Violence and Physical Assault/Injury"),
        ("Robbery/Theft", "Robbery/ Theft"),
        ("Damage to Property (Major)", "Damage to Property"),
        ("Forced Entry", "Forcible or Unauthorized entry into the TUP premises"),
        ("Cybercrime", "Commission of Cyber crimes as defined under R.A. No. 10175"),
        ("Slander/Libel", "Slander/Libel/Gossip"),
        ("Falsification", "Falsification of documents, records and credentials"),
        ("Academic Dishonesty", "Academic Dishonesty"),
        ("Immoral Acts", "Immoral Acts"),
        ("Gambling (Major)", "Gambling"),
        ("Misrepresentation", "False representation or Misrepresentation"),
        ("Disrespect", "Acts of Disrespect"),
        ("Bribery", "Offering or Giving Bribes"),
        ("Smoking (Major)", "Smoking within the University premises of any type of cigarette or tabacco product"),
        ("Littering", "Littering within the University premises"),
        ("Borrowed ID", "Entering the University premises with a borrowed ID or registration form"),
        ("Lending ID", "Leading of ID/ registration form to facilitate the entry of another student into the University premises"),
        ("4th Minor", "Commission of the same or any minor offense for the 4th time"),
        ("Probation Major", "Commission of major offense while under academic probation"),
        ("Final Conviction", "Final conviction of any offense punishable under the Revised Penal Code, special penal laws or ordinances"),
    ]
    
    STATUS_CHOICES = [("Pending","Pending"), ("Approved","Approved"), ("Rejected","Rejected")]
    SEVERITY_CHOICES = [("MINOR","Minor"), ("MAJOR","Major")]  # future-proof; guards submit MINOR
    SETTLEMENT_CHOICES = [
        ("None", "None"),
        ("Apology Letter", "Apology Letter"),
        ("Community Service", "Community Service"),
    ]

    # --- identity
    first_name = models.CharField(max_length=50)
    middle_initial = models.CharField(max_length=10, blank=True)
    extension_name = models.CharField(max_length=10, blank=True)
    last_name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=20, db_index=True)
    program_course = models.CharField(max_length=100)

    # --- violation facts
    violation_date = models.DateField()
    violation_time = models.TimeField()
    violation_type = models.CharField(max_length=150, choices=VIOLATION_TYPES)
    guard_name = models.CharField(max_length=100)
    severity = models.CharField(max_length=5, choices=SEVERITY_CHOICES, default="MINOR")

    evidence_1 = models.ImageField(upload_to='evidence/', null=True, blank=True)
    evidence_2 = models.ImageField(upload_to='evidence/', null=True, blank=True)

    # --- workflow
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=100, blank=True)

    # --- settlement (merged from ViolationSettlement)
    settlement_type = models.CharField(max_length=50, choices=SETTLEMENT_CHOICES, default="None")
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)

    # --- meta
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'violation'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['student_id', 'status']),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.violation_type} ({self.status})"

    # helpers
    def mark_approved(self, by_user: str):
        if self.status != "Approved":
            now = timezone.now()
            self.status = "Approved"
            self.reviewed_at = now
            self.approved_at = now
            self.approved_by = by_user or ""
            self.save(update_fields=["status","reviewed_at","approved_at","approved_by"])
        
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
    date_admission = models.CharField(max_length=20, null=True, blank=True)
    purpose = models.CharField(max_length=100)
    requester_name = models.CharField(max_length=100)
    requester_email = models.EmailField()
    requester_contact = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50)
    other_purpose = models.CharField(max_length=100, blank=True, null=True)
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
           
def validate_file_size(f):
    limit_mb = 10
    if f.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Max file size is {limit_mb} MB.")
    
class IDSurrenderRequest(models.Model):
    DOC_ID = "id"
    DOC_AFFIDAVIT = "affidavit"
    DOCUMENT_TYPE_CHOICES = [
        (DOC_ID, "School ID"),
        (DOC_AFFIDAVIT, "Affidavit of Loss"),
    ]
    document_type = models.CharField(
        max_length=16,
        choices=DOCUMENT_TYPE_CHOICES,
        db_index=True,
        default=DOC_ID,  
    )

    STATUS_PENDING   = "pending"
    STATUS_APPROVED  = "approved"
    STATUS_DECLINED  = "declined"
    STATUS_CHOICES = [
        (STATUS_PENDING,  "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DECLINED, "Declined"),
    ]

    REASON_CHOICES = [
        ("Dropped", "Dropped"),
        ("Graduate", "Graduate"),
        ("Transfer", "Transfer"),
        ("Withdrawn", "Withdrawn"),
        ("Claim of Credentials", "Claim of Credentials"),
        ("Worn Out", "Worn Out"),
    ]

    YEAR_LEVEL_CHOICES = [
        ("1st Year", "1st Year"),
        ("2nd Year", "2nd Year"),
        ("3rd Year", "3rd Year"),
        ("4th Year", "4th Year"),
        ("5th Year", "5th Year"),
        ("Graduate", "Graduate"),
    ]

    # --- Personal Information ---
    first_name   = models.CharField(max_length=50)
    middle_name  = models.CharField(max_length=50, blank=True)
    surname      = models.CharField(max_length=50)
    extension    = models.CharField(max_length=10, blank=True)  # Jr., Sr., etc.
    program      = models.CharField(max_length=100)
    contact_email = models.EmailField(max_length=254, blank=True, null=True, db_index=True)

    # --- Academic Information ---
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    student_number = models.CharField(
        max_length=18,
        validators=[RegexValidator(r"^TUPC-\d{2}-\d{4,10}$", message="Format: TUPC-XX-XXXX up to TUPC-XX-XXXXXXXXXX.")],
        db_index=True,  
    )
    year_level = models.CharField(max_length=12, choices=YEAR_LEVEL_CHOICES)
    inclusive_years = models.CharField(
        max_length=9,
        validators=[RegexValidator(r"^\d{4}-\d{4}$", message="Use YYYY-YYYY (e.g., 2019-2023).")]
    )

    # --- Uploads ---
    upload_id_front = models.FileField(
        upload_to="surrender_ids/%Y/%m/%d/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "pdf"]), validate_file_size],
        blank=True, null=True,
    )
    upload_id_back = models.FileField(
        upload_to="surrender_ids/%Y/%m/%d/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "pdf"]), validate_file_size],
        blank=True, null=True,
    )

    status   = models.CharField(max_length=8, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    message  = models.TextField(blank=True) 
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledgement_receipt = models.FileField(
    upload_to="surrender_ids/receipts/%Y/%m/%d/",
    validators=[FileExtensionValidator(["pdf"]), validate_file_size],
    null=True, blank=True,)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status", "submitted_at"]),
        ]
        verbose_name = "ID Surrender Request"
        verbose_name_plural = "ID Surrender Requests"
        db_table = 'Surrender_ID'
        
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.document_type == self.DOC_ID:
            if not self.upload_id_front:
                raise ValidationError({"upload_id_front": "Front ID is required."})
            if not self.upload_id_back:
                raise ValidationError({"upload_id_back": "Back ID is required."})
        elif self.document_type == self.DOC_AFFIDAVIT:
            if not self.upload_id_front:
                raise ValidationError({"upload_id_front": "Affidavit first page is required."})
        
    def __str__(self):
        return f"{self.student_number} — {self.surname}, {self.first_name} ({self.status})"

def _q_half(x: Decimal) -> Decimal:
    """Round to nearest 0.5 hours."""
    return (Decimal(x) * Decimal(2)).quantize(Decimal('1')) / Decimal(2)

class CommunityServiceCase(models.Model):
    """
    One active community service case per student.
    total_required_hours goes up with manual assignments.
    hours_completed never resets (remaining = total - completed).
    """
    # INSERTED: denormalized student snapshot (admin types these)
    last_name = models.CharField(max_length=50, default="", blank=True)
    first_name = models.CharField(max_length=50, default="", blank=True)
    middle_initial = models.CharField(max_length=10, default="", blank=True)   # optional
    extension_name = models.CharField(max_length=10, default="", blank=True)   # optional
    program_course = models.CharField(max_length=100, default="", blank=True)

    # (kept) student id
    student_id = models.CharField(max_length=20, db_index=True)

    total_required_hours = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    hours_completed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    is_closed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "community_service_case"
        indexes = [
            models.Index(fields=["student_id", "is_closed"]),
            # INSERTED: quick name search
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        # UPDATED: include snapshot name
        full = f"{self.last_name}, {self.first_name}".strip(", ")
        return f"{full} ({self.student_id}) | required={self.total_required_hours} done={self.hours_completed}"

    @property
    def remaining_hours(self) -> Decimal:
        rem = self.total_required_hours - self.hours_completed
        return rem if rem > 0 else Decimal('0.0')

    def adjust_total_required(self, new_total: Decimal) -> None:
        """
        Set the TOTAL required hours to a new value without changing completed hours.
        Never go below completed; auto-close when remaining hits 0.
        """
        if new_total < self.hours_completed:
            new_total = self.hours_completed
        self.total_required_hours = new_total
        self.is_closed = (self.remaining_hours == 0)
        self.save(update_fields=["total_required_hours", "is_closed", "updated_at"])

    # ---------- Helpers for manual workflow ----------

    @classmethod
    @transaction.atomic
    def get_or_create_open(
        cls,
        *,
        student_id: str,
        last_name: str = "",
        first_name: str = "",
        program_course: str = "",
        middle_initial: str = "",
        extension_name: str = "",
    ) -> "CommunityServiceCase":
        """
        App-level guarantee of one open case per student.
        If none exists, create with the admin-typed snapshot.
        """
        case = (cls.objects
                  .select_for_update()
                  .filter(student_id=student_id, is_closed=False)
                  .first())
        if case:
            return case
        return cls.objects.create(
            student_id=student_id,
            last_name=last_name,
            first_name=first_name,
            middle_initial=middle_initial or "",
            extension_name=extension_name or "",
            program_course=program_course,
        )

    @transaction.atomic
    def top_up_required_hours(self, add_hours: Decimal) -> None:
        """Manually increase the required hours."""
        add_hours = Decimal(add_hours)
        if add_hours <= 0:
            return
        self.adjust_total_required(self.total_required_hours + add_hours)

    @transaction.atomic
    def add_manual_hours(self, hours: Decimal, *, is_official: bool = False) -> "CommunityServiceLog":
        """
        Manually credit hours without a live timer (creates a closed log entry).
        Rounds to nearest 0.5h, updates case completion, and auto-closes if done.
        Safe for concurrent admin actions.
        """
        q = _q_half(Decimal(hours))
        now = timezone.now()
        log = CommunityServiceLog.objects.create(
            case=self,
            check_in_at=now,
            check_out_at=now,
            hours=q,
            is_official=is_official,
        )

        # UPDATED: lock the case row before updating totals (multi-admin safe)
        locked = CommunityServiceCase.objects.select_for_update().get(pk=self.pk)
        locked.hours_completed = (locked.hours_completed or Decimal('0.0')) + q
        locked.is_closed = (locked.remaining_hours == 0)
        locked.save(update_fields=["hours_completed", "is_closed", "updated_at"])

        # keep 'self' in sync for caller
        self.hours_completed = locked.hours_completed
        self.is_closed = locked.is_closed
        return log

    @transaction.atomic
    def has_open_session(self) -> bool:
        # UPDATED: lock when checking to avoid races
        return self.logs.select_for_update().filter(check_out_at__isnull=True).exists()

    @transaction.atomic
    def open_session(self) -> "CommunityServiceLog":
        """
        Start a live timer session (Time-In). Enforce at most one open session
        even under concurrent clicks (via row lock).
        """
        existing = (self.logs
                    .select_for_update()
                    .filter(check_out_at__isnull=True)
                    .first())
        if existing:
            return existing
        return CommunityServiceLog.objects.create(case=self)

    @transaction.atomic
    def close_open_session(self) -> "CommunityServiceLog | None":
        """
        Close the currently open session (Time-Out) if any, with a lock so
        concurrent requests don't double-close.
        """
        log = (self.logs
               .select_for_update()
               .filter(check_out_at__isnull=True)
               .first())
        if log:
            log.close()
        return log

class CommunityServiceLog(models.Model):
    """
    Server-authoritative session log:
      - check_in_at set by DB/app server time when the row is created
      - check_out_at set on close()
      - hours computed on the server and added to the case
    """
    case = models.ForeignKey("CommunityServiceCase", on_delete=models.CASCADE, related_name="logs")
    check_in_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    check_out_at = models.DateTimeField(null=True, blank=True)

    hours = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("0.0"))
    is_official = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "community_service_log"
        indexes = [
            models.Index(fields=["case", "check_out_at"]),  # speeds up "find open log"
        ]

    def __str__(self):
        status = "open" if self.check_out_at is None else "closed"
        return f"{self.case.student_id} | {status} | {self.hours}h"

    def save(self, *args, **kwargs):
        # guard: ensure non-negative hours
        if self.hours and self.hours < 0:
            self.hours = Decimal("0.0")
        super().save(*args, **kwargs)

    def close(self):
        """
        Close the session using server time and compute hours.
        Also updates the parent case's hours_completed and closure status.
        Concurrency-safe with row lock on case in the final update.
        """
        if self.check_out_at is None:
            self.check_out_at = timezone.now()

        # compute duration in hours, round to 0.5h
        delta_seconds = (self.check_out_at - self.check_in_at).total_seconds()
        delta_hours = Decimal(delta_seconds) / Decimal(3600)
        self.hours = _q_half(delta_hours)

        # save log first
        self.save(update_fields=["check_out_at", "hours", "updated_at"])

        # UPDATED: lock case before accumulating (multi-student safe)
        case = CommunityServiceCase.objects.select_for_update().get(pk=self.case_id)
        case.hours_completed = (case.hours_completed or Decimal('0.0')) + self.hours
        case.is_closed = (case.remaining_hours == 0)
        case.save(update_fields=["hours_completed", "is_closed", "updated_at"])
