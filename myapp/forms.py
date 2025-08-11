from django import forms
from .models import Violation, GoodMoralRequest, IDSurrenderRequest
from django.core.exceptions import ValidationError
import re

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
    
class GoodMoralRequestForm(forms.ModelForm):
    class Meta:
        model = GoodMoralRequest
        fields = [
            'first_name','middle_name','surname','ext','sex',
            'student_id','program','status','date_graduated',
            'inclusive_years','date_admission','purpose','other_purpose',
            'requester_name','requester_email','requester_contact','relationship',
            'document_type','uploaded_file'
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
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