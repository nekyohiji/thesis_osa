from django import forms
from .models import Violation, Scholarship
from django.core.exceptions import ValidationError


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

