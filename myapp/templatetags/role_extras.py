from django import template

register = template.Library()

ROLE_LABELS = {
    "admin": "Admin",
    "staff": "Staff",
    "studasst": "Student Assistant",
    "scholarship": "Scholarship Coordinator",
}

@register.filter
def role_label(code: str) -> str:
    return ROLE_LABELS.get((code or "").lower(), "User")
