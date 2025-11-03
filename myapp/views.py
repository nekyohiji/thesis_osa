# ── Standard library
import calendar
import csv
import io
import secrets
import json
import logging
import mimetypes
import os
import random
import re
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from io import BytesIO
from . import models
from functools import wraps
# ── Third-party
from PIL import Image as PILImage
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape, inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    Image as RLImage,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus import Table as PlatypusTable
from reportlab.platypus import TableStyle as PlatypusTableStyle
from reportlab.platypus import Image
# ── Django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.finders import find as find_static
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import BadHeaderError, send_mail
from django.core.paginator import EmptyPage, Paginator
from django.core.serializers import serialize
from django.core.cache import cache
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, DateTimeField, F, Q, Value, DateField
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear, Lower, TruncMonth
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import escape
from django.utils.timezone import localtime, now
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.hashers import make_password, check_password
from django.db import IntegrityError
# ── Local apps
from .decorators import role_required, facilitator_required
from .forms import (
    CSCreateOrAdjustForm,
    ClearanceRequestForm,
    GoodMoralRequestForm,
    IDSurrenderRequestForm,
    AddViolationForm,
    ViolationForm,
    FacilitatorForm
)
from .libre.ack_receipt import build_ack_pdf
from .models import (
    ACSORequirement,
    Archived_Account,
    ClearanceRequest,
    CommunityServiceCase,
    CommunityServiceLog,
    CommunityServiceAdjustment,
    GoodMoralRequest,
    IDSurrenderRequest,
    LostAndFound,
    OTPVerification,
    Scholarship,
    Student,
    StudentAssistantshipRequirement,
    UserAccount,
    Violation,
    Facilitator,
    Election,
    EligibleVoter,
    Vote,
    Candidate,
)
from .utils import (
    generate_gmf_pdf,
    send_clearance_confirmation,
    send_violation_email,
    build_student_email,
    send_violation_notice,
    send_mail_async,
    no_store,
    compute_cs_topup_for_minor,
    CS_EXEMPT_TYPES,
    )

logger = logging.getLogger(__name__)
#################################################################################################################

def current_time(request):
    return JsonResponse({'now': now().isoformat()})

def index(request):
    return HttpResponse("🎓 Hello from your thesis web app!")

def home_view(request):
    return render(request, 'myapp/client_home.html')

#------------------------------------------------------------------------------------------#

def client_goodmoral_view(request):
    return render (request, 'myapp/client_goodmoral.html')

def client_scholarships_view(request):
    scholarships = Scholarship.objects.order_by('-posted_date')
    return render (request, 'myapp/client_scholarships.html', {'scholarships': scholarships})

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

def client_clearance_view(request):
    return render (request, 'myapp/client_clearance.html')

#------------------------------------------------------------------------------------------#

def admin_insurance_view(request):
    return render (request, 'myapp/admin_insurance.html')


#------------------------------------------------------------------------------------------#

@role_required(['admin', 'staff'])
def admin_old_violation_view(request):     
    return render (request, 'myapp/admin_old_violation.html')

@role_required(['admin', 'staff'])
def admin_add_faculty_view(request):
    open_add_modal = False

    if request.method == "POST":
        form = FacilitatorForm(request.POST)
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                if getattr(request, "user", None) and request.user.is_authenticated:
                    obj.created_by = request.user
                obj.save()
                messages.success(request, "Facilitator added.")
                return redirect("admin_add_faculty")
            except IntegrityError as e:
                # fall back in case race condition or non-form path
                msg = str(e).lower()
                if "email" in msg:
                    form.add_error("email", "That email already exists.")
                elif "faculty_id" in msg:
                    form.add_error("faculty_id", "That ID already exists.")
                else:
                    form.add_error(None, "Duplicate record.")
                messages.error(request, "Please fix the errors below.")
                open_add_modal = True
        else:
            messages.error(request, "Please fix the errors below.")
            open_add_modal = True
    else:
        form = FacilitatorForm()

    q = (request.GET.get("q") or "").strip()
    facilitators = Facilitator.objects.all()
    if q:
        facilitators = facilitators.filter(
            Q(full_name__icontains=q) | Q(faculty_id__icontains=q) | Q(email__icontains=q)
        )

    ctx = {
        "form": form,
        "facilitators": facilitators,
        "q": q,
        "open_add_modal": open_add_modal,
    }
    return render(request, "myapp/admin_add_faculty.html", ctx)

@role_required(['admin', 'staff'])
def facilitator_delete(request, pk: int):
    """
    Confirm modal posts here. Only accept POST, then redirect back to the page.
    """
    if request.method != "POST":
        return redirect("admin_add_faculty")

    obj = get_object_or_404(Facilitator, pk=pk)
    name = obj.full_name
    obj.delete()
    messages.success(request, f"Removed facilitator: {name}")
    return redirect("admin_add_faculty")

#------------------------------------------------------------------------------------------#

@role_required(['admin', 'staff', 'studasst'])
def admin_dashboard_view(request):
    return render(request, 'myapp/admin_dashboard.html')

@role_required(['admin', 'staff', 'studasst'])
def admin_dashboard_data(request):
    """
    Return monthly counts + totals as JSON.

    - Card totals:
        * Good Moral: approved + rejected
        * ID Surrender: approved + declined (as "rejected")
        * Clearance: all only (no 'rejected' concept)

    - Monthly rows:
        * Per-month approved & rejected for GM and Surrender
        * Clearance has only "all" (rejected = 0)
        * Any NULL datetimes go into an 'Undated' row

    This preserves existing keys your UI already uses, and *adds*
    rejected keys so you can light up those new counters.
    """

    # ---------- Card totals ----------
    # Good Moral
    gm_approved = GoodMoralRequest.objects.filter(is_approved=True, is_rejected=False).count()
    gm_rejected = GoodMoralRequest.objects.filter(is_rejected=True).count()

    # ID Surrender
    surr_approved = IDSurrenderRequest.objects.filter(
        status=IDSurrenderRequest.STATUS_APPROVED
    ).count()
    surr_rejected = IDSurrenderRequest.objects.filter(
        status=IDSurrenderRequest.STATUS_DECLINED
    ).count()

    # Clearance (no reject)
    clr_all = ClearanceRequest.objects.count()

    totals = {
        # Existing keys (kept):
        "surrender_approved": surr_approved,
        "goodmoral_approved": gm_approved,
        "clearance_all": clr_all,
        "grand_total": surr_approved + gm_approved + clr_all,  # headline number you already show

        # NEW keys (for your Accepted/Rejected breakdowns):
        "goodmoral_rejected": gm_rejected,
        "surrender_rejected": surr_rejected,

        # Optional: convenient grand splits (clearance has no rejected)
        "grand_accepted": surr_approved + gm_approved + clr_all,
        "grand_rejected": surr_rejected + gm_rejected,
    }

    # ---------- Helper: aggregate by (year, month) in Python ----------
    def month_counts_py(qs, dt_field: str):
        """
        Returns (agg, undated_count) where:
          - agg is list of {'y': int, 'm': int, 'count': int} sorted by (y,m)
          - undated_count is count of rows with NULL dt_field
        """
        buckets = Counter()
        undated = 0

        for dt in qs.values_list(dt_field, flat=True).iterator():
            if not dt:
                undated += 1
                continue
            try:
                if timezone.is_aware(dt):
                    dt = timezone.localtime(dt)
            except Exception:
                undated += 1
                continue
            buckets[(dt.year, dt.month)] += 1

        agg = [{"y": y, "m": m, "count": c} for (y, m), c in sorted(buckets.items())]
        return agg, undated

    # ---------- Querysets for monthly aggregation ----------
    # GM: approved & rejected
    gm_qs_approved  = GoodMoralRequest.objects.filter(is_approved=True, is_rejected=False)
    gm_qs_rejected  = GoodMoralRequest.objects.filter(is_rejected=True)

    # Surrender: approved & declined (treated as rejected)
    surr_qs_approved = IDSurrenderRequest.objects.filter(status=IDSurrenderRequest.STATUS_APPROVED)
    surr_qs_rejected = IDSurrenderRequest.objects.filter(status=IDSurrenderRequest.STATUS_DECLINED)

    # Clearance: all (no rejected path)
    clr_qs = ClearanceRequest.objects.all()

    # ---------- Monthly aggregation ----------
    gm_agg_appr,   gm_undated_appr   = month_counts_py(gm_qs_approved,  "submitted_at")
    gm_agg_rej,    gm_undated_rej    = month_counts_py(gm_qs_rejected,  "submitted_at")
    surr_agg_appr, surr_undated_appr = month_counts_py(surr_qs_approved, "submitted_at")
    surr_agg_rej,  surr_undated_rej  = month_counts_py(surr_qs_rejected, "submitted_at")
    clr_agg_all,   clr_undated_all   = month_counts_py(clr_qs,           "created_at")

    # ---------- Combine into a single (year, month) map ----------
    # We keep existing fields you already render AND add rejected fields (zero for clearance).
    by_month = {}  # key: (y, m) -> dict of fields

    def bump(key, field, n):
        d = by_month.setdefault(
            key,
            {
                "surrender_approved": 0, "surrender_rejected": 0,
                "goodmoral_approved": 0, "goodmoral_rejected": 0,
                "clearance_all": 0,
            },
        )
        d[field] += int(n or 0)

    # Fill buckets
    for r in surr_agg_appr:
        bump((int(r["y"]), int(r["m"])), "surrender_approved", r["count"])
    for r in surr_agg_rej:
        bump((int(r["y"]), int(r["m"])), "surrender_rejected", r["count"])

    for r in gm_agg_appr:
        bump((int(r["y"]), int(r["m"])), "goodmoral_approved", r["count"])
    for r in gm_agg_rej:
        bump((int(r["y"]), int(r["m"])), "goodmoral_rejected", r["count"])

    for r in clr_agg_all:
        bump((int(r["y"]), int(r["m"])), "clearance_all", r["count"])

    # ---------- Build rows (newest month first) ----------
    rows = []
    for (y, m), vals in sorted(by_month.items(), key=lambda kv: kv[0], reverse=True):
        month_dt = datetime(int(y), int(m), 1)
        total = (
            vals["surrender_approved"] +
            vals["surrender_rejected"] +    # included in monthly total
            vals["goodmoral_approved"] +
            vals["goodmoral_rejected"] +    # included in monthly total
            vals["clearance_all"]
        )
        rows.append({
            "month_iso": month_dt.strftime("%Y-%m-01"),
            "month_label": month_dt.strftime("%B %Y"),
            **vals,
            "total": total,
        })

    # ---------- Optional 'Undated' ----------
    undated_totals = {
        "surrender_approved": surr_undated_appr,
        "surrender_rejected": surr_undated_rej,
        "goodmoral_approved": gm_undated_appr,
        "goodmoral_rejected": gm_undated_rej,
        "clearance_all":      clr_undated_all,
    }
    undated_total = sum(undated_totals.values())
    if undated_total:
        rows.append({
            "month_iso": "undated",
            "month_label": "Undated",
            **undated_totals,
            "total": undated_total,
        })

    return JsonResponse({
        "as_of": timezone.localtime().isoformat(),
        "totals": totals,
        "rows": rows,
    })

@role_required(['admin', 'staff'])
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

@role_required(['admin', 'staff'])
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

@role_required(['admin', 'staff'])
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

@role_required(['admin', 'staff'])
def admin_view_community_service(request, case_id):
    case = get_object_or_404(CommunityServiceCase, id=case_id)
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

@role_required(['admin', 'staff', 'studasst'])
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

@role_required(['admin', 'staff', 'scholarship'])
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

@role_required(['admin', 'staff', 'studasst'])
def admin_view_ackreq_view(request, pk):
    req = get_object_or_404(IDSurrenderRequest, pk=pk)
    return render(request, 'myapp/admin_view_ackreq.html', {"req": req})

@role_required(['admin', 'staff', 'studasst'])
def admin_view_goodmoral_view(request):
    return render (request, 'myapp/admin_view_goodmoral.html')

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

@never_cache
@never_cache
def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email) or len(email) > 164:
            messages.error(request, "Please enter a valid email address.", extra_tags="LOGIN")
            resp = render(request, 'myapp/login.html', {"next": next_url})
            return no_store(resp)

        if not (8 <= len(password) <= 128):
            messages.error(request, "Password must be between 8 and 128 characters.", extra_tags="LOGIN")
            resp = render(request, 'myapp/login.html', {"next": next_url})
            return no_store(resp)

        try:
            user = UserAccount.objects.get(email=email, is_active=True)
            if check_password(password, user.password):
                if user.must_change_password:
                    messages.info(request,
                        "Security requirement: Please set a new password to continue.",
                        extra_tags="LOGIN")
                    ctx = {
                        "next": next_url,
                        "force_pw_change": True,        
                        "force_reset_email": user.email, 
                    }
                    resp = render(request, 'myapp/login.html', ctx)
                    return no_store(resp)

                request.session.flush()
                request.session['user_id'] = user.id
                request.session['role'] = user.role
                request.session['full_name'] = user.full_name
                request.session['email'] = user.email
                request.session.set_expiry(0)

                if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                    resp = redirect(next_url)
                    return no_store(resp)

                role = (user.role or "").lower()
                if role in ('admin', 'staff', 'studasst'):
                    resp = redirect('admin_dashboard')
                elif role == 'guard':
                    resp = redirect('guard_violation')
                elif role == 'scholarship':
                    resp = redirect('admin_scholarships')
                elif role == 'comselec':
                    resp = redirect('admin_election')
                else:
                    messages.error(request, "Account role not recognized.", extra_tags="LOGIN")
                    resp = render(request, 'myapp/login.html', {"next": next_url})
                return no_store(resp)

            else:
                messages.error(request, "Incorrect password.", extra_tags="LOGIN")
        except UserAccount.DoesNotExist:
            messages.error(request, "Account not found or inactive.", extra_tags="LOGIN")

    resp = render(request, 'myapp/login.html', {"next": next_url})
    return no_store(resp)

def logout_view(request):
    request.session.flush()
    resp = redirect('login')
    return no_store(resp)

LOGIN_OTP_TTL_MINUTES = 5
LOGIN_OTP_LENGTH = 6
LOGIN_MAX_VERIFY_ATTEMPTS = 3
LOGIN_SEND_RATE_WINDOW_SEC = 60
LOGIN_SESSION_RESET_OK_FOR = 'LOGIN_otp_reset_ok_for'

def LOGIN_cache_key_attempts(email): return f"LOGIN_otp_attempts:{email.lower()}"
def LOGIN_cache_key_send(email):     return f"LOGIN_otp_send_ts:{email.lower()}"
def LOGIN_now():                     return timezone.now()

@require_POST
def login_send_otp(request):
    email = request.POST.get('email', '').strip().lower()
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) or len(email) > 164:
        return JsonResponse({"ok": False, "msg": "Please enter a valid email."}, status=400)
    try:
        user = UserAccount.objects.get(email=email, is_active=True)
    except UserAccount.DoesNotExist:
        return JsonResponse({"ok": False, "msg": "No active account found for this email."}, status=404)

    last_send = cache.get(LOGIN_cache_key_send(email))
    if last_send and (LOGIN_now() - last_send).total_seconds() < LOGIN_SEND_RATE_WINDOW_SEC:
        return JsonResponse({"ok": False, "msg": "Please wait before requesting another code."}, status=429)

    code = f"{random.randint(0, 10**LOGIN_OTP_LENGTH - 1):0{LOGIN_OTP_LENGTH}d}"

    with transaction.atomic():
        # Ensure created_at is refreshed on *every* send
        rec, _created = OTPVerification.objects.select_for_update().update_or_create(
            email=email,
            defaults={
                "otp": make_password(code),
                "full_name": user.full_name,
                "role": user.role,
                "password": "",
                "is_active": True,
                "created_at": timezone.now(),   # <-- critical line
            }
        )
        cache.set(LOGIN_cache_key_attempts(email),
                  LOGIN_MAX_VERIFY_ATTEMPTS,
                  LOGIN_OTP_TTL_MINUTES * 60)

    subject = "Your OTP Code (valid 5 minutes)"
    body = f"Hello {user.full_name or ''},\n\nYour password reset code is: {code}\nIt expires in {LOGIN_OTP_TTL_MINUTES} minutes."
    send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", None), [email], fail_silently=False)

    cache.set(LOGIN_cache_key_send(email), LOGIN_now(), LOGIN_SEND_RATE_WINDOW_SEC)
    return JsonResponse({"ok": True, "msg": "OTP sent. Check your email."})

@require_POST
def login_verify_otp(request):
    email = request.POST.get('email', '').strip().lower()
    code  = request.POST.get('otp', '').strip()
    if not email or not code:
        return JsonResponse({"ok": False, "msg": "Email and code are required."}, status=400)

    try:
        rec = OTPVerification.objects.get(email=email, is_active=True)
    except OTPVerification.DoesNotExist:
        return JsonResponse({"ok": False, "msg": "No pending reset request for this email."}, status=404)

    if LOGIN_now() - rec.created_at > timedelta(minutes=LOGIN_OTP_TTL_MINUTES):
        return JsonResponse({"ok": False, "msg": "Code expired. Please request a new one."}, status=410)

    attempts = cache.get(LOGIN_cache_key_attempts(email), LOGIN_MAX_VERIFY_ATTEMPTS)
    if attempts <= 0:
        return JsonResponse({"ok": False, "msg": "Too many attempts. Request a new code."}, status=429)

    if not check_password(code, rec.otp):
        cache.set(LOGIN_cache_key_attempts(email), attempts - 1, LOGIN_OTP_TTL_MINUTES * 60)
        return JsonResponse({"ok": False, "msg": f"Incorrect code. Attempts left: {attempts - 1}"}, status=401)

    request.session[LOGIN_SESSION_RESET_OK_FOR] = email
    cache.delete(LOGIN_cache_key_attempts(email))
    return JsonResponse({"ok": True, "msg": "Code verified. You can now set a new password."})

@require_POST
def login_reset_password(request):
    email = request.POST.get('email', '').strip().lower()
    new_password = request.POST.get('new_password', '').strip()
    confirm = request.POST.get('confirm_password', '').strip()

    if request.session.get(LOGIN_SESSION_RESET_OK_FOR) != email:
        return JsonResponse({"ok": False, "msg": "Verification required or session expired."}, status=403)
    if len(new_password) < 8:
        return JsonResponse({"ok": False, "msg": "Password must be at least 8 characters."}, status=400)
    if len(new_password) > 128:
        return JsonResponse({"ok": False, "msg": "Password is too long."}, status=400)
    if new_password != confirm:
        return JsonResponse({"ok": False, "msg": "Passwords do not match."}, status=400)

    try:
        user = UserAccount.objects.get(email=email, is_active=True)
    except UserAccount.DoesNotExist:
        return JsonResponse({"ok": False, "msg": "Account not found or inactive."}, status=404)

    user.password = make_password(new_password)
    user.must_change_password = False   
    user.save(update_fields=['password', 'must_change_password'])

    OTPVerification.objects.filter(email=email).delete()
    cache.delete_many([LOGIN_cache_key_attempts(email), LOGIN_cache_key_send(email)])
    request.session.pop(LOGIN_SESSION_RESET_OK_FOR, None)

    return JsonResponse({
        "ok": True,
        "msg": "Password updated. Please log in with your new password."
    })




########################GUARD

@role_required(['guard'])
def guard_violation_view(request):
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')
    return render (request, 'myapp/guard_violation.html', {'guards': guards})

@role_required(['guard'])
def guard_report_view(request):
    violations = Violation.objects.all().order_by('-violation_date')
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')

    # Raw query params
    start_date_raw = (request.GET.get('start_date') or '').strip()
    end_date_raw   = (request.GET.get('end_date')   or '').strip()
    violation_type = (request.GET.get('violation_type') or '').strip()
    guard_name     = (request.GET.get('guard_name') or '').strip()

    # Hard server-side bounds
    FLOOR = date(2020, 1, 1)
    CEIL  = timezone.localdate()  # today (server time)

    def parse_ymd(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    start_date = parse_ymd(start_date_raw)
    end_date   = parse_ymd(end_date_raw)

    # Clamp only if provided
    if start_date:
        if start_date < FLOOR: start_date = FLOOR
    if end_date:
        if end_date > CEIL: end_date = CEIL

    # If both provided and reversed, swap
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

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
        'today': CEIL,  # for template max=...
    }
    return render(request, 'myapp/guard_report.html', context)


def submit_violation(request):
    guards = UserAccount.objects.filter(role='guard', is_active=True).order_by('full_name')

    if request.method == 'POST':
        form = ViolationForm(request.POST, request.FILES)
        severity_choice = request.POST.get('severity_choice') 

        if not severity_choice:
            messages.error(request, "Please select Minor or Major offense first.")
            return render(request, 'myapp/guard_violation.html', {
                'form': form,
                'guards': guards,
            })

        if form.is_valid():
            student_id = form.cleaned_data['student_id']

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
            v.severity = severity_choice  
            v.status = 'Pending'
            v.settlement_type = "None"
            v.is_settled = False
            v.save()

            messages.success(request, success_message)
            return redirect('guard_violation')
        else:
            return render(request, 'myapp/guard_violation.html', {
                'form': form,
                'guards': guards,
            })

    else:
        form = ViolationForm()

    return render(request, 'myapp/guard_violation.html', {
        'form': form,
        'guards': guards,
    })

@role_required(['guard'])
def generate_guard_report_pdf(request):
    # ---- Inputs (generate-only) ----
    start_date_raw = (request.GET.get('start_date') or '').strip()
    end_date_raw   = (request.GET.get('end_date')   or '').strip()
    guard_name     = (request.GET.get('guard_name') or '').strip()
    violation_type = (request.GET.get('violation_type') or '').strip()

    # Require a guard for this report
    if not guard_name:
        return HttpResponseBadRequest("guard_name is required")

    # ---- Server-side hard bounds ----
    FLOOR = date(2020, 1, 1)
    CEIL  = timezone.localdate()  # today (server time)

    def parse_ymd(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return None

    start_date = parse_ymd(start_date_raw) or FLOOR
    end_date   = parse_ymd(end_date_raw)   or CEIL
    if start_date < FLOOR: start_date = FLOOR
    if end_date > CEIL:    end_date   = CEIL
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # ---- Query: guard + dates (+ optional type) ----
    qs = (Violation.objects
          .filter(guard_name=guard_name,
                  violation_date__gte=start_date,
                  violation_date__lte=end_date))
    if violation_type:
        qs = qs.filter(violation_type=violation_type)

    # ---- Build PDF (inline viewer) ----
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="violations_report.pdf"'

    generated_on = timezone.localtime().strftime('%Y-%m-%d %H:%M')

    styles = getSampleStyleSheet()
    subtitle_style   = ParagraphStyle(name='Subtitle', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    table_cell_style = ParagraphStyle(name='table_cell', parent=styles['Normal'], fontSize=7, leading=9)

    def header_footer(canvas, doc):
        pass

    doc = BaseDocTemplate(
        response, pagesize=A4,  
        leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=60
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')
    doc.addPageTemplates([PageTemplate(id='normal', frames=[frame], onPage=header_footer)])

    elements = []
    elements.append(Paragraph("Violations Report", styles['Title']))
    elements.append(Spacer(1, 8))

    filt_bits = [
        f"From: {start_date.isoformat()}",
        f"To: {end_date.isoformat()}",
        f"Guard on Duty: {guard_name}",
    ]
    if violation_type:
        filt_bits.append(f"Violation Type: {violation_type}")
    elements.append(Paragraph(", ".join(filt_bits), subtitle_style))
    elements.append(Spacer(1, 10))

    headers = ['Student Name', 'Student ID', 'Program/Course', 'Date', 'Time',
               'Type of Violation', 'Reported By', 'Status']
    col_widths = [
        doc.width * 0.15, doc.width * 0.11, doc.width * 0.18, doc.width * 0.10,
        doc.width * 0.08, doc.width * 0.16, doc.width * 0.12, doc.width * 0.10,
    ]

    header_style = ParagraphStyle(
    name='HeaderWhite',
    parent=styles['Heading5'],
    textColor=colors.whitesmoke
    )

    rows = [[Paragraph(h, header_style) for h in headers]]

    for v in qs.order_by('violation_date', 'violation_time'):
        rows.append([
            Paragraph(f"{v.first_name} {v.last_name}", table_cell_style),
            Paragraph(str(getattr(v, 'student_id', '') or ''), table_cell_style),
            Paragraph(str(getattr(v, 'program_course', '') or ''), table_cell_style),
            Paragraph(v.violation_date.strftime("%Y-%m-%d"), table_cell_style),
            Paragraph((v.violation_time.strftime("%H:%M") if getattr(v, 'violation_time', None) else ""), table_cell_style),
            Paragraph(str(getattr(v, 'violation_type', '') or ''), table_cell_style),
            Paragraph(str(getattr(v, 'guard_name', '') or ''), table_cell_style),
            Paragraph(str(getattr(v, 'status', '') or ''), table_cell_style),
        ])

    total = max(0, len(rows) - 1)
    if total == 0:
        rows.append([Paragraph('No data', table_cell_style)] * len(headers))

    cardinal = colors.HexColor("#8C1515")
    light    = colors.HexColor("#F2F2F2")
    mid      = colors.HexColor("#E6E6E6")

    max_rows_per_page = 26  # header + 25
    for start in range(0, len(rows), max_rows_per_page - 1):
        chunk = rows[start:start + max_rows_per_page]
        table = Table(chunk, colWidths=col_widths, repeatRows=1)
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), cardinal),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]
        for i in range(1, len(chunk)):
            style.append(('BACKGROUND', (0, i), (-1, i),
                          light if (i + start) % 2 == 0 else mid))
        table.setStyle(TableStyle(style))
        elements.append(table)
        if start + max_rows_per_page - 1 < len(rows):
            elements.append(PageBreak())

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Violations: {total}", styles['Normal']))

    counts = Counter(v.violation_type for v in qs)
    if counts:
        elements.append(Spacer(1, 6))
        for vtype, c in counts.items():
            elements.append(Paragraph(f"{vtype}: {c}", styles['Normal']))

    # Signatures
    elements.append(Spacer(1, 60))
    block_w = 150
    sig_lbl = ParagraphStyle('sig_lbl', parent=styles['Normal'], alignment=TA_LEFT, fontSize=11)
    sig_nm  = ParagraphStyle('sig_nm',  parent=styles['Normal'], alignment=TA_LEFT, fontSize=10)
    sig_pr  = ParagraphStyle('sig_pr',  parent=styles['Normal'], alignment=TA_LEFT, fontSize=10)

    def sig_block(label, name):
        return [
            Paragraph(label, sig_lbl),
            Spacer(1, 18),
            Table([[Paragraph(name or "", sig_nm)]],
                  colWidths=[block_w],
                  style=[('LINEBELOW', (0, 0), (-1, -1), 1.25, colors.black),
                         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                         ('BOTTOMPADDING', (0, 0), (-1, -1), 6)],
                  hAlign='LEFT'),
            Spacer(1, 6),
            Paragraph("Printed Name with Signature", sig_pr)
        ]

    elements.extend(sig_block("Prepared by:", guard_name))
    elements.append(Spacer(1, 40))
    elements.extend(sig_block("Noted by:", ""))

    doc.build(elements)
    return response






########################ADMIN

@csrf_exempt
@role_required(['admin', 'staff'])
def upload_student_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        import re, unicodedata  # add these imports
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)

        def _mail_part(s: str) -> str:
            """lowercase, strip spaces/punct/accents, keep letters+digits only"""
            s = (s or "").strip()
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            s = re.sub(r'[^A-Za-z0-9]', '', s)  # removes spaces, dots, hyphens, apostrophes, etc.
            return s.lower()

        skipped_duplicates = []
        skipped_missing_fields = []
        skipped_invalid_lengths = []

        for line_num, row in enumerate(reader, start=2):
            cleaned_row = {k.strip().upper(): (v.strip() if v is not None else '') for k, v in row.items()}

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

            # normalize MI/EXT fields for storage
            middle_initial = '' if middle_initial in ['', 'NA'] else middle_initial
            extension = '' if extension in ['', 'NA'] else extension

            # ✅ build email: firstname.lastname{ext}@...
            first_part = _mail_part(first_name)
            last_part  = _mail_part(last_name)
            ext_part   = _mail_part(extension)  # "JR" / "JR." -> "jr"; "II" -> "ii"
            local = f"{first_part}.{last_part}{ext_part}"
            email = f"{local}@gsfe.tupcavite.edu.ph"

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

@role_required(['admin', 'staff'])
def admin_student_view(request):
    q = (request.GET.get('q') or '').strip()

    qs = Student.objects.all()
    if q:
        qs = qs.filter(
            Q(tupc_id__icontains=q) |
            Q(program__icontains=q) |
            Q(last_name__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_initial__icontains=q) |
            Q(extension__icontains=q) |
            Q(email__icontains=q)
        )

    qs = qs.order_by(Lower('last_name'), Lower('first_name'))

    paginator = Paginator(qs, 50) 
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'myapp/admin_student.html', {
        'students': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'q': q,
    })
    
#---------Admin Manage Accounts----------------------#
OTP_TTL_MINUTES = 10  

def json_ok(message="ok", **extra):
    payload = {"status": "ok", "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=200)

def json_err(message, *, code="ERROR", status=400, **extra):
    payload = {"status": "error", "code": code, "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)

def safe_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON payload.")

def gen_otp():
    # 6-digit numeric, cryptographically secure
    return "".join(secrets.choice("0123456789") for _ in range(6))

def _expired(dt):
    return dt < timezone.now() - timedelta(minutes=OTP_TTL_MINUTES)

def _throttle_key(email, purpose):
    return f"otp:throttle:{purpose}:{email}"

def _db_too_soon(email: str, seconds: int = 60):
    """
    Fallback throttle using OTPVerification.created_at if cache is unavailable.
    Returns (True, remaining_seconds) if inside cooldown window; else (False, 0).
    """
    try:
        rec = OTPVerification.objects.get(email=email)
    except OTPVerification.DoesNotExist:
        return False, 0
    elapsed = (timezone.now() - rec.created_at).total_seconds()
    remaining = max(0, seconds - int(elapsed))
    return (elapsed < seconds), remaining

def _throttle(email: str, purpose: str, seconds: int = 60):
    """
    Preferred throttle using atomic cache.add (works with LocMem or Redis).
    Falls back to DB-based timing if cache backend errors out.
    Returns (should_throttle: bool, remaining_seconds: int|None)
    """
    key = _throttle_key(email, purpose)
    try:
        created = cache.add(key, "1", timeout=seconds)  # atomic: True if newly set
        if created:
            return False, seconds
        # Key already exists → within window. Many backends don't expose TTL; return None for remaining.
        return True, None
    except Exception:
        # Cache misconfigured or unavailable → fallback to DB window
        return _db_too_soon(email, seconds=seconds)

@role_required(['admin'])
def admin_accounts_view(request):
    # Ensure your template path matches this
    return render(request, 'myapp/admin_accounts.html')

@require_http_methods(["GET"])
@csrf_protect
def get_accounts_data(request):
    active = list(
        UserAccount.objects.filter(is_active=True)
        .values("full_name", "email", "role")
    )
    deactivated = list(
        Archived_Account.objects.all()
        .values("full_name", "email", "role")
    )
    return JsonResponse({"active": active, "deactivated": deactivated}, status=200)

@require_http_methods(["POST"])
@csrf_protect
def deactivate_account(request, user_email):
    account = get_object_or_404(UserAccount, email=user_email)
    try:
        with transaction.atomic():
            Archived_Account.objects.update_or_create(
                email=account.email,
                defaults={
                    "full_name": account.full_name,
                    "password": account.password,
                    "role": account.role,
                    "is_active": False,
                }
            )
            account.delete()
    except Exception:
        return json_err("Failed to deactivate the account.", code="DEACTIVATE_FAIL", status=500)

    messages.success(request, f"{account.full_name} ({account.email}) has been deactivated.")
    return json_ok("Deactivated.")

@require_http_methods(["PATCH", "POST"])
@csrf_protect
def edit_account(request, user_email: str):
    account = get_object_or_404(UserAccount, email=user_email)
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    full_name = (body.get("full_name") or "").strip()
    role = body.get("role", None)

    errors = {}
    if not full_name:
        errors["full_name"] = "Full name is required."
    elif len(full_name) > 128:
        errors["full_name"] = "Full name must be at most 128 characters."
    if role is not None and role not in {c[0] for c in UserAccount.ROLE_CHOICES}:
        errors["role"] = "Invalid role."
    if errors:
        return json_err("Validation failed.", code="VALIDATION", errors=errors)

    try:
        with transaction.atomic():
            account.full_name = full_name
            if role is not None:
                account.role = role
            account.save(update_fields=["full_name"] + (["role"] if role is not None else []))
    except Exception:
        return json_err("Unable to update the account.", code="UPDATE_FAIL", status=500)

    return json_ok(
        "Account updated successfully.",
        account={"full_name": account.full_name, "email": account.email, "role": account.role}
    )

@require_http_methods(["POST"])
@csrf_protect
def password_otp_request(request):
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    email = (body.get("email") or "").strip().lower()
    if not email:
        return json_err("Email is required.", code="MISSING_FIELDS")

    account = get_object_or_404(UserAccount, email=email)

    # Throttle using cache.add with DB fallback
    should_throttle, remaining = _throttle(email, "password", seconds=60)
    if should_throttle:
        msg = "Please wait before requesting another OTP."
        if remaining:  # only shown when we know the seconds
            msg = f"Please wait {remaining}s before requesting another OTP."
        return json_err(msg, code="RATE_LIMIT", status=429)

    otp = gen_otp()
    try:
        obj, created = OTPVerification.objects.get_or_create(
            email=email,
            defaults={
                "otp": otp,
                "full_name": account.full_name,
                "role": account.role,
                "password": account.password,
                "is_active": False,
                "created_at": timezone.now(),
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
    except Exception:
        return json_err("Unable to persist OTP.", code="OTP_WRITE_FAIL", status=500)

    try:
        send_mail(
            subject="Your OTP for Password Change",
            message=f"Your verification code is: {otp}\nIt expires in {OTP_TTL_MINUTES} minutes.",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )
    except (BadHeaderError, Exception):
        if getattr(settings, "DEBUG", False):
            return json_ok("OTP generated (DEBUG).", dev_otp=otp)
        return json_err("Failed to send OTP.", code="EMAIL_SEND_FAIL", status=502)

    return json_ok("OTP sent to registered email.")

@require_http_methods(["POST"])
@csrf_protect
def password_otp_verify(request):
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    email = (body.get("email") or "").strip().lower()
    otp   = (body.get("otp") or "").strip()
    if not email or not otp:
        return json_err("Email and OTP are required.", code="MISSING_FIELDS")

    try:
        rec = OTPVerification.objects.get(email=email)
    except OTPVerification.DoesNotExist:
        return json_err("No OTP request found for that email.", code="OTP_NOT_FOUND", status=404)

    if _expired(rec.created_at):
        return json_err("OTP expired. Please request a new one.", code="OTP_EXPIRED")
    if rec.otp != otp:
        return json_err("Invalid OTP.", code="OTP_INCORRECT")

    rec.is_active = True
    rec.save(update_fields=["is_active"])
    return json_ok("OTP verified.")

@require_http_methods(["POST"])
@csrf_protect
def change_password(request, email: str):
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    new_password = (body.get("new_password") or "").strip()
    if len(new_password) < 8:
        return json_err("Password must be at least 8 characters.", code="VALIDATION")

    account = get_object_or_404(UserAccount, email=email)

    try:
        rec = OTPVerification.objects.get(email=email)
    except OTPVerification.DoesNotExist:
        return json_err("Please request and verify an OTP before changing password.", code="OTP_NOT_FOUND")

    if _expired(rec.created_at):
        return json_err("OTP expired. Please request a new one.", code="OTP_EXPIRED")
    if not rec.is_active:
        return json_err("OTP not verified yet.", code="OTP_NOT_VERIFIED")

    try:
        with transaction.atomic():
            account.password = make_password(new_password)
            account.must_change_password = True
            account.save(update_fields=["password"])
            rec.delete()  # consume OTP once used
    except Exception:
        return json_err("Unable to change password right now.", code="UPDATE_FAIL", status=500)

    return json_ok("Password changed successfully.")

@require_http_methods(["POST"])
@csrf_protect
def request_otp(request):
    try:
        data = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    required = ["fullName", "email", "position", "password"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return json_err(f"Missing: {', '.join(missing)}", code="MISSING_FIELDS")

    full_name = data["fullName"].strip()
    email = data["email"].strip().lower()
    position = data["position"].strip()
    password = data["password"]

    errors = []
    if not (3 <= len(full_name) <= 128): errors.append("Full name must be 3–128 characters.")
    if not (5 <= len(email) <= 254): errors.append("Email must be 5–254 characters.")
    if not (3 <= len(position) <= 64): errors.append("Position must be 3–64 characters.")
    if not (8 <= len(password) <= 128): errors.append("Password must be 8–128 characters.")
    try:
        validate_email(email)
    except Exception:
        errors.append("Invalid email format.")
    if errors:
        return json_err("Validation failed.", code="VALIDATION", errors=errors)

    if UserAccount.objects.filter(email=email).exists() or Archived_Account.objects.filter(email=email).exists():
        return json_err("This email is already registered.", code="EMAIL_TAKEN", status=409)

    # Throttle using cache.add with DB fallback
    should_throttle, remaining = _throttle(email, "create_account", seconds=60)
    if should_throttle:
        msg = "Please wait before requesting another OTP."
        if remaining:
            msg = f"Please wait {remaining}s before requesting another OTP."
        return json_err(msg, code="RATE_LIMIT", status=429)

    otp = gen_otp()
    try:
        OTPVerification.objects.update_or_create(
            email=email,
            defaults={
                "otp": otp,
                "full_name": full_name,
                "role": position,
                "password": make_password(password),
                "created_at": timezone.now(),
                "is_active": False,
            }
        )
    except Exception:
        return json_err("Unable to persist OTP.", code="OTP_WRITE_FAIL", status=500)

    try:
        send_mail(
            subject='Your TUPC OSA OTP Code',
            message=f'Your One-Time Password is: {otp}\nThis OTP expires in {OTP_TTL_MINUTES} minutes.',
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )
    except (BadHeaderError, Exception):
        if getattr(settings, "DEBUG", False):
            return json_ok("OTP generated (DEBUG).", dev_otp=otp)
        return json_err("Failed to send OTP email.", code="EMAIL_SEND_FAIL", status=502)

    return json_ok("OTP sent.")

@require_http_methods(["POST"])
@csrf_protect
def verify_otp(request):
    try:
        data = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    email = (data.get("email") or "").strip().lower()
    otp_input = (data.get("otp") or "").strip()

    if not email or not otp_input:
        return json_err("Email and OTP are required.", code="MISSING_FIELDS")

    try:
        rec = OTPVerification.objects.get(email=email)
    except OTPVerification.DoesNotExist:
        return json_err("No OTP record found for this email.", code="OTP_NOT_FOUND", status=404)

    if _expired(rec.created_at):
        return json_err("OTP expired. Please request a new one.", code="OTP_EXPIRED")

    if rec.otp.strip() != otp_input:
        return json_err("Incorrect OTP.", code="OTP_INCORRECT")

    try:
        with transaction.atomic():
            UserAccount.objects.create(
                full_name=rec.full_name,
                email=rec.email,
                role=rec.role,
                password=rec.password,  
                is_active=True,
                must_change_password=True,
            )
            rec.delete()
    except IntegrityError:
        return json_err("Account already exists.", code="EMAIL_TAKEN", status=409)
    except Exception:
        return json_err("Could not create account.", code="CREATE_FAIL", status=500)

    return json_ok("Account successfully created!")

@require_http_methods(["POST"])
@csrf_protect
def email_change_request(request):
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    current_email = (body.get("current_email") or "").strip().lower()
    new_email     = (body.get("new_email") or "").strip().lower()

    if not current_email or not new_email:
        return json_err("Both current_email and new_email are required.", code="MISSING_FIELDS")
    if current_email == new_email:
        return json_err("New email must be different from current email.", code="SAME_EMAIL")

    account = get_object_or_404(UserAccount, email=current_email)

    if UserAccount.objects.filter(email=new_email).exists():
        return json_err("That email is already in use.", code="EMAIL_TAKEN", status=409)

    otp = gen_otp()
    try:
        obj, created = OTPVerification.objects.get_or_create(
            email=new_email,
            defaults={
                "otp": otp,
                "full_name": account.full_name,
                "role": account.role,
                "password": account.password,
                "is_active": False,
                "created_at": timezone.now(),
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
    except Exception:
        return json_err("Unable to persist OTP.", code="OTP_WRITE_FAIL", status=500)

    try:
        send_mail(
            subject="Email Change OTP",
            message=f"Your verification code is: {otp}\nIt expires in {OTP_TTL_MINUTES} minutes.",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[new_email],
            fail_silently=False,
        )
    except (BadHeaderError, Exception):
        if getattr(settings, "DEBUG", False):
            return json_ok("OTP generated (DEBUG).", dev_otp=otp)
        return json_err("Failed to send OTP.", code="EMAIL_SEND_FAIL", status=502)

    return json_ok("OTP sent to new email.")

@require_http_methods(["POST"])
@csrf_protect
def email_change_verify(request):
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    new_email = (body.get("new_email") or "").strip().lower()
    otp       = (body.get("otp") or "").strip()
    if not new_email or not otp:
        return json_err("new_email and otp are required.", code="MISSING_FIELDS")

    try:
        rec = OTPVerification.objects.get(email=new_email)
    except OTPVerification.DoesNotExist:
        return json_err("No OTP request found for that email.", code="OTP_NOT_FOUND", status=404)
    if _expired(rec.created_at):
        return json_err("OTP expired. Please request a new one.", code="OTP_EXPIRED")
    if rec.otp != otp:
        return json_err("Invalid OTP.", code="OTP_INCORRECT")

    rec.is_active = True
    rec.save(update_fields=["is_active"])
    return json_ok("OTP verified.")

@require_http_methods(["POST"])
@csrf_protect
def email_change_apply(request):
    try:
        body = safe_body(request)
    except ValueError as e:
        return json_err(str(e), code="BAD_JSON")

    current_email = (body.get("current_email") or "").strip().lower()
    new_email     = (body.get("new_email") or "").strip().lower()
    if not current_email or not new_email:
        return json_err("Both current_email and new_email are required.", code="MISSING_FIELDS")

    account = get_object_or_404(UserAccount, email=current_email)
    try:
        rec = OTPVerification.objects.get(email=new_email)
    except OTPVerification.DoesNotExist:
        return json_err("No OTP verification found for that email.", code="OTP_NOT_FOUND", status=404)

    if _expired(rec.created_at):
        return json_err("OTP expired. Please request a new one.", code="OTP_EXPIRED")
    if not rec.is_active:
        return json_err("OTP not verified yet.", code="OTP_NOT_VERIFIED")
    if UserAccount.objects.filter(email=new_email).exclude(pk=account.pk).exists():
        return json_err("That email is already in use.", code="EMAIL_TAKEN", status=409)

    try:
        with transaction.atomic():
            account.email = new_email
            account.save(update_fields=["email"])
            rec.delete()
    except Exception:
        return json_err("Failed to update email.", code="UPDATE_FAIL", status=500)

    return json_ok("Email updated successfully.", email=new_email)

#-------------------------------------------------#

#---------------Manage Reports--------------------#

@role_required(['admin'])
def admin_report_view(request):
    from django.utils import timezone
    server_today = timezone.localdate()  # server-side date (no client clock)
    return render(
        request,
        'myapp/admin_report.html',
        {'SERVER_TODAY': server_today.strftime('%Y-%m-%d')}
    )
    
PH_LONG_LANDSCAPE = landscape((8.5 * inch, 13 * inch))

styles = getSampleStyleSheet()
STYLE_TITLE = styles['Title']
STYLE_HEAD  = ParagraphStyle('Head', parent=styles['Heading5'], textColor=colors.whitesmoke)
STYLE_CELL  = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10)

def _full_name(first, middle, last, ext):
    parts = [(first or "").strip()]
    if (middle or "").strip():
        parts.append(middle.strip())
    parts.append((last or "").strip())
    if (ext or "").strip():
        parts.append(ext.strip())
    return " ".join([p for p in parts if p])

def _fmt_date(d):
    if not d:
        return ""
    if hasattr(d, "date"):  # datetime
        d = timezone.localtime(d).date()
    return d.strftime("%m/%d/%Y")

def _header_footer_factory(pdf_title: str):

    def _header_footer(canvas: Canvas, doc):
        pass

    return _header_footer

def _start_doc(response, title_text):
    doc = BaseDocTemplate(
        response, pagesize=PH_LONG_LANDSCAPE,
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')
    doc.addPageTemplates([PageTemplate(id='normal', frames=[frame],
                                       onPage=_header_footer_factory(title_text))])
    elements = [Paragraph(title_text, STYLE_TITLE), Spacer(1, 8)]
    return doc, elements

def _table(rows, col_widths):
    cardinal_red = colors.HexColor("#8C1515")
    light_gray   = colors.HexColor("#F2F2F2")
    mid_gray     = colors.HexColor("#E6E6E6")

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0,0), (-1,0), cardinal_red),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,0),10),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.black),
    ]
    for i in range(1, len(rows)):
        cmds.append(('BACKGROUND', (0,i), (-1,i), light_gray if i % 2 else mid_gray))
    tbl.setStyle(TableStyle(cmds))
    return tbl

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _date_range(qs, field_name, start_date, end_date):
    """
    Inclusive date range:
      - DateField:     [start_date .. end_date]
      - DateTimeField: [start_date 00:00:00 .. end_date 23:59:59.999999] in server TZ
    If only one bound is provided, it becomes a single-day range.
    """
    start = _parse_date(start_date)
    end   = _parse_date(end_date)

    if start and not end: end = start
    if end and not start: start = end
    if not (start and end):
        return qs  # nothing to filter

    field = qs.model._meta.get_field(field_name)

    if isinstance(field, DateTimeField):
        tz = timezone.get_default_timezone()
        start_dt = timezone.make_aware(datetime.combine(start, time.min), tz)
        end_dt   = timezone.make_aware(datetime.combine(end,   time.max), tz)
        return qs.filter(**{f"{field_name}__range": (start_dt, end_dt)})
    elif isinstance(field, DateField):
        return qs.filter(**{f"{field_name}__range": (start, end)})
    else:
        return qs

@role_required(['admin'])
def admin_violation_report_pdf(request):
    start_date = request.GET.get('start_date', '').strip()
    end_date   = request.GET.get('end_date', '').strip()
    vtype      = request.GET.get('violation_type', '').strip()
    status     = request.GET.get('status', '').strip()
    severity   = request.GET.get('severity', '').strip()

    qs = Violation.objects.all().order_by('violation_date', 'violation_time')
    if vtype:    qs = qs.filter(violation_type=vtype)
    if status:   qs = qs.filter(status=status)
    if severity: qs = qs.filter(severity=severity)
    qs = _date_range(qs, 'violation_date', start_date, end_date)

    resp = HttpResponse(content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="violation_report.pdf"'
    doc, elements = _start_doc(resp, f"VIOLATION REPORT FROM {start_date or '—'} TO {end_date or '—'}")

    headers = ['DATE (MM/DD/YYYY)', 'NAME', 'STUDENT ID', 'PROGRAM', 'SEVERITY', 'VIOLATION TYPE', 'STATUS']
    colw = [doc.width*0.12, doc.width*0.26, doc.width*0.14, doc.width*0.18, doc.width*0.08, doc.width*0.14, doc.width*0.08]
    rows = [[Paragraph(h, STYLE_HEAD) for h in headers]]

    for v in qs:
        name = _full_name(v.first_name, v.middle_initial, v.last_name, v.extension_name)
        rows.append([
            Paragraph(_fmt_date(v.violation_date), STYLE_CELL),
            Paragraph(name, STYLE_CELL),
            Paragraph(v.student_id, STYLE_CELL),
            Paragraph(v.program_course, STYLE_CELL),
            Paragraph(v.severity.title(), STYLE_CELL),
            Paragraph(dict(Violation.VIOLATION_TYPES).get(v.violation_type, v.violation_type), STYLE_CELL),
            Paragraph(v.status, STYLE_CELL),
        ])

    if len(rows) == 1:
        rows.append([Paragraph('No data', STYLE_CELL)] * len(headers))

    elements.append(_table(rows, colw))
    doc.build(elements)
    return resp

@role_required(['admin'])
def admin_good_moral_report_pdf(request):
    start_date = request.GET.get('start_date', '').strip()
    end_date   = request.GET.get('end_date', '').strip()
    status     = request.GET.get('status', '').strip()

    qs = GoodMoralRequest.objects.all().order_by('submitted_at')
    if status:
        qs = qs.filter(status=status)
    qs = _date_range(qs, 'submitted_at', start_date, end_date)

    resp = HttpResponse(content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="good_moral_report.pdf"'
    doc, elements = _start_doc(resp, f"GOOD MORAL REPORT FROM {start_date or '—'} TO {end_date or '—'}")

    headers = ['DATE (MM/DD/YYYY)', 'NAME', 'SEX', 'STUDENT ID', 'PROGRAM', 'PURPOSE', 'STATUS']
    colw = [doc.width*0.12, doc.width*0.28, doc.width*0.06, doc.width*0.14, doc.width*0.16, doc.width*0.14, doc.width*0.10]
    rows = [[Paragraph(h, STYLE_HEAD) for h in headers]]

    for r in qs:
        name = _full_name(r.first_name, r.middle_name, r.surname, r.ext)
        rows.append([
            Paragraph(_fmt_date(r.submitted_at), STYLE_CELL),
            Paragraph(name, STYLE_CELL),
            Paragraph(r.sex or "", STYLE_CELL),
            Paragraph(r.student_id, STYLE_CELL),
            Paragraph(r.program, STYLE_CELL),
            Paragraph(r.purpose, STYLE_CELL),
            Paragraph(r.status, STYLE_CELL),
        ])

    if len(rows) == 1:
        rows.append([Paragraph('No data', STYLE_CELL)] * len(headers))

    elements.append(_table(rows, colw))
    doc.build(elements)
    return resp

@role_required(['admin'])
def admin_surrender_id_report_pdf(request):
    start_date = request.GET.get('start_date', '').strip()
    end_date   = request.GET.get('end_date', '').strip()
    reason     = request.GET.get('reason', '').strip()

    qs = IDSurrenderRequest.objects.all().order_by('submitted_at')
    if reason:
        qs = qs.filter(reason=reason)
    qs = _date_range(qs, 'submitted_at', start_date, end_date)

    resp = HttpResponse(content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="surrender_id_report.pdf"'
    doc, elements = _start_doc(resp, f"SURRENDER ID REQUEST REPORT FROM {start_date or '—'} TO {end_date or '—'}")

    headers = ['DATE (MM/DD/YYYY)', 'NAME', 'STUDENT ID', 'PROGRAM', 'REASON']
    colw = [doc.width*0.14, doc.width*0.34, doc.width*0.18, doc.width*0.20, doc.width*0.14]
    rows = [[Paragraph(h, STYLE_HEAD) for h in headers]]

    for r in qs:
        name = _full_name(r.first_name, r.middle_name, r.surname, r.extension)
        rows.append([
            Paragraph(_fmt_date(r.submitted_at), STYLE_CELL),
            Paragraph(name, STYLE_CELL),
            Paragraph(r.student_number, STYLE_CELL),
            Paragraph(r.program, STYLE_CELL),
            Paragraph(r.reason, STYLE_CELL),
        ])

    if len(rows) == 1:
        rows.append([Paragraph('No data', STYLE_CELL)] * len(headers))

    elements.append(_table(rows, colw))
    doc.build(elements)
    return resp

@role_required(['admin'])
def admin_clearance_report_pdf(request):
    start_date  = request.GET.get('start_date', '').strip()
    end_date    = request.GET.get('end_date', '').strip()
    stakeholder = request.GET.get('stakeholder', '').strip()
    client_type = request.GET.get('client_type', '').strip()

    qs = ClearanceRequest.objects.all().order_by('created_at')
    if stakeholder: qs = qs.filter(stakeholder=stakeholder)
    if client_type: qs = qs.filter(client_type=client_type)
    qs = _date_range(qs, 'created_at', start_date, end_date)

    resp = HttpResponse(content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="clearance_request_report.pdf"'
    doc, elements = _start_doc(resp, f"CLEARANCE REQUEST REPORT FROM {start_date or '—'} TO {end_date or '—'}")

    headers = ['DATE (MM/DD/YYYY)', 'NAME', 'STUDENT ID', 'PROGRAM',
            'CLIENT TYPE', 'STAKEHOLDER', 'REASON']

    # sums to 1.00
    colw = [
        doc.width * 0.12,  # DATE
        doc.width * 0.28,  # NAME
        doc.width * 0.16,  # STUDENT ID
        doc.width * 0.16,  # PROGRAM
        doc.width * 0.10,  # CLIENT TYPE
        doc.width * 0.12,  # STAKEHOLDER
        doc.width * 0.06,  # REASON
    ]
    rows = [[Paragraph(h, STYLE_HEAD) for h in headers]]

    for r in qs:
        name = _full_name(r.first_name, r.middle_name, r.last_name, r.extension)
        rows.append([
            Paragraph(_fmt_date(r.created_at), STYLE_CELL),
            Paragraph(name, STYLE_CELL),
            Paragraph(r.student_number, STYLE_CELL),
            Paragraph(r.program, STYLE_CELL),
            Paragraph(r.client_type, STYLE_CELL),
            Paragraph(r.stakeholder, STYLE_CELL),
            Paragraph(r.purpose, STYLE_CELL),  # mapped to "REASON"
        ])

    if len(rows) == 1:
        rows.append([Paragraph('No data', STYLE_CELL)] * len(headers))

    elements.append(_table(rows, colw))
    doc.build(elements)
    return resp

#-------------------------------------------------#

#----------------Posting--------------------------#

@role_required(['admin', 'staff', 'studasst'])
def ajax_delete_lostandfound(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(LostAndFound, id=item_id)
        item.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@role_required(['admin', 'staff', 'studasst'])
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

@role_required(['admin', 'staff', 'scholarship'])
def ajax_delete_scholarship(request, id):
    if request.method == 'POST':
        s = get_object_or_404(Scholarship, id=id)
        s.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@role_required(['admin', 'staff', 'scholarship'])
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

#--------------------------------------------------#

#------------clearance-----------------------------#

@role_required(['admin', 'staff', 'studasst'])
def admin_clearance(request):
    q = (request.GET.get("q") or "").strip()

    records = ClearanceRequest.objects.all().order_by('-created_at')
    if q:
        records = records.filter(
            Q(student_number__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(program__icontains=q)
        )

    return render(request, 'myapp/admin_clearance.html', {
        'records': records,
        'total': records.count(),
        'q': q,
    })

@role_required(['admin', 'staff', 'studasst'])
def admin_view_clearance_view(request, pk):
    obj = get_object_or_404(ClearanceRequest, pk=pk)
    return render(request, 'myapp/admin_view_clearance.html', {'obj': obj})



#--------------------------------------------#

#-----------Good Moral Page------------------#

@role_required(['admin', 'staff', 'studasst'])
def admin_goodmoral_view(request):
    q = (request.GET.get("q") or "").strip()

    pending_qs = GoodMoralRequest.objects.filter(
        is_approved=False, is_rejected=False
    ).order_by('-submitted_at')

    if q:
        from django.db.models import Q
        pending_qs = pending_qs.filter(
            Q(surname__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_name__icontains=q) |
            Q(student_id__icontains=q)
        )

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
            'q': q,
        }
    )

@role_required(['admin', 'staff', 'studasst'])
def admin_view_goodmoral(request, pk):
    r = get_object_or_404(GoodMoralRequest, pk=pk)
    return render(request, 'myapp/admin_view_goodmoral.html', {'r': r})

DEFAULT_APPROVAL_MSG = (
    "Your Good Moral Certificate request has been approved.\n\n"
    "Please proceed to the Office of Student Affairs (OSA) to claim your request form.\n"
    "Prepare PHP 100 for payment at the cashier's office.\n"
    "After payment, reply to this email with a photo or copy of your receipt."
)

@role_required(['admin', 'staff', 'studasst'])
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

@role_required(['admin', 'staff', 'studasst'])
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

@role_required(['admin', 'staff', 'studasst'])
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

@role_required(['admin', 'staff', 'studasst'])
@xframe_options_exempt
def batch_view_gmrf(request):
    """
    Batch preview for *REQUEST FORMS* (not certificates).

    Usage (index-like range, 1-based):
      /gmrf/batch-preview?frm=1&to=50
        -> Includes Accepted + Pending (excludes Rejected)

    Optional:
      &status=accepted|pending|all    (default: all=accepted+pending; rejected always excluded)
      &guide=1                        (draws position guides for debugging)

    Sorting matches your certs batch for predictable pagination.
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

    status = (request.GET.get("status") or "all").strip().lower()
    guide  = (request.GET.get("guide") == "1")

    # Base filter: exclude rejected -> accepted + pending
    q = Q(is_rejected=False)
    if status == "accepted":
        q &= Q(is_approved=True)
    elif status == "pending":
        q &= Q(is_approved=False)
    # else: 'all' keeps accepted+pending

    qs = (GoodMoralRequest.objects
          .filter(q)
          .order_by('submitted_at', 'pk'))

    start = frm - 1
    end   = to
    rows = list(qs[start:end])
    if not rows:
        return HttpResponseBadRequest("No requests in that range (after filtering).")

    # ---- inline form renderer (copied from your single-form logic, returns bytes) ----
    def _render_form_pdf_bytes(r):
        from django.utils import timezone

        template_path = finders.find('myapp/form/GMC-request-template.pdf')
        if not template_path:
            raise FileNotFoundError("Template PDF not found.")

        with open(template_path, 'rb') as f:
            base_pdf_bytes = f.read()
        base_reader = PdfReader(BytesIO(base_pdf_bytes))
        base_page = base_reader.pages[0]
        llx, lly, urx, ury = map(float, base_page.mediabox)
        width, height = urx - llx, ury - lly

        overlay_buf = BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(width, height))

        # helpers
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

        if guide:
            draw_guides()

        # TOP ROW: NO. and DATE
        req_no = f"{r.pk:06d}"
        text(70, height - 135, req_no, bold=True, size=12)
        date_requested = timezone.localdate(r.submitted_at).strftime('%m/%d/%Y')
        text(width - 180, height - 135, date_requested, bold=True, size=12, right=True)

        # PLACE FIELDS
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
            check(320, 660)
        elif sex.startswith("f"):
            check(375, 660)

        # Program (wrapped)
        styles = getSampleStyleSheet()
        styleN = styles["Normal"]; styleN.fontSize = 8; styleN.leading = 8
        prog_para = Paragraph(r.program or "", styleN)
        prog_para.wrapOn(c, 280, 100)
        prog_para.drawOn(c, 45, 610)

        # Status
        status_val = (r.status or "").lower()
        if "alum" in status_val or "gradu" in status_val:
            check(60, 580)
            if r.date_graduated:
                text(160, 565, r.date_graduated.strftime('%Y'))
        elif "former" in status_val:
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
            check(330, 610);  (other and text(360, 595, other, size=8))
        elif "continu" in purpose or "continuing education" in purpose:
            check(330, 583)
        elif "employment" in purpose:
            check(330, 555)
        elif "scholar" in purpose:
            check(330, 530);  (other and text(360, 515, other))
        elif any(k in purpose for k in ("sit","supervised industrial training","ipt",
                                        "in-campus practice teaching","opt","off-campus practice teaching")):
            check(330, 500)
        elif any(k in purpose for k in ("student development","comselec","usg","award")):
            check(330, 460)
        else:
            check(330, 420); text(420, 420, other or purpose_raw)

        # Requester info
        text(85, 345, r.requester_name)
        text(415, 345, r.requester_contact)
        text(205, 330, r.relationship)

        c.showPage()
        c.save()
        overlay_buf.seek(0)

        overlay_reader = PdfReader(overlay_buf)
        writer = PdfWriter()
        page = base_reader.pages[0]
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

        out = BytesIO()
        writer.write(out)
        out.seek(0)
        return out.getvalue()
    # ---- end inline renderer ----

    merger = PdfMerger(strict=False)
    added = 0
    for req in rows:
        try:
            pdf_bytes = _render_form_pdf_bytes(req)
            merger.append(BytesIO(pdf_bytes))
            added += 1
        except Exception:
            # Skip bad rows silently; log if desired
            continue

    if added == 0:
        return HttpResponseBadRequest("All rows failed to render.")

    out = BytesIO()
    merger.write(out); merger.close(); out.seek(0)

    resp = HttpResponse(out.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="GMRF_batch_{frm}-{to}_{status}.pdf"'
    resp["Content-Length"] = str(len(out.getvalue()))
    return resp

@role_required(['admin', 'staff', 'studasst'])
@xframe_options_exempt
def view_gmf(request, pk):
    req = get_object_or_404(GoodMoralRequest, pk=pk)
    pdf_bytes = generate_gmf_pdf(req)  # now returns bytes
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="GMF_{req.student_id or req.pk}.pdf"'
    resp["Content-Length"] = str(len(pdf_bytes))
    return resp

@role_required(['admin', 'staff', 'studasst'])
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
    qs = (GoodMoralRequest.objects
          .filter(is_rejected=False)
          .order_by('submitted_at', 'pk'))  

    start = frm - 1
    end   = to
    rows = list(qs[start:end])
    if not rows:
        return HttpResponseBadRequest("No requests in that range (after filtering).")

    merger = PdfMerger(strict=False)
    for req in rows:
        try:
            pdf_bytes = generate_gmf_pdf(req) 
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

#--------------------------------------------------#

#------------Acknowledgement Receipt---------------#

@role_required(['admin', 'staff', 'studasst'])
def admin_ackreq_view(request):  
    q = (request.GET.get("q") or "").strip()
    pending_requests = IDSurrenderRequest.objects.filter(
        status=IDSurrenderRequest.STATUS_PENDING
    ).order_by('-submitted_at')

    if q:
        pending_requests = pending_requests.filter(
            Q(surname__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_name__icontains=q) |
            Q(student_number__icontains=q) 
        )

    history_requests = IDSurrenderRequest.objects.filter(
        status__in=[IDSurrenderRequest.STATUS_APPROVED, IDSurrenderRequest.STATUS_DECLINED]
    ).order_by('-submitted_at')

    context = {
        "pending_requests": pending_requests,
        "history_requests": history_requests,
        "pending_count": pending_requests.count(),
        "history_count": history_requests.count(),
        "STATUS_APPROVED": IDSurrenderRequest.STATUS_APPROVED,
        "STATUS_DECLINED": IDSurrenderRequest.STATUS_DECLINED,
        "q": q,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, "myapp/admin_ackreq.html", context)
    return render(request, "myapp/admin_ackreq.html", context)

@role_required(['admin', 'staff', 'studasst'])
def admin_ackreq_receipt_pdf(request, pk):
    req = get_object_or_404(IDSurrenderRequest, pk=pk)
    admin_acc = UserAccount.objects.filter(role='admin', is_active=True).order_by('-created_at').first()
    admin_name_upper = (admin_acc.full_name if admin_acc else "ADMIN").upper()

    try:
        pdf_path = build_ack_pdf(req, admin_name_upper)
    except Exception as e:
        raise Http404(f"PDF generation failed: {e}")

    filename = os.path.basename(pdf_path)
    resp = FileResponse(open(pdf_path, "rb"), content_type=mimetypes.types_map.get(".pdf", "application/pdf"))
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp

@role_required(['admin', 'staff', 'studasst'])
@xframe_options_exempt
def batch_view_ackreq_receipts(request):
    """
    Batch preview for Acknowledgement Receipt PDFs (ID Surrender).
    Uses your existing build_ack_pdf(req, admin_name_upper).

    Usage:
      /ackreq/batch-preview?frm=1&to=50
    Notes:
      - Range is 1-based index over the filtered/sorted queryset.
      - Streams a single merged PDF inline.
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

    admin_acc = UserAccount.objects.filter(role='admin', is_active=True).order_by('-created_at').first()
    admin_name_upper = (admin_acc.full_name if admin_acc else "ADMIN").upper()
    qs = IDSurrenderRequest.objects.order_by('pk')

    start = frm - 1
    end   = to
    rows = list(qs[start:end])
    if not rows:
        return HttpResponseBadRequest("No requests in that range.")

    MAX_ROWS = 300
    if len(rows) > MAX_ROWS:
        return HttpResponseBadRequest(f"Too many rows ({len(rows)}). Limit is {MAX_ROWS} per batch.")

    merger = PdfMerger(strict=False)
    added = 0
    for req in rows:
        try:
            # Reuse your existing generator which returns a file path
            pdf_path = build_ack_pdf(req, admin_name_upper)
            # Append by file path (PyPDF2 will open/close internally)
            merger.append(pdf_path)
            added += 1
        except Exception:
            # Skip row on any error; optionally log
            continue

    if added == 0:
        return HttpResponseBadRequest("All rows failed to render.")

    out = BytesIO()
    merger.write(out)
    merger.close()
    out.seek(0)

    resp = HttpResponse(out.getvalue(), content_type=mimetypes.types_map.get(".pdf", "application/pdf"))
    resp["Content-Disposition"] = f'inline; filename="ACKREQ_batch_{frm}-{to}.pdf"'
    resp["Content-Length"] = str(len(out.getvalue()))
    return resp

def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'

@role_required(['admin', 'staff', 'studasst'])
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

@role_required(['admin', 'staff', 'studasst'])
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

#-------------------------------------#

#---------------violation-------------#

@role_required(['admin', 'staff'])
def admin_view_violation(request):
    violation_id = request.GET.get('violation_id')
    if not violation_id:
        messages.error(request, "No violation ID specified.")
        return redirect('myapp/admin_violation.html')

    violation = get_object_or_404(Violation, id=violation_id)
    student   = get_object_or_404(Student, tupc_id=violation.student_id)
    approved_violations = (
        Violation.objects
        .filter(student_id=student.tupc_id, status='Approved')
        .order_by('-violation_date','-created_at')
        .defer('evidence_1','evidence_2')  
    )
    pending_violations = (
        Violation.objects
        .filter(student_id=student.tupc_id, status='Pending')
        .order_by('-violation_date','-created_at')
        .defer('evidence_1','evidence_2')
    )

    total_violations = approved_violations.count() 

    return render(request, 'myapp/admin_view_violation.html', {
        'violation': violation,
        'student': student,
        'total_violations': total_violations,
        'approved_violations': approved_violations,
        'pending_violations': pending_violations,
    })

def admin_violation_view(request):
    open_major_modal = False
    form_debug = None

    if request.method == "POST":
        add_form = AddViolationForm(request.POST, request.FILES)

        try:
            if add_form.is_valid():
                approver = getattr(request.user, "get_full_name", lambda: "")() or request.user.username

                with transaction.atomic():
                    violation = add_form.save(approved_by_user=approver)

                    # MAJOR → SDT Settlement, no CS
                    if violation.severity == "MAJOR":
                        violation.settlement_type = "SDT Settlement"
                        violation.is_settled = False
                        violation.settled_at = None
                        violation.save(update_fields=["settlement_type", "is_settled", "settled_at"])
                        hours_topup = Decimal("0")

                    # MINOR → maybe CS
                    else:
                        hours_topup = Decimal("0")
                        if (
                            violation.status == "Approved"
                            and violation.violation_type not in CS_EXEMPT_TYPES
                        ):
                            student = Student.objects.select_for_update().get(
                                tupc_id=violation.student_id
                            )
                            approved_count = (
                                Violation.objects
                                .filter(
                                    student_id=violation.student_id,
                                    status='Approved',
                                    severity='MINOR',
                                    violation_type=violation.violation_type,
                                )
                                .count()
                            )
                            hours_topup = compute_cs_topup_for_minor(
                                violation.violation_type,
                                approved_count
                            )

                            if hours_topup > 0:
                                if not hasattr(violation, "cs_adjustment"):
                                    case = CommunityServiceCase.get_or_create_open(
                                        student_id=student.tupc_id,
                                        last_name=violation.last_name or student.last_name or "",
                                        first_name=violation.first_name or student.first_name or "",
                                        program_course=(
                                            violation.program_course
                                            or getattr(student, "program_course", "")
                                            or ""
                                        ),
                                        middle_initial=(
                                            violation.middle_initial
                                            or getattr(student, "middle_initial", "")
                                            or ""
                                        ),
                                        extension_name=(
                                            violation.extension_name
                                            or getattr(student, "extension_name", "")
                                            or ""
                                        ),
                                    )
                                    case.top_up_required_hours(hours_topup)
                                    CommunityServiceAdjustment.objects.create(
                                        case=case,
                                        violation=violation,
                                        hours=hours_topup,
                                        reason=f"{approved_count} offense of {violation.violation_type}: +{hours_topup}h"
                                    )
                                else:
                                    hours_topup = Decimal("0")

                # EMAIL (no SDT number)
                student_email = build_student_email(
                    violation.first_name,
                    violation.last_name,
                    violation.extension_name,
                )
                if student_email:
                    ok, info = send_violation_notice(violation, student_email, max_history=10)
                    extra = f" Community Service +{hours_topup}h applied." if hours_topup > 0 else ""
                    if ok:
                        messages.success(request, f"Violation has been recorded. {info}.{extra}")
                    else:
                        messages.warning(request, f"Violation recorded, but email not sent: {info}{extra}")
                else:
                    extra = f" Community Service +{hours_topup}h applied." if hours_topup > 0 else ""
                    messages.warning(request, f"Violation recorded, but student email could not be constructed.{extra}")

                return redirect("admin_violation")

            else:
                open_major_modal = True
                messages.error(request, "Please correct the errors in the form.")
                if settings.DEBUG:
                    form_debug = {
                        "posted": {k: request.POST.get(k) for k in request.POST.keys()},
                        "files": {k: getattr(request.FILES.get(k), "content_type", None) for k in request.FILES.keys()},
                        "errors": json.loads(add_form.errors.as_json()),
                        "non_field_errors": add_form.non_field_errors(),
                    }
                    print("ADD_VIOLATION_DEBUG:", json.dumps(form_debug, indent=2, default=str))

        except IntegrityError:
            open_major_modal = True
            messages.error(request, "Database error while saving the violation. Please try again.")
        except Exception as e:
            open_major_modal = True
            messages.error(request, f"Unexpected error: {str(e)}")
    else:
        add_form = AddViolationForm()

    # ----- LISTS (GET + re-render invalid POST) -----
    q_pending  = (request.GET.get('q') or '').strip()
    q_history  = (request.GET.get('q_history') or '').strip()
    default_violation_date = timezone.localdate().strftime("%Y-%m-%d")
    default_violation_time = timezone.localtime().strftime("%H:%M")

    base = (Violation.objects
            .defer('evidence_1', 'evidence_2')
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

    def _toi(v, d):
        try:
            return int(v)
        except (TypeError, ValueError):
            return d

    p_page = max(1, _toi(request.GET.get('p', 1), 1))
    h_page = max(1, _toi(request.GET.get('h', 1), 1))
    per    = min(max(_toi(request.GET.get('per', 15), 15), 1), 100)

    p_pager = Paginator(pending, per)
    h_pager = Paginator(history, per)

    pending_page = p_pager.get_page(p_page)
    history_page = h_pager.get_page(h_page)

    return render(request, 'myapp/admin_violation.html', {
        'pending_violations': pending_page,
        'history_violations': history_page,
        "major_form": add_form,                   # keep existing template var name
        "open_major_modal": open_major_modal,     # controls modal re-open on errors
        "default_violation_date": default_violation_date,
        "default_violation_time": default_violation_time,
    })
     
@role_required(['admin', 'staff'])
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

    messages.error(request, f"❌ Violation for {student.first_name} {student.last_name} was lifted.")
    return redirect('admin_violation')

@role_required(['admin', 'staff'])
@transaction.atomic
def admin_approve_violation(request, violation_id):
    v = Violation.objects.select_for_update().get(id=violation_id)              # lock this violation
    student = Student.objects.select_for_update().get(tupc_id=v.student_id)     # lock per-student
    if v.status != 'Approved':
        v.mark_approved(by_user=getattr(request.user, "get_full_name", lambda: "")())

    # If MAJOR -> always SDT, no CS, no top-up
    if v.severity == 'MAJOR':
        new_settlement = 'SDT Settlement'
        # update violation if needed
        if (v.settlement_type != new_settlement) or v.is_settled:
            v.settlement_type = new_settlement
            v.is_settled = False
            v.settled_at = None
            v.save(update_fields=["settlement_type", "is_settled", "settled_at"])

        # email after commit
        transaction.on_commit(lambda: send_violation_email(
            request=request,
            violation=v,
            student=student,
            violation_count=None,    # or 0 / leave out, majors aren’t counted per-type
            settlement_type=new_settlement,
        ))

        messages.success(request, f"✅ Approved. Settlement: {new_settlement}.")
        return redirect('admin_violation')

    # ---------- MINOR logic below ----------

    # Count APPROVED MINORs of THIS TYPE for this student (includes this one now)
    approved_count = (
        Violation.objects
        .filter(
            student_id=student.tupc_id,
            status='Approved',
            severity='MINOR',
            violation_type=v.violation_type,
        )
        .count()
    )

    # Decide settlement for this MINOR violation
    if v.violation_type in CS_EXEMPT_TYPES:
        new_settlement = 'Apology Letter'
    else:
        new_settlement = 'Apology Letter' if approved_count == 1 else 'Community Service'

    # Apply settlement tag to this violation
    if (v.settlement_type != new_settlement) or v.is_settled:
        v.settlement_type = new_settlement
        v.is_settled = False
        v.settled_at = None
        v.save(update_fields=["settlement_type", "is_settled", "settled_at"])

    # ---- Community Service: compute top-up (per-type rule) ----
    hours_topup = Decimal('0')
    if (v.violation_type not in CS_EXEMPT_TYPES):
        hours_topup = compute_cs_topup_for_minor(v.violation_type, approved_count)

    # If there is a top-up, apply it ONCE by ledgering it to this violation
    if hours_topup > 0:
        if not hasattr(v, "cs_adjustment"):
            case = CommunityServiceCase.get_or_create_open(
                student_id=student.tupc_id,
                last_name=getattr(student, "last_name", "") or "",
                first_name=getattr(student, "first_name", "") or "",
                program_course=getattr(student, "program_course", "") or "",
                middle_initial=getattr(student, "middle_initial", "") or "",
                extension_name=getattr(student, "extension_name", "") or "",
            )
            case.top_up_required_hours(hours_topup)

            CommunityServiceAdjustment.objects.create(
                case=case,
                violation=v,
                hours=hours_topup,
                reason=f"{approved_count} offense of {v.violation_type}: +{hours_topup}h"
            )
        else:
            hours_topup = Decimal('0')

    # Email after commit
    transaction.on_commit(lambda: send_violation_email(
        request=request,
        violation=v,
        student=student,
        violation_count=approved_count,
        settlement_type=new_settlement,
    ))

    if hours_topup > 0:
        messages.success(
            request,
            f"✅ Approved. Settlement: {new_settlement}. Community Service +{hours_topup}h applied "
            f"(type: {v.violation_type}, offense #{approved_count})."
        )
    else:
        messages.success(request, f"✅ Approved. Settlement: {new_settlement}.")

    return redirect('admin_violation')

@role_required(['admin', 'staff'])
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

#------------------------------------#

def _current_facilitator_snapshot(request) -> tuple[str, str]:
    """
    Returns (name, source) where source in {"admin","faculty"} or ("","") if none.
    """
    s = request.session
    if s.get("facilitator_pk"):  # OTP flow
        return (s.get("facilitator_name", "") or "", "faculty")
    if s.get("user_id"):         # Admin/Staff login
        return (s.get("full_name", "") or "", "admin")
    return ("", "")

#-----admin community service--------#

@role_required(['admin', 'staff'])
@transaction.atomic
def cs_create_or_adjust(request):
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect('admin_community_service')

    form = CSCreateOrAdjustForm(request.POST)

    if not form.is_valid():
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
            'cs_form': form,
            'show_cs_modal': True,
        })

    data = form.cleaned_data
    sid = data["student_id"]
    new_total = Decimal(data["hours"])
    sdt_no = data.get("sdt_resolution_no", "").strip()  # may be ""

    case = (CommunityServiceCase.objects
            .select_for_update()
            .filter(student_id=sid, is_closed=False)
            .first())

    try:
        if case:
            # update snapshot fields
            case.last_name      = data["last_name"]
            case.first_name     = data["first_name"]
            case.middle_initial = data.get("middle_initial") or ""
            case.extension_name = data.get("extension_name") or ""
            case.program_course = data["program_course"]

            # attach SDT Resolution if provided (leave unchanged if blank)
            if sdt_no and sdt_no != (case.sdt_resolution_no or ""):
                case.sdt_resolution_no = sdt_no

            case.save(update_fields=[
                "last_name","first_name","middle_initial","extension_name",
                "program_course","sdt_resolution_no","updated_at"
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
                sdt_resolution_no=sdt_no,                     # <-- NEW on create
                total_required_hours=new_total,
                hours_completed=Decimal("0.0"),
                is_closed=(new_total == Decimal("0.0")),
            )
            messages.success(
                request,
                f"Community Service created for {case.last_name}, {case.first_name} ({case.student_id}) "
                f"with {case.total_required_hours}h."
            )

    except IntegrityError:
        # Likely the unique constraint on non-blank SDT numbers
        form.add_error("sdt_resolution_no", "This SDT Resolution No. is already used by another case.")
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
            'cs_form': form,
            'show_cs_modal': True,
        })

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

    fname, fsrc = _current_facilitator_snapshot(request)
    log = case.open_session(facilitator_name=fname, facilitator_source=fsrc)
    return JsonResponse({"ok": True, "status": "time_in", "log_id": log.id})

@require_POST
@transaction.atomic
def cs_scan_time_out(request, case_id):
    case = CommunityServiceCase.objects.select_for_update().get(id=case_id)
    scanned_raw = request.POST.get('scanned', '')
    scanned_id = _extract_tupc_id(scanned_raw)
    if not scanned_id or scanned_id != case.student_id:
        return JsonResponse({"ok": False, "error": "ID mismatch or unreadable scan."}, status=400)

    fname, fsrc = _current_facilitator_snapshot(request)
    log = case.close_open_session(facilitator_name=fname, facilitator_source=fsrc)
    if not log:
        return JsonResponse({"ok": False, "error": "No open session to close."}, status=400)
    return JsonResponse({"ok": True, "status": "time_out", "credited_hours": str(log.hours)})

#--------------------------------------------------#

#---------Facilitator Accounts---------------------#

ID_PATTERN = re.compile(r'^\d{2}-\d{3}$')   # NN-NNN
OTP_LENGTH = 6
OTP_TTL = timedelta(minutes=5)


RL_WINDOW = 600
SEND_LIMIT = 5
VERIFY_LIMIT = 8

def _generate_otp(length: int = OTP_LENGTH) -> str:
    return f"{secrets.randbelow(10**length):0{length}d}"

def _send_otp_email(to_email: str, code: str, full_name: str = "") -> None:
    subject = "Your One-Time Code"
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    body = (
        f"{greeting}\n\n"
        f"Your OTP is: {code}\n"
        f"This code expires in {int(OTP_TTL.total_seconds()//60)} minutes. "
        "If you didn’t request this, you can ignore this email.\n\n"
        "— Office of Student Affairs"
    )
    # Configure EMAIL_BACKEND etc. in settings; console backend is great for dev
    send_mail(subject, body, None, [to_email], fail_silently=False)

def _rl_hit(key: str, limit: int) -> bool:
    """
    Simple sliding-window-ish counter: returns True if under limit, else False.
    """
    now = int(timezone.now().timestamp())
    bucket = cache.get(key, [])
    bucket = [t for t in bucket if now - t < RL_WINDOW]
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    cache.set(key, bucket, RL_WINDOW)
    return True

@never_cache
def client_CS_view(request):
    if request.session.get("facilitator_pk"):
        resp = redirect("client_view_CS")
        return no_store(resp)
    resp = render(request, "myapp/client_CS.html")
    return no_store(resp)

@facilitator_required
def client_view_CS_view(request):
    fpk = request.session.get("facilitator_pk")
    if not fpk:
        messages.warning(request, "Please log in with your Faculty ID.")
        return no_store(redirect("client_CS"))

    if not Facilitator.objects.filter(pk=fpk, is_active=True).exists():
        for k in ("facilitator_pk", "facilitator_id", "facilitator_name"):
            request.session.pop(k, None)
        messages.error(request, "Session expired. Please log in again.")
        return no_store(redirect("client_CS"))

    q = (request.GET.get("q") or "").strip()
    qs = CommunityServiceCase.objects.order_by("-updated_at")
    if q:
        qs = qs.filter(
            Q(last_name__icontains=q) | Q(first_name__icontains=q) |
            Q(program_course__icontains=q) | Q(student_id__icontains=q)
        )
    resp = render(request, "myapp/client_view_CS.html", {"cases": qs, "q": q})
    return no_store(resp)

@require_POST
@never_cache
def otp_api(request):
    """
    POST actions:
      - action=send   + faculty_id
      - action=verify + faculty_id + otp
    Returns JSON.
    """
    action = (request.POST.get("action") or "").strip().lower()
    faculty_id = (request.POST.get("faculty_id") or "").strip()
    ip = request.META.get("REMOTE_ADDR", "0.0.0.0")

    # Basic faculty_id validation for both actions
    if not ID_PATTERN.match(faculty_id):
        return no_store(JsonResponse({"ok": False, "msg": "Invalid Faculty ID format."}, status=400))

    fac = (Facilitator.objects
           .filter(faculty_id=faculty_id, is_active=True)
           .only("id", "full_name", "email")
           .first())
    if not fac or not fac.email:
        return no_store(JsonResponse({"ok": False, "msg": "Account not found or no email on file."}, status=404))

    if action == "send":
        if not _rl_hit(f"otp_send:{faculty_id}", SEND_LIMIT) or not _rl_hit(f"otp_send_ip:{ip}", SEND_LIMIT):
            return no_store(JsonResponse({"ok": False, "msg": "Too many requests. Try again later."}, status=429))

        code = _generate_otp()
        otp_hash = make_password(code)
        OTPVerification.objects.filter(email=fac.email).delete()
        OTPVerification.objects.create(
            email=fac.email,
            otp=otp_hash,
            full_name=fac.full_name,
            role="facilitator",
            password="",
            is_active=False,
        )

        try:
            _send_otp_email(fac.email, code, fac.full_name)
        except Exception:
            return no_store(JsonResponse({"ok": False, "msg": "Failed to send OTP."}, status=500))

        return no_store(JsonResponse({"ok": True, "msg": "OTP sent to your email."}))

    elif action == "verify":
        if not _rl_hit(f"otp_verify:{faculty_id}", VERIFY_LIMIT) or not _rl_hit(f"otp_verify_ip:{ip}", VERIFY_LIMIT):
            return no_store(JsonResponse({"ok": False, "msg": "Too many attempts. Try again later."}, status=429))

        otp_plain = (request.POST.get("otp") or "").strip()
        if not (otp_plain.isdigit() and len(otp_plain) == OTP_LENGTH):
            return no_store(JsonResponse({"ok": False, "msg": "Invalid OTP."}, status=400))

        row = OTPVerification.objects.filter(email=fac.email).only("id", "otp", "created_at", "is_active").first()
        if not row:
            return no_store(JsonResponse({"ok": False, "msg": "No OTP request found."}, status=404))

        if timezone.now() - row.created_at > OTP_TTL:
            row.delete()
            return no_store(JsonResponse({"ok": False, "msg": "OTP expired. Request a new one."}, status=400))

        if not check_password(otp_plain, row.otp):
            return no_store(JsonResponse({"ok": False, "msg": "Incorrect OTP."}, status=400))

        # Success
        row.is_active = True
        row.save(update_fields=["is_active"])
        row.delete()
        request.session["facilitator_pk"] = fac.id
        request.session["facilitator_id"] = faculty_id
        request.session["facilitator_name"] = fac.full_name
        request.session.set_expiry(0)  

        return no_store(JsonResponse({"ok": True, "msg": "Logged in."}))

    else:
        return no_store(JsonResponse({"ok": False, "msg": "Unknown action."}, status=400))

@require_http_methods(["GET"])
@never_cache
def facilitator_logout_view(request):
    for k in ("facilitator_pk", "facilitator_id", "facilitator_name"):
        request.session.pop(k, None)
    messages.success(request, "Logged out (facilitator).")
    return no_store(redirect("client_CS"))

def cs_case_detail_api(request, case_id):
    case = get_object_or_404(CommunityServiceCase, id=case_id)

    vio = (Violation.objects
           .filter(student_id=case.student_id)
           .order_by('-violation_date', '-created_at')
           .values('violation_type', 'violation_date', 'status', 'id'))

    violations = [{
        "type": Violation.VIOLATION_TYPES_DICT.get(v['violation_type'], v['violation_type'])
                if hasattr(Violation, 'VIOLATION_TYPES_DICT') else v['violation_type'],
        "date": v['violation_date'].strftime('%b %d, %Y') if v['violation_date'] else '',
        "severity": getattr(Violation, 'severity', 'Minor') and 'Minor',  # fallback label
    } for v in vio]

    logs_qs = (case.logs
                   .order_by('-check_in_at')
                   .only('check_in_at', 'check_out_at', 'hours', 'is_official',
                         'facilitator_name', 'facilitator_source'))

    logs = []
    for l in logs_qs:
        cin = timezone.localtime(l.check_in_at)
        cout = timezone.localtime(l.check_out_at) if l.check_out_at else None
        logs.append({
            "date": cin.strftime('%b %d, %Y'),
            "in":   cin.strftime('%I:%M %p'),
            "out":  cout.strftime('%I:%M %p') if cout else None,
            "hours": str(l.hours),
            "is_official": l.is_official,
            "facilitator_name": l.facilitator_name or "",
            "facilitator_source": l.facilitator_source or "",
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







    # ------------------------ ELECTION - ADMIN








#---------Election Accounts---------------------#
@role_required(['admin', 'comselec'])
def admin_election_view(request):
    return render (request, 'myapp/admin_election.html')

def _active_election():
    return Election.objects.filter(status='active').order_by('-start_date').first()

def _clean_org(s: str) -> str:
    s = re.sub(r'[^A-Za-z0-9 .&-]+', '', s or '').strip()
    return re.sub(r'\s+', ' ', s)

def _pos_rank(pos: str) -> int:
    if pos == 'President': return 0
    if pos == 'Vice President': return 1
    if pos == 'Senator': return 2
    if pos.endswith('Governor'): return 3  
    return 99

@role_required(['admin', 'comselec'])
@require_http_methods(["GET"])
def get_candidates(request):
    e = _active_election()
    if not e:
        return JsonResponse({"status":"no_active"})
    qs = Candidate.objects.filter(election=e, is_withdrawn=False)
    data = [{
        "id": c.id,
        "name": c.name,
        "section": c.section,
        "tupc_id": c.tupc_id,
        "position": c.position, 
        "party": c.party or "",
        "image": c.image.url if c.image and hasattr(c.image,'url') else "",
    } for c in sorted(qs, key=lambda c: (_pos_rank(c.position), c.name.lower()))]
    return JsonResponse({"status":"success","election":{"id":e.id,"name":e.name,"academic_year":e.academic_year},"candidates":data})

def add_candidate(request):
    try:
        with transaction.atomic():
            e = Election.objects.select_for_update().filter(status='active').order_by('-start_date').first()
            if not e:
                return JsonResponse({"status":"error","message":"No active election to add candidates."}, status=400)
            if e.status == 'finalized':
                return JsonResponse({"status":"error","message":"Election is finalized."}, status=400)

            name     = (request.POST.get('name') or '').strip()
            section  = (request.POST.get('section') or '').strip()
            tupc_id  = normalize_tup_id(request.POST.get('tupc_id') or '')
            position = (request.POST.get('position') or '').strip()
            party    = (request.POST.get('party') or '').strip()
            photo    = request.FILES.get('photo')
            org      = (request.POST.get('org') or '').strip()

            if not all([name, section, tupc_id, position, photo]):
                return JsonResponse({"status":"error","message":"Missing required fields."}, status=400)

            if Candidate.objects.filter(election=e, tupc_id__iexact=tupc_id).exists():
                return JsonResponse({"status":"error","message":"This TUPC ID already has a candidate entry in this election."}, status=409)

            if position.lower() == 'governor':
                if not org:
                    return JsonResponse({"status":"error","message":"Program/Organization is required for Governor."}, status=400)
                org_clean = _clean_org(org)
                position = f"{org_clean} Governor"

            c = Candidate.objects.create(
                election=e,
                academic_year=e.academic_year,
                tupc_id=tupc_id,
                name=name,
                section=section,
                position=position,   
                party=party,
                image=photo
            )
        return JsonResponse({"status":"success","id": c.id})
    except Exception as ex:
        return JsonResponse({"status":"error","message": f"{ex}"}, status=500)

@role_required(['admin', 'comselec'])
@require_POST
def delete_candidate(request, cid):
    c = get_object_or_404(Candidate, id=cid)
    if c.election.status != 'active': 
        return JsonResponse({"status":"error","message":"Election not active. Deletion disabled."}, status=400)
    c.delete()
    return JsonResponse({"status":"success"})


###################################################################
@role_required(['admin', 'comselec'])
def admin_election_results_view(request):
    return render(request, 'myapp/admin_election_results.html')

@role_required(['admin', 'comselec'])
@require_http_methods(["GET"])
def api_admin_elections_list(request):
    """
    GET /api/admin/elections/
    Returns a small list for the dropdown:
      { status:'success', elections:[{id,label,is_active}, ...] }
    """
    rows = Election.objects.order_by('-start_date', '-id')
    out = []
    for e in rows:
        status_tag = "Active" if e.status == 'active' else e.status.capitalize()
        out.append({
            "id": e.id,
            "label": f"{e.name} ({e.academic_year}) — {status_tag}",
            "is_active": (e.status == 'active'),
        })
    return JsonResponse({"status": "success", "elections": out})

@role_required(['admin', 'comselec'])
@require_http_methods(["GET"])
def api_admin_results_data(request):
    """
    GET /api/admin/results/?election_id=<id>   (if omitted -> active election)
    """
    # --- resolve election ---
    eid = request.GET.get('election_id')
    if eid:
        e = get_object_or_404(Election, id=eid)
    else:
        e = _active_election()
        if not e:
            e = Election.objects.order_by('-start_date', '-id').first()
            if not e:
                return JsonResponse({"status": "success",
                                     "message": "No elections found.",
                                     "positions": {} })

    # --- base candidates ---
    base = Candidate.objects.filter(election=e, is_withdrawn=False)

    pres_qs = base.filter(position='President').order_by('name')
    vp_qs   = base.filter(position='Vice President').order_by('name')
    sen_qs  = base.filter(position='Senator').order_by('name')
    gov_qs  = base.filter(position__icontains='Governor').order_by('position','name')

    # --- all vote rows for this election ---
    votes_qs = Vote.objects.filter(election=e)
    ballots_total = votes_qs.count()  # used for thresholds & percentages

    # --- init tallies ---
    def init_counts(qs):
        return {cid: 0 for cid in qs.values_list('id', flat=True)}

    pres_counts = init_counts(pres_qs)
    vp_counts   = init_counts(vp_qs)
    sen_counts  = init_counts(sen_qs)

    gov_labels = sorted(gov_qs.values_list('position', flat=True).distinct())

    # Helpers for org-based governor math
    def _org_key_from_label(label: str) -> str:
        # "FEO Governor" -> "FEO"
        return (label or "").replace(" Governor", "").strip().upper()

    # Map governor-candidate-id -> org key
    gov_cid_to_org = {}
    for label in gov_labels:
        orgk = _org_key_from_label(label)
        for cid in gov_qs.filter(position=label).values_list('id', flat=True):
            gov_cid_to_org[cid] = orgk

    # Per-org electorate and per-org candidate counters
    org_keys = sorted({_org_key_from_label(lbl) for lbl in gov_labels} - {''})
    ballots_per_org = {k: 0 for k in org_keys}
    gov_counts_by_org = {
        k: {cid: 0 for cid in gov_qs.filter(position=f"{k} Governor").values_list('id', flat=True)}
        for k in org_keys
    }

    SENATOR_SEATS = 9

    pres_abstain = 0
    vp_abstain   = 0
    senator_filled_slots_total = 0   # number of non-empty senator picks across all ballots
    senator_total_slots = ballots_total * SENATOR_SEATS

    # --- tally loop ---
    for v in votes_qs:
        b = v.ballot or {}

        # President
        pid = b.get('president')
        if pid and pid in pres_counts:
            pres_counts[pid] += 1
        else:
            pres_abstain += 1

        # Vice President
        vid = b.get('vice_president')
        if vid and vid in vp_counts:
            vp_counts[vid] += 1
        else:
            vp_abstain += 1

        # Senators (dedupe per ballot)
        seen = set()
        for sid in (b.get('senators') or []):
            if sid and sid in sen_counts and sid not in seen:
                sen_counts[sid] += 1
                senator_filled_slots_total += 1
                seen.add(sid)

        # Governor (per-org electorate)
        gid = b.get('governor')
        voter_org = (b.get('voter_org') or '').strip().upper()

        # infer org for legacy rows with no voter_org but with a governor pick
        if not voter_org and gid and gid in gov_cid_to_org:
            voter_org = gov_cid_to_org.get(gid, '')

        if voter_org in ballots_per_org:
            ballots_per_org[voter_org] += 1
            if gid and gid in gov_counts_by_org[voter_org]:
                gov_counts_by_org[voter_org][gid] += 1
        else:
            # no org / not mapped -> exclude from org electorates (doesn't harm anyone)
            pass

    # --- helpers to pack lists ---
    def pack_list_percent_of_total_ballots(qs, counts: dict):
        """Return list with percent relative to *ballots_total* (not candidate sum)."""
        base_pct = ballots_total or 1
        meta = {c.id: (c.name, (c.party or '')) for c in qs}
        out = []
        for cid, cnt in counts.items():
            name, party = meta.get(cid, (f"#{cid}", ""))
            out.append({
                "id": cid,
                "name": name,
                "party": party,
                "votes": cnt,
                "percent": round(cnt * 100.0 / base_pct, 2)
            })
        out.sort(key=lambda x: (-x['votes'], x['name'].lower()))
        return out

    # --- Single-seat blocks (President/VP as percent of total ballots) ---
    def single_seat_block(qs, counts, abstain_count, title):
        rows = pack_list_percent_of_total_ballots(qs, counts)
        single_candidate = qs.count() == 1
        block = {
            "mode": "majority" if single_candidate else "plurality",
            "candidates": rows,
            "abstain": abstain_count,
            "abstain_percent": round((abstain_count * 100.0 / (ballots_total or 1)), 2),
        }
        if single_candidate:
            threshold = (ballots_total // 2) + 1 if ballots_total > 0 else 0
            block["threshold"] = threshold
            block["approved"] = [r for r in rows if r["votes"] >= threshold][:1]
            block["notes"] = f"Uncontested {title}: candidate must reach 50%+1 of ballots."
        return block

    president_block = single_seat_block(pres_qs, pres_counts, pres_abstain, "President")
    vp_block        = single_seat_block(vp_qs,   vp_counts,   vp_abstain,   "Vice President")

    def _norm_party(p):
        p = (p or '').strip().upper()
        return p if p else 'INDEPENDENT'

    sen_parties = {_norm_party(c.party) for c in sen_qs}
    uncontested = (len(sen_parties) == 1 and sen_qs.count() <= SENATOR_SEATS)

    sen_rows = pack_list_percent_of_total_ballots(sen_qs, sen_counts)

    if uncontested:
        threshold = (ballots_total // 2) + 1 if ballots_total > 0 else 0
        approved = [r for r in sen_rows if r["votes"] >= threshold][:SENATOR_SEATS]
        vacant = max(0, SENATOR_SEATS - len(approved))
        senator_block = {
            "mode": "majority",
            "seat_count": SENATOR_SEATS,
            "candidates": sen_rows,
            "threshold": threshold,
            "approved": approved,
            "vacant_seats": vacant,
            "notes": "Uncontested senate: each candidate must reach 50%+1 of ballots."
        }
    else:
        winners = sen_rows[:SENATOR_SEATS]
        abstain_slots = max(0, senator_total_slots - senator_filled_slots_total)
        senator_block = {
            "mode": "plurality",
            "seat_count": SENATOR_SEATS,
            "candidates": sen_rows,
            "winners": winners,
            "abstain_slots": abstain_slots
        }
    senator_block["ballots_total"] = ballots_total

    # --- Governors by org label (percent & thresholds use org electorate) ---
    def pack_governor_block(label):
        orgk = _org_key_from_label(label)
        qs = gov_qs.filter(position=label)
        candidate_ids = list(qs.values_list('id', flat=True))

        org_total = ballots_per_org.get(orgk, 0)
        counts_map = gov_counts_by_org.get(orgk, {cid: 0 for cid in candidate_ids})

        base_pct = org_total or 1
        meta = {c.id: (c.name, (c.party or '')) for c in qs}
        rows = []
        for cid in candidate_ids:
            cnt = counts_map.get(cid, 0)
            name, party = meta.get(cid, (f"#{cid}", ""))
            rows.append({
                "id": cid,
                "name": name,
                "party": party,
                "votes": cnt,
                "percent": round(cnt * 100.0 / base_pct, 2)
            })
        rows.sort(key=lambda x: (-x['votes'], x['name'].lower()))

        abstain_cnt = max(0, org_total - sum(counts_map.get(cid, 0) for cid in candidate_ids))
        abstain_pct = round(abstain_cnt * 100.0 / base_pct, 2)

        mode = "majority" if qs.count() == 1 else "plurality"
        block = {
            "candidates": rows,
            "mode": mode,
            "org_ballots": org_total,
            "abstain": abstain_cnt,
            "abstain_percent": abstain_pct,
        }
        if mode == "majority":
            threshold = (org_total // 2) + 1 if org_total > 0 else 0
            block["threshold"] = threshold
            block["approved"] = [r for r in rows if r["votes"] >= threshold][:1]
            block["notes"] = f"{label}: candidate must reach 50%+1 of eligible ballots."
        return block

    gov_groups = {label: pack_governor_block(label) for label in gov_labels}
    overall_abstain = sum(
        max(0, ballots_per_org.get(_org_key_from_label(lbl), 0) -
                sum(gov_counts_by_org.get(_org_key_from_label(lbl), {}).values()))
        for lbl in gov_labels
    )

    governors_block = {
        "groups": gov_groups,
        "overall_abstain": overall_abstain
    }

    return JsonResponse({
        "status": "success",
        "election": {"id": e.id, "name": e.name, "academic_year": e.academic_year},
        "ballots_total": ballots_total, 
        "positions": {
            "President": president_block,
            "Vice President": vp_block,
            "Senator": senator_block,
            "Governors": governors_block
        }
    })



###################################################################
@role_required(['admin', 'comselec'])
def admin_election_manage_view(request):
    elections = Election.objects.order_by('-start_date')[:20]
    today = timezone.localdate()
    return render(request, 'myapp/admin_election_manage.html', {
        'elections': elections,
        'now': today,  
    })

@role_required(['admin', 'comselec'])
@require_POST
def eligibles_upload_view(request, eid):
    election = get_object_or_404(Election, id=eid)
    f = request.FILES.get('csv')
    if not f:
        messages.error(request, "Please choose a CSV file (one TUP ID per line, no headers).")
        return redirect('admin_election_manage')

    try:
        raw = f.read().decode('utf-8-sig', errors='ignore')
        raw_ids = (line.strip().strip(',;') for line in io.StringIO(raw))

        ids, seen = [], set()
        for s in raw_ids:
            sid = normalize_tup_id(s)
            if sid and sid not in seen:
                ids.append(sid); seen.add(sid)

        if not ids:
            messages.error(request, "No valid TUP IDs found in file.")
            return redirect('admin_election_manage')

        existing_students = set(
            Student.objects.filter(tupc_id__in=ids).values_list('tupc_id', flat=True)
        )
        matched = [sid for sid in ids if sid in existing_students]
        skipped = [sid for sid in ids if sid not in existing_students]

        if not matched:
            messages.error(request, "No IDs matched Student records.")
            if skipped:
                sample = ", ".join(skipped[:10])
                more = f" …(+{len(skipped)-10} more)" if len(skipped) > 10 else ""
                messages.info(request, f"Not in Student (sample): {sample}{more}")
            return redirect('admin_election_manage')

        created_count = 0
        enabled_count = 0

        with transaction.atomic():
            existing_qs = EligibleVoter.objects.select_for_update().filter(
                election=election, student_id__in=matched
            )
            existing_list = list(existing_qs)
            existing_map = {ev.student_id: ev for ev in existing_list}
            to_create_sids = [sid for sid in matched if sid not in existing_map]
            to_create = [
                EligibleVoter(election=election, student_id=sid, is_eligible=True)
                for sid in to_create_sids
            ]
            if to_create:
                EligibleVoter.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=2000)
                created_count = EligibleVoter.objects.filter(
                    election=election, student_id__in=to_create_sids
                ).count()

            to_enable_ids = [ev.id for ev in existing_list if not ev.is_eligible]
            if to_enable_ids:
                updated = EligibleVoter.objects.filter(id__in=to_enable_ids).update(is_eligible=True)
                enabled_count = updated

        messages.success(
            request,
            (
                f"Uploaded for {election.academic_year}: "
                f"{len(ids)} unique IDs parsed; "
                f"{len(matched)} matched Student records; "
                f"{created_count} newly added; "
                f"{enabled_count} re-enabled; "
                f"{len(skipped)} skipped (not in Student)."
            )
        )
        if skipped:
            sample = ", ".join(skipped[:10])
            more = f" …(+{len(skipped)-10} more)" if len(skipped) > 10 else ""
            messages.info(request, f"Not in Student (sample): {sample}{more}")

    except Exception as e:
        messages.error(request, f"Upload failed: {e}")

    return redirect('admin_election_manage')

DASHES = r"[‐-‒–—―]" 

def normalize_tup_id(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    # unify dashes to ASCII hyphen
    s = re.sub(DASHES, "-", s)
    # collapse internal spaces (remove or you can change to replace with nothing)
    s = re.sub(r"\s+", "", s)
    # keep only A–Z, 0–9, and hyphen
    s = re.sub(r"[^A-Za-z0-9-]", "", s)
    # uppercase
    return s.upper()

ID_SCAN_REGEX = re.compile(r"(TUP[A-Z]*-\d{2}-\d{3,10})", re.IGNORECASE)

def extract_tup_id_from_qr(raw: str) -> str:
    if not raw:
        return ""
    m = ID_SCAN_REGEX.search(raw)
    if m:
        return normalize_tup_id(m.group(1))
    # fallback: take first token & normalize if it looks like a TUP id
    token = (raw.split()[0] if raw.split() else raw)
    token = normalize_tup_id(token)
    return token if token.startswith("TUP") else ""

@role_required(['admin', 'comselec'])
@require_POST
def api_eligible_scan(request, eid):
    election = get_object_or_404(Election, id=eid)
    raw = (request.POST.get('payload') or '').strip()
    sid = extract_tup_id_from_qr(raw)  

    if not sid:
        return JsonResponse({"status": "error", "message": "No TUP ID found in scan."}, status=400)

    if not Student.objects.filter(tupc_id__iexact=sid).exists():
        return JsonResponse({"status": "not_in_student", "sid": sid})
    already_voted = Vote.objects.filter(
        election=election,
        voter_student_id__iexact=sid
    ).exists()
    try:
        with transaction.atomic():
            ev, created = EligibleVoter.objects.select_for_update().get_or_create(
                election=election,
                student_id=sid,              
                defaults={"is_eligible": True}
            )
            if created:
                result = "enrolled"
            elif not ev.is_eligible:
                ev.is_eligible = True
                ev.save(update_fields=["is_eligible"])
                result = "re_enabled"
            else:
                result = "already_eligible"
    except IntegrityError:
        result = "already_eligible"
    eligible_count = EligibleVoter.objects.filter(election=election, is_eligible=True).count()
    stu = Student.objects.filter(tupc_id__iexact=sid).values(
        'first_name', 'last_name', 'program'
    ).first() or {}
    name = f"{(stu.get('first_name') or '').strip()} {(stu.get('last_name') or '').strip()}".strip() or None

    return JsonResponse({
        "status": result,
        "sid": sid,
        "already_voted": already_voted,
        "eligible_count": eligible_count,
        "student": {"name": name, "program": stu.get('program') or None},
    })
    
def _to_aware(dt_str):
    dt = parse_datetime(dt_str)  # expects 'YYYY-MM-DDTHH:MM'
    if dt is None: return None
    return make_aware(dt) if is_naive(dt) else dt

def _someone_else_active(exclude_id=None):
    qs = Election.objects.filter(status='active')
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()

@role_required(['admin', 'comselec'])
@require_POST
def admin_election_create(request):
    name = (request.POST.get('name') or 'Student Government Election').strip()
    ay   = (request.POST.get('academic_year') or '').strip()
    end  = request.POST.get('end_date')

    if not ay:
        messages.error(request, "Academic year is required.")
        return redirect('admin_election_manage')
    try:
        end_date = date.fromisoformat(end)
    except Exception:
        messages.error(request, "Invalid end date.")
        return redirect('admin_election_manage')

    today = timezone.localdate()
    if end_date < today:
        messages.error(request, "End cannot be before today."); return redirect('admin_election_manage')
    if end_date > today + timedelta(days=60):
        messages.error(request, "Window must be within 60 days."); return redirect('admin_election_manage')

    if _someone_else_active():
        messages.error(request, "Cannot create a new election while another is ACTIVE. Close/finalize it first.")
        return redirect('admin_election_manage')

    Election.objects.create(
        name=name,
        academic_year=ay,
        start_date=today,
        end_date=end_date,
        status='active',
        is_finalized=False,
    )
    messages.success(request, f"Election {ay} created and opened today.")
    return redirect('admin_election_manage')

@role_required(['admin', 'comselec'])
@require_POST
def admin_election_open_now(request, eid):
    with transaction.atomic():
        e = Election.objects.select_for_update().get(id=eid)
        if Election.objects.select_for_update().filter(status='active').exclude(id=e.id).exists():
            messages.error(request, "Cannot open: another election is already ACTIVE.")
            return redirect('admin_election_manage')

        today = timezone.localdate()
        e.start_date = today
        max_end = e.start_date + timedelta(days=60)
        if e.end_date < e.start_date or e.end_date > max_end:
            e.end_date = max_end
        e.status = 'active'
        e.is_finalized = False
        e.save(update_fields=['start_date','end_date','status','is_finalized'])

    messages.success(request, f"Election opened today for {e.academic_year}.")
    return redirect('admin_election_manage')

@role_required(['admin', 'comselec'])
@require_POST
def admin_election_close_now(request, eid):
    e = get_object_or_404(Election, id=eid)
    if e.status in ('closed', 'finalized'):
        messages.success(request, f"Election {e.name} closed.")
        return redirect('admin_election_manage')

    e.status = 'closed'
    e.end_date = timezone.localdate() 
    e.save(update_fields=['status','end_date'])
    messages.success(request, f"Election {e.name} is already closed.")
    return redirect('admin_election_manage')

@role_required(['admin', 'comselec'])
@require_POST
def admin_election_finalize(request, eid):
    e = get_object_or_404(Election, id=eid)
    e.status = 'finalized'
    e.is_finalized = True
    e.save(update_fields=['status','is_finalized'])
    messages.success(request, "Election finalized (locked).")
    return redirect('admin_election_manage')














# === views.py (client election) ==============================================

def _get_voter_from_session(request):
    return request.session.get('voter') or {}

def __clean_org(s: str) -> str:
    return (s or '').upper().strip()

def voter_required_page(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        e = _active_election()
        voter = _get_voter_from_session(request)
        if not e:
            messages.warning(request, "No active election.")
            return redirect('client_election')
        if not voter or voter.get('election_id') != e.id:
            messages.warning(request, "Please log in with your TUPC ID and organization to access the ballot.")
            return redirect('client_election')

        sid = voter.get('student_id')
        if Vote.objects.filter(election=e, voter_student_id__iexact=sid).exists():
            request.session.pop('voter', None)   
            request.session.modified = True
            messages.info(request, "You have already voted.")
            return redirect('client_election')

        request.election = e
        request.voter = voter
        return view_func(request, *args, **kwargs)
    return _wrapped

def voter_required_api(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        e = _active_election()
        voter = _get_voter_from_session(request)
        if not e:
            return JsonResponse({"status":"error","message":"No active election."}, status=400)
        if not voter or voter.get('election_id') != e.id:
            return JsonResponse({"status":"error","message":"Login required."}, status=401)
        sid = voter.get('student_id')
        if Vote.objects.filter(election=e, voter_student_id__iexact=sid).exists():
            request.session.pop('voter', None)
            request.session.modified = True
            return JsonResponse({"status":"already_voted"}, status=409)

        request.election = e
        request.voter = voter
        return view_func(request, *args, **kwargs)
    return _wrapped

# ---------- Pages ----------
@never_cache
@ensure_csrf_cookie
def client_election_view(request):
    """Login page (org + TUPC ID)."""
    return render(request, 'myapp/client_election.html')

@never_cache
@ensure_csrf_cookie
@voter_required_page
def client_view_election_view(request):
    """Ballot page (requires voter session)."""
    return render(request, 'myapp/client_view_election.html', {
        'election': request.election,
        'voter_sid': request.voter.get('student_id'),
        'voter_org': request.voter.get('org'),
    })

@never_cache
def client_logout(request):
    request.session.flush()           
    messages.success(request, "You have been logged out.")
    return redirect('client_election')

# ---------- Login API (eligibility + session login) ----------

@csrf_exempt
@require_POST
def api_check_eligibility(request):
    """POST: student_id, org  → session login if eligible & not yet voted."""
    sid = normalize_tup_id(request.POST.get('student_id') or '')
    org = __clean_org(request.POST.get('org') or '')

    if not sid:
        return JsonResponse({"status":"error","message":"Missing TUPC ID."}, status=400)
    if not org:
        return JsonResponse({"status":"error","message":"Program/Organization is required."}, status=400)

    e = _active_election()
    if not e:
        return JsonResponse({"status":"error","message":"No active election right now."}, status=400)

    listed = EligibleVoter.objects.filter(election=e, student_id__iexact=sid, is_eligible=True).exists()
    if not listed:
        return JsonResponse({"status":"not_listed"})

    already = Vote.objects.filter(election=e, voter_student_id__iexact=sid).exists()
    if already:
        return JsonResponse({"status":"already_voted"})

    request.session['voter'] = {'election_id': e.id, 'student_id': sid, 'org': org}
    request.session.modified = True

    return JsonResponse({
        "status":"eligible",
        "election":{"id": e.id, "name": e.name, "academic_year": e.academic_year}
    })

# ---------- Ballot API (fetch lists + parties) ----------

@voter_required_api
@require_http_methods(["GET"])
def api_get_ballot(request):
    """
    Returns candidate lists for President, Vice President, Senator (all),
    and <ORG> Governor (only that org). Also returns distinct party names.
    Seats: senators=9, governor=1.
    """
    e = request.election
    org = request.voter.get('org')

    base = Candidate.objects.filter(election=e, is_withdrawn=False)

    presidents = list(base.filter(position='President').order_by('name'))
    vps        = list(base.filter(position='Vice President').order_by('name'))
    senators   = list(base.filter(position='Senator').order_by('name'))

    gov_label = f"{org} Governor"
    governors = list(base.filter(position__iexact=gov_label).order_by('name'))

    def pack(qs):
        return [{
            "id": c.id,
            "name": c.name,
            "section": c.section,
            "party": c.party or "",
            "image": (c.image.url if c.image and hasattr(c.image,'url') else "")
        } for c in qs]

    parties = list(
        base.exclude(party__isnull=True).exclude(party__exact="")
            .values_list('party', flat=True).distinct().order_by('party')
    )

    seats = {"senator": 9, "governor": 1}

    return JsonResponse({
        "status": "success",
        "election": {"id": e.id, "name": e.name, "academic_year": e.academic_year},
        "org": org,
        "ballot": {
            "President": pack(presidents),
            "Vice President": pack(vps),
            "Senator": pack(senators),
            gov_label: pack(governors),  
        },
        "seats": seats,
        "parties": parties,
    })

@voter_required_api
@require_POST
def api_submit_vote(request):
    """
    POST fields:
      - president: candidate_id or "" (abstain)
      - vice_president: candidate_id or "" (abstain)
      - senators: JSON array (length up to 9) of candidate_id or "" (abstain entries ok)
      - governor: candidate_id or "" (abstain)
      - email: optional (to send receipt)
    """
    e = request.election
    voter = request.voter
    sid = voter.get('student_id')
    org = voter.get('org')

    SENATOR_SEATS = 9

    def to_id_or_none(raw):
        s = (raw or "").strip()
        return int(s) if s.isdigit() else None

    president_id      = to_id_or_none(request.POST.get('president'))
    vice_president_id = to_id_or_none(request.POST.get('vice_president'))
    governor_id       = to_id_or_none(request.POST.get('governor'))
    email_raw         = (request.POST.get('email') or '').strip()
    email = ""
    if email_raw:
        try:
            validate_email(email_raw)
            email = email_raw
        except ValidationError:
            return JsonResponse({"status":"error","message":"Invalid email address."}, status=400)

    senators_raw = request.POST.get('senators')
    try:
        senators_list = json.loads(senators_raw) if senators_raw else []
    except Exception:
        return JsonResponse({"status":"error","message":"Invalid senators payload."}, status=400)
    norm_sen = []
    for x in senators_list:
        if x is None or str(x).strip()=="":
            continue
        if str(x).isdigit():
            norm_sen.append(int(x))
        else:
            return JsonResponse({"status":"error","message":"Invalid senator choice."}, status=400)
    norm_sen = list(dict.fromkeys(norm_sen))[:SENATOR_SEATS]
    base = Candidate.objects.filter(election=e, is_withdrawn=False)
    pres_ids = set(base.filter(position='President').values_list('id', flat=True))
    vp_ids   = set(base.filter(position='Vice President').values_list('id', flat=True))
    sen_ids  = set(base.filter(position='Senator').values_list('id', flat=True))
    gov_ids  = set(base.filter(position__iexact=f"{org} Governor").values_list('id', flat=True))

    if president_id is not None and president_id not in pres_ids:
        return JsonResponse({"status":"error","message":"Invalid president choice."}, status=400)
    if vice_president_id is not None and vice_president_id not in vp_ids:
        return JsonResponse({"status":"error","message":"Invalid vice president choice."}, status=400)
    if any(i not in sen_ids for i in norm_sen):
        return JsonResponse({"status":"error","message":"Invalid senator choice(s)."}, status=400)
    if governor_id is not None and governor_id not in gov_ids:
        return JsonResponse({"status":"error","message":"Invalid governor choice for your organization."}, status=400)

    if Vote.objects.filter(election=e, voter_student_id__iexact=sid).exists():
        return JsonResponse({"status":"error","message":"You have already voted."}, status=409)

    with transaction.atomic():
        Vote.objects.create(
            election=e,
            voter_student_id=sid,
            email=email or "",
            ballot={
                "president": president_id,        
                "vice_president": vice_president_id, 
                "senators": norm_sen,                
                "governor": governor_id,          
                "voter_org": org                  
            }
        )

    if email:
        chosen_ids = [x for x in [president_id, vice_president_id, governor_id, *norm_sen] if x]
        names = dict(Candidate.objects.filter(id__in=chosen_ids).values_list('id', 'name'))

        def n(id_): return "ABSTAIN" if not id_ else names.get(int(id_), f"#{id_}")
        lines = []
        lines.append(f"Election: {e.name} ({e.academic_year})")
        lines.append(f"Voter: {sid}")
        if org: lines.append(f"Program/Organization: {org}")
        lines.append("")
        lines.append(f"President: {n(president_id)}")
        lines.append(f"Vice President: {n(vice_president_id)}")
        lines.append("Senators: " + (", ".join([n(x) for x in norm_sen]) if norm_sen else "ABSTAIN ALL"))
        lines.append(f"Governor: {n(governor_id)}")
        lines.append("")
        lines.append("Thank you for voting!")
        body = "\n".join(lines)

        def _send():
            send_mail_async(
                subject=f"{e.name} ({e.academic_year}) - Your Ballot Receipt",
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost'),
                recipient_list=[email],
                fail_silently=False,
            )
        transaction.on_commit(_send) 

    return JsonResponse({"status":"success", "logout_after": 5})