from django.http import HttpResponse, JsonResponse
import csv, random, json, re
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import Student, UserAccount, OTPVerification, Archived_Account, Candidate, Violation, Scholarship, LostAndFound, ViolationSettlement, StudentAssistantshipRequirement, ACSORequirement
from django.db.models.functions import Lower
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from .decorators import role_required
from django.core.serializers import serialize
from django.utils.html import escape
from django.templatetags.static import static
from django.urls import reverse
import uuid, os
from django.core.files.base import ContentFile
from .forms import ViolationForm, GoodMoralRequestForm
from django.utils.timezone import now
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.utils.dateparse import parse_date
from .utils import send_violation_email  
from django.db.models import Q

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
    scholarships = Scholarship.objects.order_by('-posted_date')
    return render (request, 'myapp/client_scholarships.html', {'scholarships': scholarships})

def client_CS_view(request):
    return render (request, 'myapp/client_CS.html')

def client_SurrenderingID_view(request):
    return render (request, 'myapp/client_SurrenderingID.html')

def client_studentAssistantship_view(request):
    try:
        requirement = StudentAssistantshipRequirement.objects.latest('last_updated')
    except StudentAssistantshipRequirement.DoesNotExist:
        requirement = None
    return render(request, 'myapp/client_studentAssistantship.html', {'requirement': requirement})

def client_ACSO_view(request):
    try:
        accreditation = ACSORequirement.objects.latest('last_updated')
    except ACSORequirement.DoesNotExist:
        accreditation = None
    return render(request, 'myapp/client_ACSO.html', {'accreditation': accreditation})

def client_lostandfound_view(request):
    items = LostAndFound.objects.order_by('-posted_date')
    return render(request, 'myapp/client_lostandfound.html', {'items': items})

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
    obj, _ = ACSORequirement.objects.get_or_create(id=1)

    if request.method == 'POST':
        content = request.POST.get('description', '').strip()
        if not content:
            messages.error(request, "Description cannot be empty.")
            return render(request, 'myapp/admin_ACSO.html', {'requirement': obj})

        obj.content = content
        obj.save()
        messages.success(request, "ACSO Accreditation requirements updated successfully.")
        return redirect('admin_ACSO')

    return render(request, 'myapp/admin_ACSO.html', {'requirement': obj})

@role_required(['admin'])
def admin_assistantship_view(request):
    obj, _ = StudentAssistantshipRequirement.objects.get_or_create(id=1)

    if request.method == 'POST':
        try:
            content = request.POST.get('description', '').strip()

            if not content:
                messages.error(request, "Description cannot be empty.")
                return render(request, 'myapp/admin_assistantship.html', {'requirement': obj})

            obj.content = content
            obj.save()
            messages.success(request, "Student Assistantship requirements updated successfully.")
            return redirect('admin_assistantship')

        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return render(request, 'myapp/admin_assistantship.html', {'requirement': obj})

    return render(request, 'myapp/admin_assistantship.html', {'requirement': obj})

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
    items = LostAndFound.objects.order_by('-posted_date')

    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('image', None)

        if not description:
            messages.error(request, "Please enter a description of the found item.")
            return redirect('admin_lostandfound')

        try:
            lost_item = LostAndFound(
                description=description,
                image=image
            )
            lost_item.save()
            messages.success(request, "✅ Lost and Found item posted successfully.")
            return redirect('admin_lostandfound')
        except Exception as e:
            messages.error(request, f"🚨 Error saving post: {e}")
            return redirect('admin_lostandfound')

    return render(request, 'myapp/admin_lostandfound.html', {'items': items})

@role_required(['admin'])
def admin_report_view(request):
    return render (request, 'myapp/admin_report.html')

@role_required(['admin', 'scholarship'])
def admin_scholarships_view(request):
    scholarships = Scholarship.objects.order_by('-posted_date')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        deadline_date = request.POST.get('deadline_date', '').strip()
        description = request.POST.get('description', '').strip()

        missing_fields = []
        if not title:
            missing_fields.append("Title")
        if not category:
            missing_fields.append("Category")
        if not deadline_date:
            missing_fields.append("Deadline Date")

        if missing_fields:
            messages.error(
                request,
                f"⚠️ Please fill in all required fields: {', '.join(missing_fields)}."
            )
            return redirect('admin_scholarships')

        try:
            scholarship = Scholarship(
                title=title,
                category=category,
                deadline_date=deadline_date,
                description=description,
                attachment_1=request.FILES.get('attachment_1') or None,
                attachment_2=request.FILES.get('attachment_2') or None,
                attachment_3=request.FILES.get('attachment_3') or None,
                attachment_4=request.FILES.get('attachment_4') or None,
                attachment_5=request.FILES.get('attachment_5') or None,
            )
            scholarship.save()
            messages.success(request, "✅ Scholarship posted successfully.")
            return redirect('admin_scholarships')

        except Exception as e:
            messages.error(request, f"🚨 Something went wrong while saving: {e}")
            return redirect('admin_scholarships')

    return render(request, 'myapp/admin_scholarships.html', {
        'scholarships': scholarships
    })

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
def admin_view_violation(request):
    violation_id = request.GET.get('violation_id')

    if not violation_id:
        # fallback if no id provided
        messages.error(request, "No violation ID specified.")
        return redirect('admin_violation')

    violation = get_object_or_404(Violation, id=violation_id)
    student = get_object_or_404(Student, tupc_id=violation.student_id)

    # Approved violations (including this one if approved)
    approved_violations = Violation.objects.filter(
        student_id=student.tupc_id,
        status='Approved'
    ).select_related('settlement')

    # Pending violations (including this one if still pending)
    pending_violations = Violation.objects.filter(
        student_id=student.tupc_id,
        status='Pending'
    )

    total_violations = approved_violations.count()

    return render(request, 'myapp/admin_view_violation.html', {
        'violation': violation,
        'student': student,
        'total_violations': total_violations,
        'approved_violations': approved_violations,
        'pending_violations': pending_violations,
    })

@role_required(['admin'])
def admin_violation_view(request):
    pending_violations = Violation.objects.filter(status='Pending').order_by('-created_at')
    history_violations = Violation.objects.exclude(status='Pending').order_by('-created_at')

    return render(request, 'myapp/admin_violation.html', {
        'pending_violations': pending_violations,
        'history_violations': history_violations
    })

@role_required(['admin'])
def admin_removedstud_view(request):
    return render (request, 'myapp/admin_removedstud.html')

@role_required(['admin', 'comselec'])
def admin_election_results_view(request):
    return render (request, 'myapp/admin_election_results.html')

@role_required(['admin', 'comselec'])
def admin_election_manage_view(request):
    return render (request, 'myapp/admin_election_manage.html')


#########################CLIENT

def scholarship_feed_api(request):
    data = list(Scholarship.objects.order_by('-posted_date').values(
        'id', 'title', 'description', 'category', 'posted_date', 'deadline_date'
    ))
    return JsonResponse({'scholarships': data})

def lostandfound_feed_api(request):
    data = list(LostAndFound.objects.order_by('-posted_date').values(
        'id', 'description', 'posted_date', 'image'
    ))
    # optionally add .url if image is present
    for item in data:
        if item['image']:
            item['image'] = request.build_absolute_uri(item['image'])
    return JsonResponse({'items': data})

def goodmoral_request_form(request):
    if request.method == 'POST':
        form = GoodMoralRequestForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False) 
            try:
                send_mail(
                    subject="Good Moral Certificate Request Received",
                    message=(
                        "We have received your Good Moral Certificate request.\n"
                        "You will receive another email once it is reviewed and approved/rejected."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.requester_email],
                    fail_silently=False
                )
                obj.save()
                return render(request, 'client_goodmoral.html', {'show_modal': True})

            except BadHeaderError:
                messages.error(request, "Invalid header found. Please check your email.")
            except Exception as e:
                messages.error(request, f"Failed to send confirmation email: {e}")
    else:
        form = GoodMoralRequestForm()

    return render(request, 'client_goodmoral.html', {'form': form})





#########################LOGIN

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
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')

    if request.method == 'POST':
        form = ViolationForm(request.POST, request.FILES)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            unsettled_first_violation = ViolationSettlement.objects.filter(
                violation__student_id=student_id,
                is_settled=False
            ).first()

            success_message = "Violation has been recorded and is pending approval."
            if unsettled_first_violation:
                success_message += " Note: This student has an unsettled first violation. Please confiscate the student's ID."

            violation = form.save(commit=False)
            violation.status = 'Pending'
            violation.save()

            messages.success(request, success_message)

            return redirect('guard_violation')
    else:
        form = ViolationForm()

    return render(request, 'myapp/guard_violation.html', {
        'form': form,
        'guards': guards,
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

def scan_student(request, tupc_id):
    has_unsettled_first = ViolationSettlement.objects.filter(
        violation__student_id=tupc_id,
        settlement_type='Apology Letter',
        is_settled=False
    ).exists()

    if has_unsettled_first:
        return JsonResponse({
            'success': False,
            'message': 'Student has an unsettled first violation. Please advise them to submit their apology letter.'
        })
    else:
        return JsonResponse({
            'success': True,
            'message': 'Student cleared for entry.'
        })
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

@role_required(['admin'])
def ajax_delete_lostandfound(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(LostAndFound, id=item_id)
        item.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@role_required(['admin', 'scholarship'])
def ajax_edit_lostandfound(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(LostAndFound, id=item_id)
        description = request.POST.get('description', '').strip()
        if not description:
            return JsonResponse({'success': False, 'error': 'Description required'}, status=400)
        item.description = description
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        item.save()
        return JsonResponse({'success': True, 'description': item.description, 'image_url': item.image.url if item.image else None})
    return JsonResponse({'success': False}, status=400)

@role_required(['admin', 'scholarship'])
def ajax_delete_scholarship(request, id):
    if request.method == 'POST':
        s = get_object_or_404(Scholarship, id=id)
        s.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@role_required(['admin'])
def ajax_edit_scholarship(request, id):
    if request.method == 'POST':
        s = get_object_or_404(Scholarship, id=id)
        s.title = request.POST.get('title', '').strip()
        s.description = request.POST.get('description', '').strip()
        s.category = request.POST.get('category', '').strip()
        s.deadline_date = request.POST.get('deadline_date')
        s.save()
        return JsonResponse({
            'success': True,
            'title': s.title,
            'description': s.description,
            'category': s.category,
            'deadline_date': s.deadline_date,
        })
    return JsonResponse({'success': False}, status=400)
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

def admin_approve_violation(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    student = get_object_or_404(Student, tupc_id=violation.student_id)

    settled_count = ViolationSettlement.objects.filter(
        violation__student_id=student.tupc_id,
        is_settled=True
    ).count()

    settlement_type = 'Apology Letter' if settled_count == 0 else 'Community Service'

    violation.status = 'Approved'
    violation.reviewed_at = timezone.now()
    violation.save()

    ViolationSettlement.objects.create(
        violation=violation,
        settlement_type=settlement_type,
        is_settled=False
    )

    send_violation_email(
        violation=violation,
        student=student,
        violation_count=settled_count + 1,
        settlement_type=settlement_type
    )

    # ✅ Add success message
    messages.success(
        request,
        f"✅ Violation for {student.first_name} {student.last_name} was successfully approved."
    )

    return redirect('admin_violation')

def admin_decline_violation(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    student = get_object_or_404(Student, tupc_id=violation.student_id)

    violation.status = 'Rejected'
    violation.reviewed_at = timezone.now()
    violation.save()

    send_violation_email(
        violation=violation,
        student=student,
        declined=True
    )

    # ✅ Add decline message (style as error)
    messages.error(
        request,
        f"❌ Violation for {student.first_name} {student.last_name} was successfully declined."
    )

    return redirect('admin_violation')

def mark_settlement_as_settled(request, settlement_id):
    settlement = get_object_or_404(ViolationSettlement, id=settlement_id)
    settlement.is_settled = True
    settlement.settled_at = timezone.now()
    settlement.save()

    # Always redirect back to the violation page with the correct student
    violation_id = settlement.violation.id
    return redirect(f"{reverse('admin_view_violation')}?violation_id={violation_id}")
