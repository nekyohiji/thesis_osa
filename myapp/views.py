from django.http import HttpResponse, JsonResponse
import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import Student
from django.db.models.functions import Lower




def index(request):
    return HttpResponse("🎓 Hello from your thesis web app!")
def home_view(request):
    return render(request, 'myapp/client_home.html')
def login_view(request):
    return render (request, 'myapp/login.html')
def guard_violation_view(request):
    return render (request, 'myapp/guard_violation.html')
def guard_report_view(request):
    return render (request, 'myapp/guard_report.html')
def client_goodmoral_view(request):
    return render (request, 'myapp/client_goodmoral.html')
def client_scholarships_view(request):
    return render (request, 'myapp/client_scholarships.html')
def client_CS_view(request):
    return render (request, 'myapp/client_CS.html')
def client_SurrenderingID_view(request):
    return render (request, 'myapp/client_SurrenderingID.html')
def client_studentAssistantship_view(request):
    return render (request, 'myapp/client_studentAssistantship.html')
def client_ACSO_view(request):
    return render (request, 'myapp/client_ACSO.html')
def client_lostandfound_view(request):
    return render (request, 'myapp/client_lostandfound.html')
def admin_dashboard_view(request):
    return render (request, 'myapp/admin_dashboard.html')
def admin_accounts_view(request):
    return render (request, 'myapp/admin_accounts.html')
def admin_ackreq_view(request):
    return render (request, 'myapp/admin_ackreq.html')
def admin_ACSO_view(request):
    return render (request, 'myapp/admin_ACSO.html')
def admin_assistantship_view(request):
    return render (request, 'myapp/admin_assistantship.html')
def admin_CS_view(request):
    return render (request, 'myapp/admin_CS.html')
def admin_election_view(request):
    return render (request, 'myapp/admin_election.html')
def admin_goodmoral_view(request):
    return render (request, 'myapp/admin_goodmoral.html')
def admin_lostandfound_view(request):
    return render (request, 'myapp/admin_lostandfound.html')
def admin_report_view(request):
    return render (request, 'myapp/admin_report.html')
def admin_scholarships_view(request):
    return render (request, 'myapp/admin_scholarships.html')
def admin_view_ackreq_view(request):
    return render (request, 'myapp/admin_view_ackreq.html')
def admin_view_CS_view(request):
    return render (request, 'myapp/admin_view_CS.html')
def admin_view_goodmoral_view(request):
    return render (request, 'myapp/admin_view_goodmoral.html')
def admin_view_violation_view(request):
    return render (request, 'myapp/admin_view_violation.html')
def admin_violation_view(request):
    return render (request, 'myapp/admin_violation.html')
def client_election_view(request):
    return render (request, 'myapp/client_election.html')
def client_view_election_view(request):
    return render (request, 'myapp/client_view_election.html')


########################GUARD
def get_student_by_id(request, tupc_id):
    try:
        student = Student.objects.get(tupc_id=tupc_id)
        return JsonResponse({
            'success': True,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'middle_initial': student.middle_initial or '',
            'extension': student.extension or '',
            'program': student.program
        })
    except Student.DoesNotExist:
        return JsonResponse({'success': False})




########################ADMIN

@csrf_exempt
def upload_student_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)

        skipped_duplicates = []
        skipped_missing_fields = []
        skipped_invalid_lengths = []

        for line_num, row in enumerate(reader, start=2):
            cleaned_row = {k.strip().upper(): v.strip() for k, v in row.items()}

            tupc_id = cleaned_row.get('TUPC_ID', '')
            last_name = cleaned_row.get('LAST_NAME', '')
            first_name = cleaned_row.get('FIRST_NAME', '')
            program = cleaned_row.get('PROGRAM', '')
            middle_initial = cleaned_row.get('MIDDLE_INITIAL', '').strip().upper()
            extension = cleaned_row.get('EXT', '').strip().upper()
            if not tupc_id or not last_name:
                skipped_missing_fields.append(f"Row {line_num}")
                continue

            if (
                len(tupc_id) > 50 or
                len(program) > 50 or
                len(last_name) > 128 or
                len(first_name) > 128 or
                len(middle_initial) > 5 or
                len(extension) > 10
            ):
                skipped_invalid_lengths.append(f"Row {line_num}")
                continue

            if Student.objects.filter(tupc_id=tupc_id).exists():
                full_name = f"{first_name} {last_name}"
                skipped_duplicates.append(full_name)
                continue

            middle_initial = '' if middle_initial in ['', 'NA'] else middle_initial
            extension = '' if extension in ['', 'NA'] else extension

            email = f"{first_name.replace(' ', '').lower()}.{last_name.replace(' ', '').lower()}@gsfe.tupcavite.edu.ph"

            Student.objects.create(
                tupc_id=tupc_id,
                program=program,
                last_name=last_name,
                first_name=first_name,
                middle_initial=middle_initial,
                extension=extension,
                email=email
            )
            
        if skipped_duplicates:
            messages.warning(request, f"⚠️ Skipped existing students: {', '.join(skipped_duplicates)}")
        if skipped_missing_fields:
            messages.warning(request, f"⚠️ Skipped rows missing required fields: {', '.join(skipped_missing_fields)}")
        if skipped_invalid_lengths:
            messages.warning(request, f"⚠️ Skipped rows exceeding character limits: {', '.join(skipped_invalid_lengths)}")
        if not (skipped_duplicates or skipped_missing_fields or skipped_invalid_lengths):
            messages.success(request, "✅ All student records uploaded successfully.")

        return redirect('admin_student')

    return HttpResponse("❌ Invalid request", status=400)

def admin_student_view(request):
    students = Student.objects.all().order_by(Lower('last_name'), Lower('first_name'))
    return render(request, 'myapp/admin_student.html', {'students': students})



