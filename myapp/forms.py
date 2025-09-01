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

class MajorViolationForm(forms.ModelForm):
    class Meta:
        model = Violation
        # no evidence fields here
        fields = [
            "first_name","middle_initial","extension_name","last_name",
            "student_id","program_course","violation_date","violation_time",
            "violation_type"
        ]
        widgets = {
            "violation_date": forms.DateInput(attrs={"type":"date"}),
            "violation_time": forms.TimeInput(attrs={"type":"time"}),
        }

    def save(self, approved_by_user=None, *args, **kwargs):
        obj = super().save(commit=False)
        obj.severity = "MAJOR"
        obj.status = "Approved"             # recorded, not reviewed
        now = timezone.now()
        obj.reviewed_at = now
        obj.approved_at = now
        obj.approved_by = approved_by_user or ""
        obj.guard_name = approved_by_user or "Admin"
        # hard-force no evidence on MAJOR, even if someone posts files manually
        obj.evidence_1 = None
        obj.evidence_2 = None
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
        fields = ["full_name", "faculty_id"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
            "faculty_id": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "12-345",
                "inputmode": "numeric",
                "maxlength": "6",
                "pattern": r"\d{2}-\d{3}"
            }),
        }

    def clean_faculty_id(self):
        val = (self.cleaned_data.get("faculty_id") or "").strip()
        if not NNNNN.match(val):
            raise forms.ValidationError("ID must be NN-NNN (e.g., 12-345). Only digits and a hyphen.")
        return val