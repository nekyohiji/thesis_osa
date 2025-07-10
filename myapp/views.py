from django.http import HttpResponse, JsonResponse
import csv, random, json, re
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import Student, UserAccount, OTPVerification, Archived_Account, Candidate, Violation
from django.db.models.functions import Lower
from django.core.mail import send_mail
from django.conf import settings
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from .decorators import role_required
from django.core.serializers import serialize
from django.utils.html import escape
from django.templatetags.static import static
import uuid, os
from django.core.files.base import ContentFile
from .forms import ViolationForm
from django.utils.timezone import now
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def current_time(request):
    return JsonResponse({'now': now().isoformat()})

def index(request):
    return HttpResponse("🎓 Hello from your thesis web app!")

def home_view(request):
    return render(request, 'myapp/client_home.html')

@role_required(['guard'])
def guard_violation_view(request):
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')
    return render (request, 'myapp/guard_violation.html', {'guards': guards})

@role_required(['guard'])
def guard_report_view(request):
    violations = Violation.objects.all().order_by('-violation_date')
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')

    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    violation_type = request.GET.get('violation_type')
    guard_name = request.GET.get('guard_name')

    # Apply filters
    if start_date:
        violations = violations.filter(violation_date__gte=start_date)
    if end_date:
        violations = violations.filter(violation_date__lte=end_date)
    if violation_type:
        violations = violations.filter(violation_type=violation_type)
    if guard_name:
        violations = violations.filter(guard_name=guard_name)

    context = {
        'violations': violations,
        'guards': guards,
        'violation_types': Violation.VIOLATION_TYPES,
    }
    return render(request, 'myapp/guard_report.html', context)

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

def client_election_view(request):
    return render (request, 'myapp/client_election.html')

def client_view_election_view(request):
    return render (request, 'myapp/client_view_election.html')

@role_required(['admin'])
def admin_dashboard_view(request):
    return render (request, 'myapp/admin_dashboard.html')

@role_required(['admin'])
def admin_accounts_view(request):
    return render (request, 'myapp/admin_accounts.html')

@role_required(['admin'])
def admin_ackreq_view(request):
    return render (request, 'myapp/admin_ackreq.html')

@role_required(['admin'])
def admin_ACSO_view(request):
    return render (request, 'myapp/admin_ACSO.html')

@role_required(['admin'])
def admin_assistantship_view(request):
    return render (request, 'myapp/admin_assistantship.html')

@role_required(['admin'])
def admin_CS_view(request):
    return render (request, 'myapp/admin_CS.html')

@role_required(['admin', 'comselec'])
def admin_election_view(request):
    return render (request, 'myapp/admin_election.html')

@role_required(['admin'])
def admin_goodmoral_view(request):
    return render (request, 'myapp/admin_goodmoral.html')

@role_required(['admin'])
def admin_lostandfound_view(request):
    return render (request, 'myapp/admin_lostandfound.html')

@role_required(['admin'])
def admin_report_view(request):
    return render (request, 'myapp/admin_report.html')

@role_required(['admin', 'scholarship'])
def admin_scholarships_view(request):
    return render (request, 'myapp/admin_scholarships.html')

@role_required(['admin'])
def admin_view_ackreq_view(request):
    return render (request, 'myapp/admin_view_ackreq.html')

@role_required(['admin'])
def admin_view_CS_view(request):
    return render (request, 'myapp/admin_view_CS.html')

@role_required(['admin'])
def admin_view_goodmoral_view(request):
    return render (request, 'myapp/admin_view_goodmoral.html')

@role_required(['admin'])
def admin_view_violation_view(request):
    return render (request, 'myapp/admin_view_violation.html')

@role_required(['admin'])
def admin_violation_view(request):
    return render (request, 'myapp/admin_violation.html')

@role_required(['admin'])
def admin_removedstud_view(request):
    return render (request, 'myapp/admin_removedstud.html')

@role_required(['admin', 'comselec'])
def admin_election_results_view(request):
    return render (request, 'myapp/admin_election_results.html')

@role_required(['admin', 'comselec'])
def admin_election_manage_view(request):
    return render (request, 'myapp/admin_election_manage.html')







def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # Validate email
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'myapp/login.html')
        if len(email) > 164:
            messages.error(request, "Please enter a valid email.")
            return render(request, 'myapp/login.html')

        # Validate password length
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'myapp/login.html')
        if len(password) > 128:
            messages.error(request, "Password is too long.")
            return render(request, 'myapp/login.html')

        try:
            user = UserAccount.objects.get(email=email, is_active=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['role'] = user.role
                request.session['full_name'] = user.full_name
                request.session['email'] = user.email

                # Redirect by role
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'guard':
                    return redirect('guard_violation')
                elif user.role == 'scholarship':
                    return redirect('admin_scholarships')
                elif user.role == 'comselec':
                    return redirect('admin_election')
                else:
                    messages.error(request, "Account role not recognized.")
            else:
                messages.error(request, "Incorrect password.")
        except UserAccount.DoesNotExist:
            messages.error(request, "Account not found or inactive.")

    return render(request, 'myapp/login.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


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

def submit_violation(request):
    submitted = False
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')
    if request.method == 'POST':
        form = ViolationForm(request.POST, request.FILES)
        if form.is_valid():
            violation = form.save(commit=False)
            violation.status = 'Pending'
            violation.save()
            submitted = True
            form = ViolationForm()  # clear form
    else:
        form = ViolationForm()
        print(form.errors)
    return render(request, 'myapp/guard_violation.html', {
        'form': form,
        'submitted': submitted,
        'guards': guards
    })

@role_required(['guard'])
def generate_guard_report_pdf(request):
    # Apply same filters as your view
    violations = Violation.objects.all()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    violation_type = request.GET.get('violation_type')
    guard_name = request.GET.get('guard_name')

    if start_date:
        violations = violations.filter(violation_date__gte=start_date)
    if end_date:
        violations = violations.filter(violation_date__lte=end_date)
    if violation_type:
        violations = violations.filter(violation_type=violation_type)
    if guard_name:
        violations = violations.filter(guard_name=guard_name)

    # Start PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="violations_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Violations Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Table headers
    data = [
        ['Student Name', 'Student ID', 'Program/Course', 'Date', 'Time', 'Type of Violation', 'Reported By']
    ]

    for v in violations:
        data.append([
            f"{v.first_name} {v.last_name}",
            v.student_id,
            v.program_course,
            v.violation_date.strftime("%Y-%m-%d"),
            v.violation_time.strftime("%H:%M"),
            v.violation_type,
            v.guard_name
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"Prepared by: {guard_name or '________________'}", styles['Normal']))
    elements.append(Paragraph(f"Noted by: Chief Security Officer", styles['Normal']))

    doc.build(elements)
    return response

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

def request_otp(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'fail', 'message': 'Invalid request method.'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'fail', 'message': 'Invalid JSON payload.'})
    required_fields = ['fullName', 'email', 'position', 'password']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return JsonResponse({'status': 'fail', 'message': f'Missing: {", ".join(missing_fields)}'})

    full_name = data['fullName'].strip()
    email = data['email'].strip().lower()
    position = data['position'].strip()
    password = data['password']
    errors = []
    if not (3 <= len(full_name) <= 128):
        errors.append("Full name must be 3–128 characters.")
    if not (5 <= len(email) <= 254):
        errors.append("Email must be 5–254 characters.")
    if not (3 <= len(position) <= 64):
        errors.append("Position must be 3–64 characters.")
    if not (8 <= len(password) <= 128):
        errors.append("Password must be 8–128 characters.")

    if errors:
        return JsonResponse({'status': 'fail', 'message': " ".join(errors)})
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'fail', 'message': 'Invalid email format.'})
    
    if UserAccount.objects.filter(email=email).exists() or Archived_Account.objects.filter(email=email).exists():
        return JsonResponse({'status': 'fail', 'message': 'This email is already registered.'})
    try:
        record = OTPVerification.objects.get(email=email)
        elapsed = timezone.now() - record.created_at
        if elapsed < timedelta(minutes=5):
            remaining = 300 - int(elapsed.total_seconds())
            return JsonResponse({
                'status': 'wait',
                'message': f'Please wait {remaining} seconds before requesting another OTP.'
            })
    except OTPVerification.DoesNotExist:
        pass
    otp = ''.join(random.choices('0123456789', k=6))
    OTPVerification.objects.update_or_create(
        email=email,
        defaults={
            'otp': otp,
            'full_name': full_name,
            'role': position,
            'password': make_password(password),
            'created_at': timezone.now()
        }
    )
    try:
        send_mail(
            subject='Your TUPC OSA OTP Code',
            message=f'Your One-Time Password is: {otp}\n\nThis OTP will expire in 5 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
    except Exception as e:
        return JsonResponse({'status': 'fail', 'message': f'Failed to send email: {str(e)}'})

    return JsonResponse({'status': 'ok'})

@csrf_exempt
def verify_otp(request):
    data = json.loads(request.body)
    email = data['email']
    otp_input = data['otp'].strip()

    try:
        record = OTPVerification.objects.get(email=email)
        if record.otp.strip() == otp_input:
            UserAccount.objects.create(
                full_name=record.full_name,
                email=record.email,
                role=record.role,
                password=record.password
            )
            record.delete()
            return JsonResponse({'status': 'ok', 'message': 'Account successfully created!'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Incorrect OTP.'})
    except OTPVerification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'No OTP record found for this email.'})

def deactivate_account(request, user_email):
    try:
        account = get_object_or_404(UserAccount, email=user_email)

        Archived_Account.objects.create(
            full_name=account.full_name,
            email=account.email,
            password=account.password,
            role=account.role,
            is_active=False,
        )

        messages.success(request, f"{account.full_name} ({account.email}) has been deactivated.")
        account.delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_accounts_data(request):
    if request.method == 'GET':
        active_accounts = list(UserAccount.objects.filter(is_active=True).values('full_name', 'email', 'role'))
        deactivated_accounts = list(Archived_Account.objects.all().values('full_name', 'email', 'role'))

        return JsonResponse({
            'active': active_accounts,
            'deactivated': deactivated_accounts
        })



################################ELECTIONS   
@csrf_exempt
def add_candidate(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        section = request.POST.get('section')
        tupc_id = request.POST.get('tupc_id')
        position = request.POST.get('position')
        academic_year = request.POST.get('academic_year')
        photo = request.FILES.get('photo')

        if not all([name, section, tupc_id, position, academic_year, photo]):
            return JsonResponse({'status': 'error', 'message': 'Missing fields'}, status=400)

        # ✅ Check if the TUPC ID already exists for this academic year
        existing = Candidate.objects.filter(tupc_id=tupc_id, academic_year=academic_year).exists()
        if existing:
            return JsonResponse({
                'status': 'error',
                'message': f'TUPC ID "{tupc_id}" is already registered for academic year {academic_year}.'
            }, status=409)

        # 🆗 Safe to create
        original_name = photo.name
        extension = os.path.splitext(original_name)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"

        candidate = Candidate.objects.create(
            name=name,
            section=section,
            tupc_id=tupc_id,
            position=position,
            academic_year=academic_year
        )
        candidate.photo.save(unique_filename, photo)
        candidate.save()

        return JsonResponse({'status': 'success', 'candidate_id': candidate.id})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_candidates(request):
    if request.method == 'GET':
        candidates = Candidate.objects.all().order_by('-academic_year', 'position')
        data = []
        for c in candidates:
            image_url = c.photo.url if c.photo and c.photo.name else static('myapp/images/default.png')
            data.append({
                'id': c.id,
                'name': c.name,
                'section': c.section,
                'tupc_id': c.tupc_id,
                'position': c.position,
                'academic_year': str(c.academic_year),  # optional, if this is a model
                'image': image_url
            })
        return JsonResponse({'status': 'success', 'candidates': data})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def delete_candidate(request, candidate_id):
    if request.method == 'DELETE':
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            candidate.delete()
            return JsonResponse({'status': 'success'})
        except Candidate.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Candidate not found'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def get_academic_years(request):
    years = Candidate.objects.values_list('academic_year', flat=True).distinct()
    return JsonResponse({'status': 'success', 'academic_years': list(years)})