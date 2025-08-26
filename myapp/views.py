from django.http import HttpResponse, JsonResponse
import csv, random, json, re
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import Student, UserAccount, OTPVerification, Archived_Account, Candidate, Violation, Scholarship, LostAndFound, StudentAssistantshipRequirement, ACSORequirement, GoodMoralRequest, IDSurrenderRequest, CommunityServiceCase, CommunityServiceLog, ClearanceRequest
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
from django.utils.timezone import localtime
import uuid, os
from django.core.files.base import ContentFile
from .forms import ViolationForm, GoodMoralRequestForm, IDSurrenderRequestForm, CSCreateOrAdjustForm, MajorViolationForm, ClearanceRequestForm
from django.utils.timezone import now
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, BaseDocTemplate, Frame, PageTemplate, FrameBreak, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.utils.dateparse import parse_date
from .utils import send_violation_email, generate_gmf_pdf, send_clearance_confirmation
from django.db.models import Q
import os
import io
from collections import Counter
from django.conf import settings
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from PIL import Image
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table as PlatypusTable, TableStyle as PlatypusTableStyle
from django.views.decorators.http import require_POST, require_GET
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import FileResponse, Http404
from django.contrib.staticfiles import finders
from django.views.decorators.clickjacking import xframe_options_exempt
from django.core.files.storage import default_storage
from .libre.ack_receipt import build_ack_pdf
import mimetypes
from decimal import Decimal
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage
from django.http import JsonResponse, HttpResponseBadRequest
import logging
logger = logging.getLogger(__name__)
# views.py
from io import BytesIO
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.models import Q
from PyPDF2 import PdfMerger  # pip install pypdf or PyPDF2
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
#################################################################################################################

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

def client_view_CS_view(request):
    q = request.GET.get('q','').strip()
    qs = CommunityServiceCase.objects.order_by('-updated_at')
    if q:
        qs = qs.filter(
            Q(last_name__icontains=q) | Q(first_name__icontains=q) |
            Q(program_course__icontains=q) | Q(student_id__icontains=q)
        )
    return render(request, 'myapp/client_view_CS.html', {'cases': qs, 'q': q})

def cs_case_detail_api(request, case_id):
    case = get_object_or_404(CommunityServiceCase, id=case_id)
    vio = (Violation.objects
           .filter(student_id=case.student_id)
           .order_by('-violation_date', '-created_at')
           .values('violation_type','violation_date','status','id'))
    # map violations to simple JSON
    violations = [{
        "type": Violation.VIOLATION_TYPES_DICT.get(v['violation_type'], v['violation_type']) if hasattr(Violation,'VIOLATION_TYPES_DICT') else v['violation_type'],
        "date": v['violation_date'].strftime('%b %d, %Y') if v['violation_date'] else '',
        "severity": getattr(Violation, 'severity', 'Minor') and 'Minor'  # fallback label
    } for v in vio]

    logs_qs = case.logs.order_by('-check_in_at')
    logs = []
    for l in logs_qs:
        logs.append({
            "date": timezone.localtime(l.check_in_at).strftime('%b %d, %Y'),
            "in":   timezone.localtime(l.check_in_at).strftime('%I:%M %p'),
            "out":  timezone.localtime(l.check_out_at).strftime('%I:%M %p') if l.check_out_at else None,
            "hours": str(l.hours)
        })

    open_session = logs_qs.filter(check_out_at__isnull=True).exists()

    return JsonResponse({
        "case": {
            "id": case.id,
            "student_id": case.student_id,
            "first_name": case.first_name,
            "last_name": case.last_name,
            "program_course": case.program_course,
            "total_required_hours": str(case.total_required_hours),
            "hours_completed": str(case.hours_completed),
            "remaining_hours": str(case.remaining_hours),
            "is_closed": case.is_closed,
        },
        "violations": violations,
        "logs": logs,
        "open_session": open_session,
    })

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

def client_clearance_view(request):
    return render (request, 'myapp/client_clearance.html')




def admin_old_violation_view(request):      ##### DIKO ALAM SAN ILALAGAY - JOCHELLE
    return render (request, 'myapp/admin_old_violation.html')

@role_required(['admin'])
def admin_dashboard_view(request):
    return render (request, 'myapp/admin_dashboard.html')

@role_required(['admin'])
def admin_accounts_view(request):
    return render (request, 'myapp/admin_accounts.html')

@role_required(['admin'])
def admin_clearance(request):
    records = ClearanceRequest.objects.all().order_by('-created_at')  # newest first
    return render(request, 'myapp/admin_clearance.html', {
        'records': records,
        'total': records.count(),
    })


@role_required(['admin'])
def admin_view_clearance_view(request, pk):
    obj = get_object_or_404(ClearanceRequest, pk=pk)
    return render(request, 'myapp/admin_view_clearance.html', {'obj': obj})

@role_required(['admin'])
def admin_ackreq_view(request):
    pending_requests = IDSurrenderRequest.objects.filter(
        status=IDSurrenderRequest.STATUS_PENDING
    ).order_by('-submitted_at')

    history_requests = IDSurrenderRequest.objects.filter(
        status__in=[IDSurrenderRequest.STATUS_APPROVED, IDSurrenderRequest.STATUS_DECLINED]
    ).order_by('-submitted_at')

    context = {
        "pending_requests": pending_requests,
        "history_requests": history_requests,
        "pending_count": pending_requests.count(),
        "history_count": history_requests.count(),
        # make constants available to the template for clean comparisons
        "STATUS_APPROVED": IDSurrenderRequest.STATUS_APPROVED,
        "STATUS_DECLINED": IDSurrenderRequest.STATUS_DECLINED,
    }
    return render(request, "myapp/admin_ackreq.html", context)

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
def admin_community_service(request):
    q = (request.GET.get('q') or '').strip()
    cases = CommunityServiceCase.objects.order_by('is_closed', '-updated_at')
    if q:
        cases = cases.filter(
            Q(student_id__icontains=q) |
            Q(last_name__icontains=q) |
            Q(first_name__icontains=q)
        )

    cs_form = CSCreateOrAdjustForm()   # for the modal
    return render(request, 'myapp/admin_community_service.html', {
        'cases': cases,
        'q': q,
        'cs_form': cs_form,
        'show_cs_modal': False,        # only True when posting with errors
    })

@role_required(['admin'])
def admin_view_community_service(request, case_id):
    case = get_object_or_404(CommunityServiceCase, id=case_id)
    # Pull violations for the *same student_id*
    violations = (Violation.objects
                  .filter(student_id=case.student_id)
                  .order_by('-violation_date', '-created_at'))
    logs = case.logs.order_by('-check_in_at')  # newest first
    open_log = case.logs.filter(check_out_at__isnull=True).first()
    return render(request, 'myapp/admin_view_community_service.html', {
        'case': case,
        'violations': violations,
        'logs': logs,
        'open_log': open_log,
    })

@role_required(['admin', 'comselec'])
def admin_election_view(request):
    return render (request, 'myapp/admin_election.html')

@role_required(['admin'])
def admin_goodmoral_view(request):
    pending_qs = GoodMoralRequest.objects.filter(
        is_approved=False, is_rejected=False
    ).order_by('-submitted_at')

    history_qs = GoodMoralRequest.objects.exclude(
        is_approved=False, is_rejected=False
    ).order_by('-submitted_at')

    return render(
        request,
        'myapp/admin_goodmoral.html',
        {
            'pending_requests': pending_qs,
            'history_requests': history_qs,
            'pending_count': pending_qs.count(),
            'history_count': history_qs.count(),
        }
    )

@role_required(['admin'])
def admin_view_goodmoral(request, pk):
    r = get_object_or_404(GoodMoralRequest, pk=pk)
    return render(request, 'myapp/admin_view_goodmoral.html', {'r': r})

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

def admin_view_ackreq_view(request, pk):
    req = get_object_or_404(IDSurrenderRequest, pk=pk)
    return render(request, 'myapp/admin_view_ackreq.html', {"req": req})

@role_required(['admin'])
def admin_view_goodmoral_view(request):
    return render (request, 'myapp/admin_view_goodmoral.html')

@role_required(['admin'])
def admin_view_violation(request):
    violation_id = request.GET.get('violation_id')
    if not violation_id:
        messages.error(request, "No violation ID specified.")
        return redirect('myapp/admin_violation.html')

    violation = get_object_or_404(Violation, id=violation_id)
    student   = get_object_or_404(Student, tupc_id=violation.student_id)

    # “Profile” tables in the template = Approved + Pending for that student
    approved_violations = (
        Violation.objects
        .filter(student_id=student.tupc_id, status='Approved')
        .order_by('-violation_date','-created_at')
        .defer('evidence_1','evidence_2')  # table shows links; you can remove defer if you need urls immediately
    )
    pending_violations = (
        Violation.objects
        .filter(student_id=student.tupc_id, status='Pending')
        .order_by('-violation_date','-created_at')
        .defer('evidence_1','evidence_2')
    )

    total_violations = approved_violations.count()  # matches how your template displays “Total Violations”

    return render(request, 'myapp/admin_view_violation.html', {
        'violation': violation,
        'student': student,
        'total_violations': total_violations,
        'approved_violations': approved_violations,
        'pending_violations': pending_violations,
    })

@role_required(['admin'])
def admin_violation_view(request):
    # ----- POST: create MAJOR violation -----
    open_major_modal = False
    if request.method == "POST" and request.POST.get("is_major") == "1":
        major_form = MajorViolationForm(request.POST)  # no files for major
        if major_form.is_valid():
            approver = getattr(request.user, "get_full_name", lambda: "")() or request.user.username
            major_form.save(approved_by_user=approver)
            messages.success(request, "Major violation has been recorded.")
            return redirect("admin_violation")  # stay on the same page (PRG)
        else:
            open_major_modal = True  # re-open the modal to show errors
    else:
        major_form = MajorViolationForm()

    # ----- GET + (re-render after invalid POST) -----
    q_pending  = (request.GET.get('q') or '').strip()
    q_history  = (request.GET.get('q_history') or '').strip()
    default_violation_date = timezone.localdate().strftime("%Y-%m-%d")
    default_violation_time = timezone.localtime().strftime("%H:%M")

    base = (Violation.objects
            .defer('evidence_1','evidence_2')
            .order_by('-created_at'))

    pending = base.filter(status='Pending')
    if q_pending:
        pending = pending.filter(
            Q(student_id__icontains=q_pending) |
            Q(first_name__icontains=q_pending) |
            Q(last_name__icontains=q_pending)
        )

    history = base.exclude(status='Pending')
    if q_history:
        history = history.filter(
            Q(student_id__icontains=q_history) |
            Q(first_name__icontains=q_history) |
            Q(last_name__icontains=q_history)
        )

    # robust ints
    def _toi(v, d):
        try: return int(v)
        except (TypeError, ValueError): return d

    p_page = max(1, _toi(request.GET.get('p', 1), 1))
    h_page = max(1, _toi(request.GET.get('h', 1), 1))
    per    = min(max(_toi(request.GET.get('per', 15), 15), 1), 100)

    p_pager = Paginator(pending, per)
    h_pager = Paginator(history, per)
    try: pending_page = p_pager.page(p_page)
    except EmptyPage: pending_page = p_pager.page(max(p_pager.num_pages, 1))
    try: history_page = h_pager.page(h_page)
    except EmptyPage: history_page = h_pager.page(max(h_pager.num_pages, 1))

    return render(request, 'myapp/admin_violation.html', {
        'pending_violations': pending_page,
        'history_violations': history_page,
        "major_form": major_form,
        "open_major_modal": open_major_modal,
        "default_violation_date": default_violation_date,
        "default_violation_time": default_violation_time,
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
    template = 'myapp/client_goodmoral.html'
    # Clear any stray messages from previous requests
    list(messages.get_messages(request))

    if request.method == 'POST':
        form = GoodMoralRequestForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            needs_other = obj.purpose in ['Others', 'Scholarship', 'Transfer to Another School']
            if needs_other and not (obj.other_purpose or '').strip():
                messages.error(request, "You must specify your purpose.", extra_tags="gm-client")
                return render(request, template, {'form': form})

            obj.save()
            try:
                send_mail(
                    subject="Good Moral Certificate Request Received",
                    message=("We have received your Good Moral Certificate request.\n"
                             "You will receive another email once it is reviewed and approved/rejected."),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.requester_email],
                    fail_silently=False,
                )
            except Exception:
                # Log the real error for admins, show a safe message to the client
                logger.exception("Good Moral: send_mail failed for id=%s email=%s", obj.id, obj.requester_email)
                messages.error(
                    request,
                    "Your request was submitted, but email notification could not be sent. We’ll follow up.",
                    extra_tags="gm-client",
                )

            return render(request, template, {'form': GoodMoralRequestForm(), 'show_modal': True})
        else:
            # Let your HTML show field errors; optionally add a non-field error for general problems
            # form.add_error(None, "Please correct the errors below.")
            return render(request, template, {'form': form})
    else:
        form = GoodMoralRequestForm()

    return render(request, template, {'form': form})

def id_surrender_request(request):
    template = 'myapp/client_SurrenderingID.html'

    if request.method == 'POST':
        form = IDSurrenderRequestForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)

            # If your model has submitted_by (ForeignKey to User), record it
            if hasattr(obj, "submitted_by") and request.user.is_authenticated:
                obj.submitted_by = request.user

            obj.save()

            # Choose best recipient: the form's contact_email, else logged-in user email
            recipient = getattr(obj, "contact_email", None)
            if not recipient and request.user.is_authenticated:
                recipient = request.user.email

            if recipient:
                try:
                    send_mail(
                        subject="ID Surrender Request Received",
                        message=("We have received your ID Surrender request.\n"
                                 "You will receive another email once it is reviewed and approved or rejected.\n"
                                 "Please prepare to present your ID for verification prior to issuance of the Acknowledgement slip."),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        recipient_list=[recipient],
                        fail_silently=False,
                    )
                except Exception as e:
                    messages.error(request, f"Email error: {e}")

            # Re-render with a fresh form and the success modal flag
            return render(request, template, {
                'form': IDSurrenderRequestForm(),
                'show_modal': True
            })

        # Invalid: redisplay with errors
        return render(request, template, {'form': form})

    # GET
    return render(request, template, {'form': IDSurrenderRequestForm()})

@require_http_methods(["GET", "POST"])
def clearance_request_view(request):
    if request.method == "POST":
        form = ClearanceRequestForm(request.POST)
        if not form.is_valid():
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "errors": form.errors}, status=400)
            return render(request, "myapp/client_clearance.html", {"form": form})
        obj = form.save()

        # send confirmation to the client
        try:
            send_clearance_confirmation(obj)
        except Exception as e:
            # don't block UX on email failure; log as needed
            print("Email send failed:", e)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "id": obj.pk})
        return render(request, "myapp/client_clearance.html", {"form": ClearanceRequestForm()})
    return render(request, "myapp/client_clearance.html", {"form": ClearanceRequestForm()})












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

            # Does the student have an approved first violation that needs an Apology Letter and isn’t settled?
            unsettled_first = Violation.objects.filter(
                student_id=student_id,
                status='Approved',
                settlement_type='Apology Letter',
                is_settled=False
            ).exists()

            success_message = "Violation has been recorded and is pending approval."
            if unsettled_first:
                success_message += " Note: This student has an unsettled first violation. Please confiscate the student's ID."

            v = form.save(commit=False)
            v.severity = "MINOR"            # guards only submit minors (for now)
            v.status = 'Pending'
            v.settlement_type = "None"      # determined on approval
            v.is_settled = False
            v.save()

            messages.success(request, success_message)
            return redirect('guard_violation')
    else:
        form = ViolationForm()

    return render(request, 'myapp/guard_violation.html', {
        'form': form,
        'guards': guards,
        # optional: surface this on GET only if you capture a student id on the page
        # 'unsettled_warning': False,
    })

@role_required(['guard'])
def generate_guard_report_pdf(request):

    # --- Filters ---
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    violation_type = request.GET.get('violation_type', '').strip()
    guard_name = request.GET.get('guard_name', '').strip()

    # --- Filters ---
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    violation_type = request.GET.get('violation_type', '').strip()
    guard_name = request.GET.get('guard_name', '').strip()

    # Query
    violations = Violation.objects.all()
    # Query
    violations = Violation.objects.all()
    if start_date:
        violations = violations.filter(violation_date__gte=start_date)
    if end_date:
        violations = violations.filter(violation_date__lte=end_date)
    if violation_type:
        violations = violations.filter(violation_type=violation_type)
    if guard_name:
        violations = violations.filter(guard_name=guard_name)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="violations_report.pdf"'

    generated_on = timezone.now().strftime('%Y-%m-%d %H:%M')

    generated_on = timezone.now().strftime('%Y-%m-%d %H:%M')

    styles = getSampleStyleSheet()
    subtitle_style = ParagraphStyle(name='Subtitle', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    table_cell_style = ParagraphStyle(name='table_cell', parent=styles['Normal'], fontSize=7, leading=9)

    # ===== HEADER/FOOTER =====
    def header_footer(canvas, doc):
        canvas.saveState()
        gray_tone = colors.Color(0.45, 0.45, 0.45)
        canvas.setFillColor(gray_tone)

        # Left-aligned header text
        x_pos = 40
        y_pos = A4[1] - 50
        canvas.setFont("Helvetica", 10)
        canvas.drawString(x_pos, y_pos, "Republic of the Philippines")
        y_pos -= 13
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(x_pos, y_pos, "TECHNOLOGICAL UNIVERSITY OF THE PHILIPPINES - CAVITE CAMPUS")
        y_pos -= 13
        canvas.setFont("Helvetica", 10)
        canvas.drawString(x_pos, y_pos, "Carlos Q. Trinidad Avenue, Salawag, Dasmariñas City, Cavite, 4114")

        # Right-aligned images
        image_names = ["tuplogo.png", "bgph.png", "ISO.png"]
        img_size = 40
        padding = 8
        right_x = A4[0] - 40

        for name in reversed(image_names):
            img_path = os.path.join(settings.BASE_DIR, 'myapp', 'static', 'myapp', 'images', name)
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    img.thumbnail((img_size, img_size), Image.LANCZOS)
                    img_io = io.BytesIO()
                    img.save(img_io, format='PNG')
                    img_io.seek(0)
                    right_x -= img.size[0]
                    canvas.drawImage(
                        ImageReader(img_io),
                        right_x,
                        A4[1] - 60,
                        width=img.size[0],
                        height=img.size[1],
                        mask='auto'
                    )
                    right_x -= padding
                except Exception:
                    pass

        # Footer
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 30, f"Generated on: {generated_on}")
        canvas.drawRightString(A4[0] - 40, 30,
                               "This report was generated automatically by the Student Violation System.")

        canvas.restoreState()

    # ===== DOC SETUP =====
    doc = BaseDocTemplate(
        response,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=110,
        bottomMargin=60
    )

    frame_main = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')
    template = PageTemplate(id='normal', frames=[frame_main], onPage=header_footer)
    doc.addPageTemplates([template])

    elements = []

    # Title & filters
    elements.append(Paragraph("Violations Report", styles['Title']))
    elements.append(Spacer(1, 8))

    filters = []
    if start_date:
        filters.append(f"From: {start_date}")
    if end_date:
        filters.append(f"To: {end_date}")
    if violation_type:
        filters.append(f"Violation Type: {violation_type}")
    if guard_name:
        filters.append(f"Guard on Duty: {guard_name}")

    if filters:
        elements.append(Paragraph(", ".join(filters), subtitle_style))
        elements.append(Spacer(1, 10))

    # ===== Table with Status =====
    headers = ['Student Name', 'Student ID', 'Program/Course', 'Date', 'Time',
               'Type of Violation', 'Reported By', 'Status']
    col_widths = [
        doc.width * 0.15,
        doc.width * 0.11,
        doc.width * 0.18,
        doc.width * 0.10,
        doc.width * 0.08,
        doc.width * 0.16,
        doc.width * 0.12,
        doc.width * 0.10,
    ]

    # Build table rows
    rows = [[Paragraph(h, styles['Heading5']) for h in headers]]
    for v in violations.order_by('violation_date', 'violation_time'):
        rows.append([
            Paragraph(f"{v.first_name} {v.last_name}", table_cell_style),
            Paragraph(v.student_id, table_cell_style),
            Paragraph(v.program_course, table_cell_style),
            Paragraph(v.violation_date.strftime("%Y-%m-%d"), table_cell_style),
            Paragraph(v.violation_time.strftime("%H:%M"), table_cell_style),
            Paragraph(v.violation_type, table_cell_style),
            Paragraph(v.guard_name, table_cell_style),
            Paragraph(getattr(v, 'status', ''), table_cell_style),
        ])

    if len(rows) == 1:
        rows.append([Paragraph('No data', table_cell_style)] * len(headers))
        total_violations = 0
    else:
        total_violations = len(rows) - 1

    cardinal_red = colors.HexColor("#8C1515")
    light_gray = colors.HexColor("#F2F2F2")
    mid_gray = colors.HexColor("#E6E6E6")

    # Split table into pages of 25 rows of data (plus header)
    max_rows_per_page = 26  # header + 25 data rows
    for start in range(0, len(rows), max_rows_per_page - 1):
        chunk = rows[start:start + max_rows_per_page]
        table = Table(chunk, colWidths=col_widths, repeatRows=1)
        table_style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), cardinal_red),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]
        for i in range(1, len(chunk)):
            bg_color = light_gray if (i + start) % 2 == 0 else mid_gray
            table_style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        table.setStyle(TableStyle(table_style_cmds))
        elements.append(table)

        # Add page break if more chunks remain
        if start + max_rows_per_page - 1 < len(rows):
            elements.append(PageBreak())

    # Totals
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Violations: {total_violations}", styles['Normal']))

    type_counts = Counter(v.violation_type for v in violations)
    if type_counts:
        elements.append(Spacer(1, 6))
        for vtype, count in type_counts.items():
            elements.append(Paragraph(f"{vtype}: {count}", styles['Normal']))

    # Signatures on last page only
    elements.append(Spacer(1, 60))
    block_width = 150
    sig_label_style = ParagraphStyle('sig_label_style', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11)
    sig_name_style = ParagraphStyle('sig_name_style', parent=styles['Normal'], alignment=TA_LEFT, fontSize=10)
    sig_printed_style = ParagraphStyle('sig_printed_style', parent=styles['Normal'], alignment=TA_LEFT, fontSize=10)

    def signature_block(label, name):
        return [
            Paragraph(label, sig_label_style),
            Spacer(1, 18),
            Table(
                [[Paragraph(name, sig_name_style)]],
                colWidths=[block_width],
                style=[
                    ('LINEBELOW', (0, 0), (-1, -1), 1.25, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ],
                hAlign='LEFT'
            ),
            Spacer(1, 6),
            Paragraph("Printed Name with Signature", sig_printed_style)
        ]

    elements.extend(signature_block("Prepared by:", guard_name if guard_name else ""))
    elements.append(Spacer(1, 40))
    elements.extend(signature_block("Noted by:", ""))

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
            
OTP_TTL_MINUTES = 10

# ----- helpers -----
def _json_err(msg, status=400, **extra):
    payload = {"status": "error", "message": msg}
    payload.update(extra)
    return JsonResponse(payload, status=status)

def _safe_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON payload.")

def _gen_otp():
    return f"{random.randint(0, 999999):06d}"

def _expired(dt):
    return dt < timezone.now() - timedelta(minutes=OTP_TTL_MINUTES)

# =========================
#  NAME EDIT
# =========================
@require_http_methods(["POST", "PATCH"])
def edit_account(request, user_email: str):
    """
    Edit name (and optionally role if you enable it in UI).
    Body: { "full_name": "...", "role": "admin" (optional) }
    """
    account = get_object_or_404(UserAccount, email=user_email)
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    full_name = (body.get("full_name") or "").strip()
    role      = body.get("role", None)

    errors = {}
    if not full_name:
        errors["full_name"] = "Full name is required."
    elif len(full_name) > 128:
        errors["full_name"] = "Full name must be at most 128 characters."
    if role is not None and role not in {c[0] for c in UserAccount.ROLE_CHOICES}:
        errors["role"] = "Invalid role."

    if errors:
        return JsonResponse({"status": "error", "message": "Validation failed.", "errors": errors}, status=400)

    try:
        with transaction.atomic():
            account.full_name = full_name
            if role is not None:
                account.role = role
            fields = ["full_name"] + (["role"] if role is not None else [])
            account.save(update_fields=fields)
    except Exception as e:
        return _json_err(f"Unable to update the account: {e}", 500)

    return JsonResponse({
        "status": "ok",
        "message": "Account updated successfully.",
        "account": {"full_name": account.full_name, "email": account.email, "role": account.role}
    })

# =========================
#  EMAIL CHANGE (OTP)
# =========================
@require_http_methods(["POST"])
def email_change_request(request):
    """
    Body: { "current_email": "...", "new_email": "..." }
    Send OTP to the NEW email, stored in OTPVerification keyed by new_email.
    """
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    current_email = (body.get("current_email") or "").strip()
    new_email     = (body.get("new_email") or "").strip()

    if not current_email or not new_email:
        return _json_err("Both current_email and new_email are required.")
    if current_email == new_email:
        return _json_err("New email must be different from current email.")

    account = get_object_or_404(UserAccount, email=current_email)

    # Prevent duplicates
    if UserAccount.objects.filter(email=new_email).exists():
        return _json_err("That email is already in use.", 409)

    otp = _gen_otp()

    # Upsert OTPVerification by email=new_email
    obj, created = OTPVerification.objects.get_or_create(
        email=new_email,
        defaults={
            "otp": otp,
            "full_name": account.full_name,
            "role": account.role,
            "password": account.password,
            "is_active": False,
        }
    )
    if not created:
        obj.otp = otp
        obj.full_name = account.full_name
        obj.role = account.role
        obj.password = account.password
        obj.is_active = False
        obj.created_at = timezone.now()
        obj.save(update_fields=["otp", "full_name", "role", "password", "is_active", "created_at"])

    try:
        send_mail(
            subject="Email Change OTP",
            message=f"Your verification code is: {otp}\nIt expires in {OTP_TTL_MINUTES} minutes.",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[new_email],
            fail_silently=False,
        )
    except (BadHeaderError, Exception) as e:
        if settings.DEBUG:
            # In development we can reveal the OTP to make testing easier
            return JsonResponse({"status": "ok", "message": "OTP generated (DEBUG).", "dev_otp": otp})
        return _json_err(f"Failed to send OTP: {e}", 500)

    return JsonResponse({"status": "ok", "message": "OTP sent to new email."})

@require_http_methods(["POST"])
def email_change_verify(request):
    """
    Body: { "new_email": "...", "otp": "123456" }
    Mark OTPVerification.is_active=True (verified) for that new email.
    """
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    new_email = (body.get("new_email") or "").strip()
    otp       = (body.get("otp") or "").strip()
    if not new_email or not otp:
        return _json_err("new_email and otp are required.")

    try:
        rec = OTPVerification.objects.get(email=new_email)
    except OTPVerification.DoesNotExist:
        return _json_err("No OTP request found for that email.", 404)

    if _expired(rec.created_at):
        return _json_err("OTP expired. Please request a new one.", 400)
    if rec.otp != otp:
        return _json_err("Invalid OTP.", 400)

    rec.is_active = True
    rec.save(update_fields=["is_active"])
    return JsonResponse({"status": "ok", "message": "OTP verified."})

@require_http_methods(["POST"])
def email_change_apply(request):
    """
    Body: { "current_email": "...", "new_email": "..." }
    Requires verified + unexpired OTPVerification for new_email, then updates UserAccount.email.
    """
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    current_email = (body.get("current_email") or "").strip()
    new_email     = (body.get("new_email") or "").strip()
    if not current_email or not new_email:
        return _json_err("Both current_email and new_email are required.")

    account = get_object_or_404(UserAccount, email=current_email)

    try:
        rec = OTPVerification.objects.get(email=new_email)
    except OTPVerification.DoesNotExist:
        return _json_err("No OTP verification found for that email.", 404)

    if _expired(rec.created_at):
        return _json_err("OTP expired. Please request a new one.", 400)
    if not rec.is_active:
        return _json_err("OTP not verified yet.", 400)
    if UserAccount.objects.filter(email=new_email).exclude(pk=account.pk).exists():
        return _json_err("That email is already in use.", 409)

    with transaction.atomic():
        account.email = new_email
        account.save(update_fields=["email"])
        rec.delete()  # clean up

    return JsonResponse({"status": "ok", "message": "Email updated successfully.", "email": new_email})

@require_http_methods(["POST"])
def password_otp_request(request):
    """Body: { email } — send a 6-digit OTP to the registered email for password change."""
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    email = (body.get("email") or "").strip()
    if not email:
        return _json_err("Email is required.")

    account = get_object_or_404(UserAccount, email=email)

    otp = _gen_otp()
    obj, created = OTPVerification.objects.get_or_create(
        email=email,
        defaults={
            "otp": otp,
            "full_name": account.full_name,
            "role": account.role,
            "password": account.password,
            "is_active": False,
        }
    )
    if not created:
        obj.otp = otp
        obj.full_name = account.full_name
        obj.role = account.role
        obj.password = account.password
        obj.is_active = False
        obj.created_at = timezone.now()
        obj.save(update_fields=["otp", "full_name", "role", "password", "is_active", "created_at"])

    try:
        send_mail(
            subject="Your OTP for Password Change",
            message=f"Your verification code is: {otp}\nIt expires in {OTP_TTL_MINUTES} minutes.",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )
    except (BadHeaderError, Exception) as e:
        if settings.DEBUG:
            return JsonResponse({"status": "ok", "message": "OTP generated (DEBUG).", "dev_otp": otp})
        return _json_err(f"Failed to send OTP: {e}", 500)

    return JsonResponse({"status": "ok", "message": "OTP sent to registered email."})

@require_http_methods(["POST"])
def password_otp_verify(request):
    """Body: { email, otp } — verify password-change OTP (marks OTPVerification.is_active=True)."""
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    email = (body.get("email") or "").strip()
    otp   = (body.get("otp") or "").strip()
    if not email or not otp:
        return _json_err("Email and OTP are required.")

    try:
        rec = OTPVerification.objects.get(email=email)
    except OTPVerification.DoesNotExist:
        return _json_err("No OTP request found for that email.", 404)

    if _expired(rec.created_at):
        return _json_err("OTP expired. Please request a new one.", 400)
    if rec.otp != otp:
        return _json_err("Invalid OTP.", 400)

    rec.is_active = True
    rec.save(update_fields=["is_active"])
    return JsonResponse({"status": "ok", "message": "OTP verified."})

@require_http_methods(["POST"])
def change_password(request, email: str):
    """Body: { new_password } — requires a verified, unexpired OTPVerification for this email."""
    try:
        body = _safe_body(request)
    except ValueError as e:
        return _json_err(str(e), 400)

    new_password = (body.get("new_password") or "").strip()
    if len(new_password) < 8:
        return _json_err("Password must be at least 8 characters.", 400)

    account = get_object_or_404(UserAccount, email=email)

    try:
        rec = OTPVerification.objects.get(email=email)
    except OTPVerification.DoesNotExist:
        return _json_err("Please request and verify an OTP before changing password.", 400)

    if _expired(rec.created_at):
        return _json_err("OTP expired. Please request a new one.", 400)
    if not rec.is_active:
        return _json_err("OTP not verified yet.", 400)

    try:
        with transaction.atomic():
            account.password = make_password(new_password)
            account.save(update_fields=["password"])
            rec.delete()  # consume OTP once used
    except Exception as e:
        return _json_err(f"Unable to change password right now: {e}", 500)

    return JsonResponse({"status": "ok", "message": "Password changed successfully."})

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

DEFAULT_APPROVAL_MSG = (
    "Your Good Moral Certificate request has been approved.\n\n"
    "Please proceed to the Office of Student Affairs (OSA) to claim your request form.\n"
    "Prepare PHP 100 for payment at the cashier's office.\n"
    "After payment, reply to this email with a photo or copy of your receipt."
)

@role_required(['admin'])
@require_POST
def goodmoral_accept(request, pk):
    r = get_object_or_404(GoodMoralRequest, pk=pk)

    # Build a human-friendly reference using the DB primary key
    ref = f"GM-{r.pk:06d}"  # e.g., GM-000117

    note = (request.POST.get('accept_message') or "").strip()
    base_msg = DEFAULT_APPROVAL_MSG
    final_msg = (note if note else base_msg) + f"\n\nReference ID: {ref}"

    # Update status
    r.is_approved = True
    r.is_rejected = False
    r.rejection_reason = ""
    r.save(update_fields=['is_approved', 'is_rejected', 'rejection_reason'])

    subject = f"[{ref}] Your Good Moral Certificate Request has been APPROVED"
    body = (
        f"Hello {r.requester_name},\n\n"
        f"Your Good Moral Certificate request for {r.first_name} {r.surname} "
        f"(Student ID: {r.student_id}) has been APPROVED.\n\n"
        f"{final_msg}\n\n"
        f"Purpose: {r.purpose}{(' - ' + r.other_purpose) if r.other_purpose else ''}\n"
        f"Submitted: {r.submitted_at:%b %d, %Y %I:%M %p}\n\n"
        "Thank you."
    )

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [r.requester_email],
            fail_silently=False,
        )
        messages.success(request,
                 f"Request accepted and email sent. Ref: {ref}",
                 extra_tags='gm-admin')
    except Exception as e:
        messages.warning(request, f"Accepted, but email failed: {e}. Ref: {ref}")

    return redirect('admin_view_goodmoral', pk=pk)

@role_required(['admin'])
@require_POST
def goodmoral_decline(request, pk):
    r = get_object_or_404(GoodMoralRequest, pk=pk)
    reason = (request.POST.get('decline_message') or "").strip()
    if not reason:
        messages.error(request, "Decline reason is required.")
        return redirect('admin_view_goodmoral', pk=pk)

    r.is_approved = False
    r.is_rejected = True
    r.rejection_reason = reason
    r.save()

    subject = "Your Good Moral Certificate Request has been DECLINED"
    body = (
        f"Hello {r.requester_name},\n\n"
        f"Your Good Moral Certificate request for {r.first_name} {r.surname} "
        f"(Student ID: {r.student_id}) has been DECLINED.\n\n"
        f"Reason from the Office:\n{reason}\n\n"
        "If you believe this was an error or need assistance, please reply to this email."
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [r.requester_email], fail_silently=False)
        messages.success(request, "Request declined and email sent.")
    except Exception as e:
        messages.warning(request, f"Declined, but email failed: {e}")

    return redirect('admin_view_goodmoral', pk=pk)

TEMPLATE_PATH = os.path.join(settings.BASE_DIR, 'myapp', 'static', 'myapp', 'pdf', 'GMC-request-template.pdf')

@role_required(['admin'])
def goodmoral_request_form_pdf(request, pk):
    from django.utils import timezone
    from io import BytesIO

    r = get_object_or_404(GoodMoralRequest, pk=pk)

    template_path = finders.find('myapp/form/GMC-request-template.pdf')
    if not template_path:
        raise Http404("Template PDF not found.")

    with open(template_path, 'rb') as f:
        base_pdf_bytes = f.read()
    base_reader = PdfReader(BytesIO(base_pdf_bytes))
    base_page = base_reader.pages[0]
    llx, lly, urx, ury = map(float, base_page.mediabox)
    width, height = urx - llx, ury - lly

    overlay_buf = BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(width, height))

    # ---------- helpers ----------
    def check(x, y):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "✓")

    def text(x, y, s, bold=False, size=11, right=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        if right:
            c.drawRightString(x, y, s or "")
        else:
            c.drawString(x, y, s or "")

    def draw_guides(step=25):
        c.setFont("Helvetica", 6)
        c.setFillGray(0.6)
        for x in range(0, int(width), step):
            c.line(x, 0, x, height); c.drawString(x+1, 2, str(x))
        for y in range(0, int(height), step):
            c.line(0, y, width, y); c.drawString(2, y+2, str(y))
        c.setFillGray(0)

    if request.GET.get("guide") == "1":
        draw_guides()

    # ---------- TOP ROW: NO. and DATE ----------
    # Use the DB primary key as the request number (zero-padded). Change to r.student_id if you prefer.
    req_no = f"{r.pk:06d}"
    # Coordinates are close; open with ?guide=1 and nudge ±5–15 if needed.
    text(70, height - 135, req_no, bold=True, size=12)  # NO. (left box)

    # Date from submitted_at, rendered as local calendar date (respects TIME_ZONE / activation)
    date_requested = timezone.localdate(r.submitted_at).strftime('%m/%d/%Y')
    text(width - 180, height - 135, date_requested, bold=True, size=12, right=True)  # DATE (right box)

    # ---------- PLACE FIELDS ----------
    surname = (r.surname or "").upper()
    first = (r.first_name or "").upper()
    ext = (r.ext or "").upper()
    mi = ((r.middle_name[:1] + ".").upper() if r.middle_name else "")

    text(45, 660, surname)
    text(120, 660, first)
    text(210, 660, ext)
    text(240, 660, mi)

    # Sex checkboxes
    sex = (r.sex or "").lower()
    if sex.startswith("m"):
        check(320, 660)  # Male
    elif sex.startswith("f"):
        check(375, 660)  # Female

    # Program & Status
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontSize = 8
    styleN.leading = 8  # spacing between wrapped lines

    # Wrap program text inside a fixed width
    max_width = 280  # adjust to fit your table cell
    prog_para = Paragraph(r.program or "", styleN)
    prog_para.wrapOn(c, max_width, 100)   # ✅ use c (the Canvas instance)
    prog_para.drawOn(c, 45, 610)          # ✅ use c (the Canvas instance)

    status = (r.status or "").lower()
    if "alum" in status or "gradu" in status:
        check(60, 580)
        if r.date_graduated:
            text(160, 565, r.date_graduated.strftime('%Y'))
    elif "former" in status:
        check(60, 550)
        text(190, 535, r.inclusive_years)
    else:
        check(60, 520)
        text(170, 505, r.date_admission)

    # Purpose of Request
    purpose_raw = r.purpose or ""
    purpose = purpose_raw.strip().lower()
    other = (r.other_purpose or "").strip()

    if "transfer" in purpose:
        check(330, 610);  text(360, 595, other, size=8) if other else None
    elif "continu" in purpose or "continuing education" in purpose:
        check(330, 583)
    elif "employment" in purpose:
        check(330, 555)
    elif "scholar" in purpose:
        check(330, 530);  text(360, 515, other) if other else None
    elif any(k in purpose for k in (
            "sit", "supervised industrial training", "ipt",
            "in-campus practice teaching", "opt", "off-campus practice teaching")):
        check(330, 500)
    elif any(k in purpose for k in ("student development", "comselec", "usg", "award")):
        check(330, 460)
    else:
        check(330, 420); text(420, 420, other or purpose_raw)

    # Requester info
    text(85, 345, r.requester_name)
    text(415, 345, r.requester_contact)
    text(205, 330, r.relationship)

    # done
    c.showPage()
    c.save()
    overlay_buf.seek(0)

    # Merge & return
    overlay_reader = PdfReader(overlay_buf)
    writer = PdfWriter()
    page = base_reader.pages[0]
    page.merge_page(overlay_reader.pages[0])
    writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    out.seek(0)
    return FileResponse(out, as_attachment=False, filename=f"GMC_RequestForm_{r.student_id or r.pk}.pdf")

@role_required(['admin'])
@xframe_options_exempt
def view_gmf(request, pk):
    req = get_object_or_404(GoodMoralRequest, pk=pk)
    pdf_bytes = generate_gmf_pdf(req)  # now returns bytes
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="GMF_{req.student_id or req.pk}.pdf"'
    resp["Content-Length"] = str(len(pdf_bytes))
    return resp

@role_required(['admin'])
@xframe_options_exempt
def batch_view_gmf(request):
    """
    /gmf/batch-preview?frm=1&to=10
    Returns one inline PDF for all GoodMoralRequest where is_rejected=False,
    sliced by the provided 1-based indices.
    """
    def _num(x, default):
        try:
            v = int(x)
            return v if v >= 1 else default
        except Exception:
            return default

    frm = _num(request.GET.get('frm'), 1)
    to  = _num(request.GET.get('to'),  frm)
    if to < frm:
        return HttpResponseBadRequest("Invalid range.")

    # Filter first, slice second. This includes pending+approved, excludes rejected.
    qs = (GoodMoralRequest.objects
          .filter(is_rejected=False)
          .order_by('submitted_at', 'pk'))  # mirror your UI sort if needed

    start = frm - 1
    end   = to
    rows = list(qs[start:end])
    if not rows:
        return HttpResponseBadRequest("No requests in that range (after filtering).")

    merger = PdfMerger(strict=False)
    for req in rows:
        try:
            pdf_bytes = generate_gmf_pdf(req)  # your existing function
            merger.append(BytesIO(pdf_bytes))
        except Exception:
            # Skip problematic rows silently; log if you prefer
            continue

    out = BytesIO()
    merger.write(out)
    merger.close()
    out.seek(0)

    resp = HttpResponse(out.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="GMF_batch_{frm}-{to}.pdf"'
    resp["Content-Length"] = str(len(out.getvalue()))
    return resp

@role_required(['admin'])
def admin_ackreq_receipt_pdf(request, pk):
    req = get_object_or_404(IDSurrenderRequest, pk=pk)

    # Pull the single active admin's name and uppercase it
    admin_acc = UserAccount.objects.filter(role='admin', is_active=True).order_by('-created_at').first()
    admin_name_upper = (admin_acc.full_name if admin_acc else "ADMIN").upper()

    try:
        pdf_path = build_ack_pdf(req, admin_name_upper)
    except Exception as e:
        # show a basic error in-browser
        raise Http404(f"PDF generation failed: {e}")

    # Stream inline so Chrome opens a new tab instead of forcing a download
    filename = os.path.basename(pdf_path)
    resp = FileResponse(open(pdf_path, "rb"), content_type=mimetypes.types_map.get(".pdf", "application/pdf"))
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp

def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'

@role_required(['admin'])
@require_POST
def admin_ackreq_accept(request, pk):
    req = get_object_or_404(IDSurrenderRequest, pk=pk)

    if req.status != IDSurrenderRequest.STATUS_PENDING:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Request already finalized."}, status=400)
        messages.warning(request, "This request is already finalized.")
        return redirect("admin_view_ackreq", pk=req.pk)

    msg = (request.POST.get("message") or "").strip()
    if not msg:
        msg = ("Your ID surrender request has been accepted. "
               "You may claim the acknowledgement receipt at the Office of Student Affairs during office hours. "
               "Please bring a valid ID.")

    req.status = IDSurrenderRequest.STATUS_APPROVED
    req.message = msg
    req.save(update_fields=["status", "message"])

    # best-effort email
    if req.contact_email:
        try:
            send_mail(
                subject="ID Surrender Request — Accepted",
                message=(f"Hello {req.first_name},\n\n{msg}\n\n"
                         f"Student Number: {req.student_number}\n"
                         f"Program: {req.program}\n"
                         f"Year Level: {req.year_level}\n"
                         f"Reason: {req.get_reason_display()}\n\n— Office of Student Affairs"),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[req.contact_email],
                fail_silently=True,
            )
        except Exception:
            pass

    if _is_ajax(request):
        return JsonResponse({"ok": True, "status": req.status, "message": req.message})

    messages.success(request, "Request accepted and email sent.")
    return redirect("admin_view_ackreq", pk=req.pk)

@role_required(['admin'])
@require_POST
def admin_ackreq_decline(request, pk):
    req = get_object_or_404(IDSurrenderRequest, pk=pk)

    if req.status != IDSurrenderRequest.STATUS_PENDING:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Request already finalized."}, status=400)
        messages.warning(request, "This request is already finalized.")
        return redirect("admin_view_ackreq", pk=req.pk)

    msg = (request.POST.get("message") or "").strip()
    if not msg:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "A reason/message is required to decline."}, status=400)
        messages.error(request, "A reason/message is required to decline.")
        return redirect("admin_view_ackreq", pk=req.pk)

    req.status = IDSurrenderRequest.STATUS_DECLINED
    req.message = msg
    req.save(update_fields=["status", "message"])

    if req.contact_email:
        try:
            send_mail(
                subject="Update on your ID Surrender Request",
                message=(f"Hello {req.first_name},\n\n"
                         f"Status: Declined\n"
                         f"Reason/Notes:\n{msg}\n\n"
                         "If you have questions, please reply to this email.\n\n— Office of Student Affairs"),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[req.contact_email],
                fail_silently=True,
            )
        except Exception:
            pass

    if _is_ajax(request):
        return JsonResponse({"ok": True, "status": req.status, "message": req.message})

    messages.success(request, "Request declined and email sent.")
    return redirect("admin_view_ackreq", pk=req.pk)

@role_required(['admin'])
@transaction.atomic
def admin_decline_violation(request, violation_id):
    v = Violation.objects.select_for_update().get(id=violation_id)
    # lock the student row to serialize actions for the same student
    student = Student.objects.select_for_update().get(tupc_id=v.student_id)

    if v.status == 'Rejected':
        messages.info(request, "Already declined.")
        return redirect('admin_violation')

    # delete files from storage (saves space)
    if v.evidence_1:
        v.evidence_1.delete(save=False); v.evidence_1 = None
    if v.evidence_2:
        v.evidence_2.delete(save=False); v.evidence_2 = None

    # reset workflow/settlement info
    v.status = 'Rejected'
    v.reviewed_at = timezone.now()
    v.approved_at = None
    v.approved_by = ""
    v.settlement_type = "None"
    v.is_settled = False
    v.settled_at = None
    v.save(update_fields=[
        "status","reviewed_at","approved_at","approved_by",
        "settlement_type","is_settled","settled_at","evidence_1","evidence_2"
    ])

    # send only after DB commit
    transaction.on_commit(lambda: send_violation_email(
        request=request,
        violation=v,
        student=student,
        declined=True,
    ))

    messages.error(request, f"❌ Violation for {student.first_name} {student.last_name} was declined.")
    return redirect('admin_violation')

@role_required(['admin'])
@transaction.atomic
def admin_approve_violation(request, violation_id):
    v = Violation.objects.select_for_update().get(id=violation_id)              # lock this violation
    student = Student.objects.select_for_update().get(tupc_id=v.student_id)     # lock per-student

    # Idempotent approve + stamp
    if v.status != 'Approved':
        v.mark_approved(by_user=getattr(request.user, "get_full_name", lambda:"")())

    # Count approved MINORs for this student (includes this one now)
    # Ensure your model has severity with default 'MINOR'; otherwise drop this filter.
    approved_count = (
        Violation.objects
        .filter(student_id=student.tupc_id, status='Approved', severity='MINOR')
        .count()
    )

    # Business rule: 1st -> Apology Letter, 2nd+ -> Community Service
    new_settlement = 'Apology Letter' if approved_count == 1 else 'Community Service'

    # Tag settlement on this violation (reset settled flags)
    if (v.settlement_type != new_settlement) or v.is_settled:
        v.settlement_type = new_settlement
        v.is_settled = False
        v.settled_at = None
        v.save(update_fields=["settlement_type","is_settled","settled_at"])

    # send only after commit (avoids emails if transaction rolls back)
    transaction.on_commit(lambda: send_violation_email(
        request=request,
        violation=v,
        student=student,
        violation_count=approved_count,
        settlement_type=new_settlement,
    ))

    messages.success(request, f"✅ Approved. Settlement: {new_settlement}.")
    return redirect('admin_violation')

@role_required(['admin'])
@transaction.atomic
def mark_apology_settled(request, violation_id):
    v = get_object_or_404(Violation, id=violation_id)
    if v.status != 'Approved' or v.settlement_type != 'Apology Letter':
        messages.error(request, "This violation is not an unsettled Apology Letter.")
        return redirect(f"{reverse('admin_view_violation')}?violation_id={v.id}")

    if not v.is_settled:
        v.is_settled = True
        v.settled_at = timezone.now()
        v.save(update_fields=['is_settled','settled_at'])

    messages.success(request, "✅ Apology Letter marked as received.")
    return redirect(f"{reverse('admin_view_violation')}?violation_id={v.id}")

@role_required(['admin'])
@transaction.atomic
def cs_create_or_adjust(request):
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect('admin_community_service')

    form = CSCreateOrAdjustForm(request.POST)

    if not form.is_valid():
        # rebuild the list and re-render the page with the modal open
        q = (request.GET.get('q') or '').strip()
        cases = CommunityServiceCase.objects.order_by('is_closed', '-updated_at')
        if q:
            cases = cases.filter(
                Q(student_id__icontains=q) |
                Q(last_name__icontains=q) |
                Q(first_name__icontains=q) |
                Q(program_course__icontains=q)
            )
        return render(request, 'myapp/admin_community_service.html', {
            'cases': cases,
            'q': q,
            'cs_form': form,       # bound form with field errors
            'show_cs_modal': True, # auto-open modal
        })

    # ----- valid submission -----
    data = form.cleaned_data
    sid = data["student_id"]
    new_total = Decimal(data["hours"])

    # lock any existing open case for this student
    case = (CommunityServiceCase.objects
            .select_for_update()
            .filter(student_id=sid, is_closed=False)
            .first())

    if case:
        # update snapshot (admin may correct spelling each time)
        case.last_name = data["last_name"]
        case.first_name = data["first_name"]
        case.middle_initial = data.get("middle_initial") or ""
        case.extension_name = data.get("extension_name") or ""
        case.program_course = data["program_course"]
        case.save(update_fields=[
            "last_name","first_name","middle_initial","extension_name","program_course","updated_at"
        ])

        # set TOTAL required hours (completed stays the same)
        case.adjust_total_required(new_total)
        messages.success(
            request,
            f"Hours set to {case.total_required_hours}h for {case.last_name}, {case.first_name}. "
            f"Remaining: {case.remaining_hours}h."
        )
    else:
        case = CommunityServiceCase.objects.create(
            last_name=data["last_name"],
            first_name=data["first_name"],
            middle_initial=data.get("middle_initial") or "",
            extension_name=data.get("extension_name") or "",
            program_course=data["program_course"],
            student_id=sid,
            total_required_hours=new_total,
            hours_completed=Decimal("0.0"),
            is_closed=(new_total == Decimal("0.0")),
        )
        messages.success(
            request,
            f"Community Service created for {case.last_name}, {case.first_name} ({case.student_id}) "
            f"with {case.total_required_hours}h."
        )

    return redirect('admin_view_community_service', case_id=case.id)

def cs_update_total_required(request, case_id):
    case = CommunityServiceCase.objects.select_for_update().get(id=case_id)
    try:
        total = Decimal(request.POST.get('total', '').strip())
    except Exception:
        return HttpResponseBadRequest("Invalid total hours.")
    if total < case.hours_completed:
        total = case.hours_completed  # never below completed

    case.adjust_total_required(total)
    return JsonResponse({
        "ok": True,
        "total_required_hours": str(case.total_required_hours),
        "hours_completed": str(case.hours_completed),
        "remaining_hours": str(case.remaining_hours),
        "is_closed": case.is_closed,
    })

# Helpers
def _extract_tupc_id(raw: str) -> str | None:
    # Generic + forgiving: grabs 'TUPC-<2 digits>-<digits>' until whitespace/end
    import re
    m = re.search(r'(TUPC-\d{2}-\d+)(?=\s|$)', raw or '', flags=re.IGNORECASE)
    return m.group(1).upper() if m else None

# AJAX: scanner -> TIME IN

@require_POST
@transaction.atomic
def cs_scan_time_in(request, case_id):
    case = CommunityServiceCase.objects.select_for_update().get(id=case_id)
    scanned_raw = request.POST.get('scanned', '')
    scanned_id = _extract_tupc_id(scanned_raw)
    if not scanned_id or scanned_id != case.student_id:
        return JsonResponse({"ok": False, "error": "ID mismatch or unreadable scan."}, status=400)
    if case.is_closed:
        return JsonResponse({"ok": False, "error": "Case is closed. Add hours first."}, status=400)
    log = case.open_session()
    return JsonResponse({"ok": True, "status": "time_in", "log_id": log.id})

# AJAX: scanner -> TIME OUT

@require_POST
@transaction.atomic
def cs_scan_time_out(request, case_id):
    case = CommunityServiceCase.objects.select_for_update().get(id=case_id)
    scanned_raw = request.POST.get('scanned', '')
    scanned_id = _extract_tupc_id(scanned_raw)
    if not scanned_id or scanned_id != case.student_id:
        return JsonResponse({"ok": False, "error": "ID mismatch or unreadable scan."}, status=400)
    log = case.close_open_session()
    if not log:
        return JsonResponse({"ok": False, "error": "No open session to close."}, status=400)
    return JsonResponse({"ok": True, "status": "time_out", "credited_hours": str(log.hours)})








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

