from django import forms
from .models import Violation, GoodMoralRequest, IDSurrenderRequest
from django.core.exceptions import ValidationError
import re, csv
from django.utils import timezone
from datetime import date
from decimal import Decimal
from django.core.validators import MinLengthValidator
from django.contrib.staticfiles import finders
from .models import ClearanceRequest, YEAR_LEVEL_CHOICES, CLIENT_TYPE_CHOICES, STAKEHOLDER_CHOICES, PURPOSE_CHOICES
from .models import Facilitator

class ViolationForm(forms.ModelForm):
    class Meta:
        model = Violation
        fields = [
            'first_name', 'middle_initial', 'extension_name', 'last_name',
            'student_id', 'program_course',
            'violation_date', 'violation_time', 'violation_type',
            'guard_name', 'evidence_1', 'evidence_2'
        ]

    def clean_violation_type(self):
        value = self.cleaned_data.get('violation_type')
        if not value:
            raise forms.ValidationError("Please select a valid violation type.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('evidence_1'):
            raise forms.ValidationError("At least one evidence photo is required.")
        return cleaned_data

class AddViolationForm(forms.ModelForm):
    MINOR_KEYS = [
        "Disturbance","Proper Uniform","Cross Dressing","Facial Hair","Earrings","Caps",
        "Entering Classroom","Leaving Classroom","Attempt Fraternity","Posting Materials",
        "Use of University Facilities","Official Notices","Gambling","Devices","Resources",
        "Harassment",  "Property Damage","PDA","Cigarette",
    ]

    # Minor is optional; if chosen we map it to violation_type
    minor_offense = forms.ChoiceField(
        choices=[("", "-- Select Minor Violation Type --")] +
                [(k, dict(Violation.VIOLATION_TYPES)[k]) for k in MINOR_KEYS],
        required=False
    )

    # ↓↓↓ add this line so field-level validation doesn't fail before clean()
    violation_type = forms.ChoiceField(
        choices=Violation.VIOLATION_TYPES,
        required=False
    )

    MAX_EVIDENCE_MB = 5
    ALLOWED_IMAGE_CT = {"image/jpeg", "image/png", "image/webp", "image/gif"}

    class Meta:
        model = Violation
        fields = [
            "first_name","middle_initial","extension_name","last_name",
            "student_id","program_course","violation_date","violation_time",
            "violation_type",     
            "evidence_1","evidence_2",
        ]
        widgets = {
            "violation_date": forms.DateInput(attrs={"type":"date"}),
            "violation_time": forms.TimeInput(attrs={"type":"time"}),
            "evidence_1": forms.ClearableFileInput(attrs={"accept":"image/*"}),
            "evidence_2": forms.ClearableFileInput(attrs={"accept":"image/*"}),
        }

    def _validate_image(self, f, label):
        if not f:
            return
        max_bytes = self.MAX_EVIDENCE_MB * 1024 * 1024
        if getattr(f, "size", 0) > max_bytes:
            self.add_error(label, f"File too large. Max {self.MAX_EVIDENCE_MB} MB.")
        ct = (getattr(f, "content_type", "") or "").lower()
        if ct and ct not in self.ALLOWED_IMAGE_CT:
            self.add_error(label, "Unsupported image type. Use JPG, PNG, WEBP, or GIF.")

    def clean(self):
        cleaned = super().clean()
        minor = (cleaned.get("minor_offense") or "").strip()
        major = (cleaned.get("violation_type") or "").strip()
        if not minor and not major:
            self.add_error("minor_offense", "Pick either a Minor OR a Major offense.")
            self.add_error("violation_type", "Pick either a Major OR a Minor offense.")
        if minor and major:
            self.add_error("minor_offense", "Pick only one: Minor OR Major.")
            self.add_error("violation_type", "Pick only one: Minor OR Major.")
        if minor and not major:
            if minor not in self.MINOR_KEYS:
                self.add_error("minor_offense", f"Invalid minor violation key: {minor}")
            else:
                cleaned["violation_type"] = minor  

        self._validate_image(cleaned.get("evidence_1"), "evidence_1")
        self._validate_image(cleaned.get("evidence_2"), "evidence_2")

        if self.errors:
            raise ValidationError("Please correct the errors below.")
        return cleaned

    def save(self, approved_by_user=None, *args, **kwargs):
        obj = super().save(commit=False)
        used_minor = bool(self.cleaned_data.get("minor_offense"))
        obj.severity = "MINOR" if used_minor else "MAJOR"
        prior_minor_approved = (
            Violation.objects
            .filter(student_id=obj.student_id, status="Approved", severity="MINOR")
            .count()
        )

        if obj.severity == "MINOR":
            new_settlement = "Apology Letter" if prior_minor_approved == 0 else "Community Service"
        else:
            new_settlement = "None"

        obj.settlement_type = new_settlement
        obj.is_settled = False
        obj.settled_at = None
        now = timezone.now()
        obj.status = "Approved"
        obj.reviewed_at = now
        obj.approved_at = now
        obj.approved_by = approved_by_user or ""
        obj.guard_name  = approved_by_user or "Admin"

        obj.save()
        return obj
      
class GoodMoralRequestForm(forms.ModelForm):
    # Override model fields so we can accept "YYYY" strings
    date_graduated = forms.CharField(required=False)
    date_admission = forms.CharField(required=False)

    class Meta:
        model = GoodMoralRequest
        fields = [
            'first_name','middle_name','surname','ext','sex',
            'student_id','program','status','date_graduated',
            'inclusive_years','date_admission','purpose','other_purpose',
            'requester_name','requester_email','requester_contact','relationship',
            'document_type','uploaded_file'
        ]

    def clean_date_graduated(self):
        s = (self.cleaned_data.get('date_graduated') or '').strip()
        if not s:
            return None
        if not re.fullmatch(r'\d{4}', s):
            raise forms.ValidationError('Enter a 4-digit year for Year Graduated.')
        y = int(s)
        cur = date.today().year
        if y < 1979 or y > cur:
            raise forms.ValidationError(f'Year Graduated must be between 1979 and {cur}.')
        # store as Jan 1 of that year (fits your DateField)
        return date(y, 1, 1)

    def clean_date_admission(self):
        s = (self.cleaned_data.get('date_admission') or '').strip()
        if not s:
            return ''  # your model field is CharField(null=True, blank=True)
        if not re.fullmatch(r'\d{4}', s):
            raise forms.ValidationError('Enter a 4-digit year for Year of Admission.')
        y = int(s)
        cur = date.today().year
        if y < 1979 or y > cur:
            raise forms.ValidationError(f'Year of Admission must be between 1979 and {cur}.')
        # model column is CharField → store "YYYY"
        return str(y)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # normalize names
        for f in ['first_name','middle_name','surname','ext']:
            val = getattr(instance, f, "")
            setattr(instance, f, (val or "").strip().upper())
        if commit:
            instance.save()
        return instance
    
class IDSurrenderRequestForm(forms.ModelForm):
    class Meta:
        model = IDSurrenderRequest
        exclude = ("status", "message", "submitted_at", "acknowledgement_receipt")
        labels = {
            "document_type": "Document Type",                           # <-- add
            "first_name": "First Name",
            "middle_name": "Middle Name",
            "surname": "Surname",
            "extension": "Suffix",
            "program": "Program",
            "reason": "Reason to Surrender",
            "student_number": "Student Number",
            "year_level": "Year Level",
            "inclusive_years": "Inclusive Years (YYYY-YYYY)",
            "upload_id_front": "Upload ID (Front) / Affidavit First Page",
            "upload_id_back": "Upload ID (Back) / Affidavit Second Page",
            "contact_email": "Email",
        }
        widgets = {
            "document_type": forms.Select(                              # <-- add
                choices=IDSurrenderRequest.DOCUMENT_TYPE_CHOICES
            ),
            "first_name": forms.TextInput(attrs={"maxlength": 50}),
            "middle_name": forms.TextInput(attrs={"maxlength": 50}),
            "surname": forms.TextInput(attrs={"maxlength": 50}),
            "extension": forms.TextInput(attrs={"maxlength": 10, "placeholder": "Jr., Sr., II (optional)"}),
            "program": forms.TextInput(attrs={"maxlength": 100}),
            "student_number": forms.TextInput(attrs={
                "maxlength": 18,
                "placeholder": "TUPC-23-0123 … TUPC-23-1234567890",
                "title": "Format: TUPC-XX-XXXX up to TUPC-XX-XXXXXXXXXX (last block 4–10 digits)",
            }),
            "inclusive_years": forms.TextInput(attrs={
                "placeholder": "2019-2023",
                "title": "Use YYYY-YYYY (e.g., 2019-2023)",
            }),
            "upload_id_front": forms.ClearableFileInput(attrs={"accept": ".jpg,.jpeg,.png,.pdf"}),
            "upload_id_back": forms.ClearableFileInput(attrs={"accept": ".jpg,.jpeg,.png,.pdf"}),
            "contact_email": forms.EmailInput(attrs={"placeholder": "you@tup.edu.ph"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Require email (even though model allows null/blank)
        if "contact_email" in self.fields:
            self.fields["contact_email"].required = True
        # Require choosing a document type (front-end also enforces this)
        if "document_type" in self.fields:
            self.fields["document_type"].required = True

    def clean_student_number(self):
        sn = (self.cleaned_data.get("student_number") or "").strip()
        if not re.match(r"^TUPC-\d{2}-\d{4,10}$", sn):
            raise ValidationError("Use TUPC-XX-XXXX up to TUPC-XX-XXXXXXXXXX (last block 4–10 digits).")
        return sn

    def clean_contact_email(self):
        email = (self.cleaned_data.get("contact_email") or "").strip()
        if not email:
            raise ValidationError("Email is required.")
        return email
    
class CSCreateOrAdjustForm(forms.Form):
    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        validators=[MinLengthValidator(1)],
    )
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        validators=[MinLengthValidator(1)],
    )
    middle_initial = forms.CharField(
        label="Middle Initial",
        max_length=10,
        required=False,
    )
    extension_name = forms.CharField(
        label="Ext",
        max_length=10,
        required=False,
    )
    student_id = forms.CharField(
        label="Student ID",
        max_length=20,
        validators=[MinLengthValidator(1)],
    )
    program_course = forms.CharField(
        label="Program",
        max_length=100,
        validators=[MinLengthValidator(1)],
    )
    hours = forms.DecimalField(
        label="Hours (Total Required)",
        max_digits=5,
        decimal_places=1,
        min_value=Decimal("0.5"),
        help_text="Set the TOTAL required hours (0.5 increments).",
    )

    def clean(self):
        cleaned = super().clean()
        # optional: strip spaces from text fields
        for f in ("last_name","first_name","middle_initial","extension_name","student_id","program_course"):
            if f in cleaned and isinstance(cleaned[f], str):
                cleaned[f] = cleaned[f].strip()
        return cleaned
    
def load_programs_from_csv():
    path = finders.find('myapp/data/programs.csv')
    programs = []
    if path:
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.reader(f):
                if not row: continue
                val = row[0].rstrip()
                if val and val.lower() != "program":
                    programs.append(val)
    return programs

STUDENT_RE = re.compile(r'^TUPC-[A-Z0-9]{2}-\d{4,10}$')

class ClearanceRequestForm(forms.ModelForm):
    hasExtension = forms.ChoiceField(
        choices=[('yes','Yes'), ('no','No')],
        widget=forms.RadioSelect,
        initial='no'
    )

    first_name = forms.CharField(min_length=2, max_length=50)
    last_name  = forms.CharField(min_length=2, max_length=50)
    middle_name = forms.CharField(required=False, min_length=1, max_length=50)  
    extension  = forms.CharField(required=False, min_length=2, max_length=15)
    email      = forms.EmailField()
    contact    = forms.CharField(min_length=14, max_length=14)
    student_number = forms.CharField(min_length=12, max_length=18)
    program    = forms.CharField(min_length=2, max_length=100)

    year_level = forms.ChoiceField(choices=[('', '-- Select --')] + YEAR_LEVEL_CHOICES)
    client_type= forms.ChoiceField(choices=[('', '-- Select --')] + CLIENT_TYPE_CHOICES)
    stakeholder= forms.ChoiceField(choices=[('', '-- Select --')] + STAKEHOLDER_CHOICES)
    purpose    = forms.ChoiceField(choices=[('', '-- Select Purpose --')] + PURPOSE_CHOICES)

    class Meta:
        model = ClearanceRequest
        fields = [
            "first_name", "middle_name", "last_name","extension","email","contact",
            "student_number","program","year_level","client_type","stakeholder","purpose"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contact"].widget.attrs.update({
            "placeholder": "+63 XXXXXXXXXX",
            "pattern": r"^\+63\s\d{10}$"
        })
        self.fields["student_number"].widget.attrs.update({
            "placeholder": "TUPC-XX-XXXXXXXX (4–10 digits)",
            "pattern": r"^TUPC-[A-Z0-9]{2}-\d{4,10}$"
        })
    def clean(self):
        cleaned = super().clean()
        for fld in ["first_name","last_name","extension","email","student_number","program"]:
            if fld in cleaned and isinstance(cleaned[fld], str):
                cleaned[fld] = cleaned[fld].rstrip()
        has_ext = (self.data.get("hasExtension") or "no").lower()
        if has_ext == "yes":
            if not cleaned.get("extension"):
                self.add_error("extension", "Extension is required when 'Yes' is selected.")
        else:
            cleaned["extension"] = ""
        contact = cleaned.get("contact","")
        if contact and not re.fullmatch(r"\+63\s\d{10}", contact):
            self.add_error("contact", "Contact number must be exactly: +63 XXXXXXXXXX.")
        sn = cleaned.get("student_number","")
        if sn:
            sn = sn.upper()
            cleaned["student_number"] = sn
            if not STUDENT_RE.fullmatch(sn):
                self.add_error("student_number",
                               "Use TUPC-XX-XXXXXXXX (XX letters/digits; 4–10 digits at end).")
        prog = cleaned.get("program","")
        if not prog:
            self.add_error("program", "Program is required.")

        return cleaned
    
NNNNN = re.compile(r'^\d{2}-\d{3}$')

class FacilitatorForm(forms.ModelForm):
    class Meta:
        model = Facilitator
        fields = ["full_name", "faculty_id", "email"]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email