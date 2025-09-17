from django.urls import path
from . import views
from django.urls import re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('current_time/', views.current_time, name='current_time'),
    path('', views.home_view, name='client_home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('auth/otp/send', views.login_send_otp, name='login_send_otp'),
    path('auth/otp/verify', views.login_verify_otp, name='login_verify_otp'),
    path('auth/reset-password', views.login_reset_password, name='login_reset_password'),
    
    
    path('guard_violation/', views.guard_violation_view, name='guard_violation'),
    path('guard_report/', views.guard_report_view, name='guard_report'),
    path('client_goodmoral/', views.client_goodmoral_view, name='client_goodmoral'),
    path('client_scholarships/', views.client_scholarships_view, name='client_scholarships'),
    path('client_SurrenderingID/', views.client_SurrenderingID_view, name='client_SurrenderingID'),
    path('client_studentAssistantship/', views.client_studentAssistantship_view, name='client_studentAssistantship'),
    path('client_ACSO/', views.client_ACSO_view, name='client_ACSO'),
    path('client_lostandfound/', views.client_lostandfound_view, name='client_lostandfound'),
  

    
    path('client_view_CS/', views.client_view_CS_view, name='client_view_CS'),
    path('client_CS/', views.client_CS_view, name='client_CS'),
    path("client_cs/otp/", views.otp_api, name="otp_api"), 
    path("client/logout/", views.facilitator_logout_view, name="facilitator_logout"),
     
    path('client_clearance/', views.client_clearance_view, name='client_clearance'),
    path("clearance/", views.clearance_request_view, name="clearance_request"),
    
    
    path("admin_add_faculty/", views.admin_add_faculty_view, name="admin_add_faculty"),
    path("facilitators/<int:pk>/delete/", views.facilitator_delete, name="facilitator_delete"),
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path("admin_dashboard/data/", views.admin_dashboard_data, name="admin_dashboard_data"),
    
    # --- accounts ---
    path('admin_accounts/', views.admin_accounts_view, name='admin_accounts'),
    path('get-accounts/', views.get_accounts_data, name='get_accounts'),
    path('deactivate-account/<str:user_email>/', views.deactivate_account, name='deactivate_account'),
    path('edit-account/<str:user_email>/', views.edit_account, name='edit_account'),
    path('request-otp/', views.request_otp, name='request_otp'),
    path('verify-otp/',  views.verify_otp,  name='verify_otp'),
    path('email-change/request/', views.email_change_request, name='email_change_request'),
    path('email-change/verify/',  views.email_change_verify,  name='email_change_verify'),
    path('email-change/apply/',   views.email_change_apply,   name='email_change_apply'),
    path('password-otp/request/', views.password_otp_request, name='password_otp_request'),
    path('password-otp/verify/',  views.password_otp_verify,  name='password_otp_verify'),
    path('change-password/<str:email>/', views.change_password, name='change_password'),
    # ---------------
    
    # --- report ---
    path('admin_report/', views.admin_report_view, name='admin_report'),
    path('reports/violations.pdf',   views.admin_violation_report_pdf,    name='admin_violation_report_pdf'),
    path('reports/good-moral.pdf',   views.admin_good_moral_report_pdf,   name='admin_good_moral_report_pdf'),
    path('reports/surrender-id.pdf', views.admin_surrender_id_report_pdf, name='admin_surrender_id_report_pdf'),
    path('reports/clearance.pdf',    views.admin_clearance_report_pdf,    name='admin_clearance_report_pdf'),
    # ---------------
    
    
    path('admin_ackreq/', views.admin_ackreq_view, name='admin_ackreq'),
    path("ackreq/batch-preview", views.batch_view_ackreq_receipts, name="ackreq_batch_preview"),
    
    path('admin_ACSO/', views.admin_ACSO_view, name='admin_ACSO'),
    path('admin_assistantship/', views.admin_assistantship_view, name='admin_assistantship'),
    path("gmf/batch-preview", views.batch_view_gmf, name="gmf_batch_preview"),

    
    path('admin_community_service/', views.admin_community_service, name='admin_community_service'),
    path('admin_community_service/<int:case_id>/', views.admin_view_community_service, name='admin_view_community_service'),
    path('admin_community_service/<int:case_id>/update-total/', views.cs_update_total_required, name='cs_update_total_required'),
    path('admin_community_service/<int:case_id>/scan/time-in/', views.cs_scan_time_in, name='cs_scan_time_in'),
    path('admin_community_service/<int:case_id>/scan/time-out/', views.cs_scan_time_out, name='cs_scan_time_out'),
    path('admin_community_service/create-or-adjust/', views.cs_create_or_adjust, name='cs_create_or_adjust'),
    path('api/cs/case/<int:case_id>/', views.cs_case_detail_api, name='cs_case_detail_api'),
    
    
    path('admin_lostandfound/', views.admin_lostandfound_view, name='admin_lostandfound'),
    path('admin_report/', views.admin_report_view, name='admin_report'),
    path('admin_scholarships/', views.admin_scholarships_view, name='admin_scholarships'),
    path('admin_view_ackreq/<int:pk>/', views.admin_view_ackreq_view, name='admin_view_ackreq'),
    
    path('admin_clearance/', views.admin_clearance, name='admin_clearance'),
    path('admin_clearance/<int:pk>/', views.admin_view_clearance_view, name='admin_view_clearance'),

    
    path('admin_goodmoral/', views.admin_goodmoral_view, name='admin_goodmoral'),
    path('admin_view_goodmoral/', views.admin_view_goodmoral_view, name='admin_view_goodmoral'),
    path("gmrf/batch-preview", views.batch_view_gmrf, name="batch_view_gmrf"),
    
    path('admin_view_violation/', views.admin_view_violation, name='admin_view_violation'),
    path('admin_violation/', views.admin_violation_view, name='admin_violation'),
    path('admin_violations/<int:violation_id>/apology/settled', views.mark_apology_settled, name='mark_apology_settled'),
    path('admin_old_violation/', views.admin_old_violation_view, name='admin_old_violation'),
    
    
    path('admin_student/', views.admin_student_view, name='admin_student'),
    



    
    ###-------------------ELECTION - admin
    path('admin_election/', views.admin_election_view, name='admin_election'),
    # Candidates (active-election scoped)
    path('admin_election/candidates/', views.get_candidates, name='admin_get_candidates'),                 # GET
    path('admin_election/candidates/add/', views.add_candidate, name='admin_add_candidate'),              # POST
    path('admin_election/candidates/<int:cid>/delete/', views.delete_candidate, name='admin_delete_candidate'),  # POST
    
    path('admin_election_results/', views.admin_election_results_view, name='admin_election_results'),
    path('api/admin/elections/', views.api_admin_elections_list, name='api_admin_elections_list'),  # <—         # dropdown source
    path('api/admin/results/', views.api_admin_results_data, name='api_admin_results_data'),      # data for one election

    
    path('admin_election_manage/', views.admin_election_manage_view, name='admin_election_manage'),
    # NEW actions for the manage page (no /admin/ prefix)
    path('admin_election/create/', views.admin_election_create, name='admin_election_create'),
    path('admin_election/<int:eid>/open_now/', views.admin_election_open_now, name='admin_election_open_now'),
    path('admin_election/<int:eid>/close_now/', views.admin_election_close_now, name='admin_election_close_now'),
    path('admin_election/<int:eid>/finalize/', views.admin_election_finalize, name='admin_election_finalize'),

    # Whitelist (TUP-ID only) upload + verify
    path('admin_election/<int:eid>/eligibles/upload/', views.eligibles_upload_view, name='eligibles_upload'),
    path('admin_election/<int:eid>/eligibles/verify/', views.eligibles_verify_view, name='eligibles_verify'),

    
     
    ###-------------------ELECTION - client
    path('client_election/', views.client_election_view, name='client_election'),
    path('client_view_election/', views.client_view_election_view, name='client_view_election'),
    path('api/eligibility/', views.api_check_eligibility, name='api_check_eligibility'),
    path('api/ballot/', views.api_get_ballot, name='api_get_ballot'),
    path('api/submit_vote/', views.api_submit_vote, name='api_submit_vote'),
    path('logout/', views.client_logout, name='client_logout'),
    
    
    
    
    
    
    
    ########################################client
    path('goodmoral/request/', views.goodmoral_request_form, name='goodmoral_request'),  
    path('id-surrender/', views.id_surrender_request, name='id_surrender_request'),

    
    
    ########################################admin
    path('upload_student_csv/', views.upload_student_csv, name='upload_student_csv'),
    path('request-otp/', views.request_otp, name='request_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('get-accounts/', views.get_accounts_data, name='get_accounts_data'),
    path('deactivate-account/<str:user_email>/', views.deactivate_account, name='deactivate_account'),
    path('lostandfound/ajax/delete/<int:item_id>/', views.ajax_delete_lostandfound, name='ajax_delete_lostandfound'),
    path('lostandfound/ajax/edit/<int:item_id>/', views.ajax_edit_lostandfound, name='ajax_edit_lostandfound'),
    path('scholarships/ajax/delete/<int:id>/', views.ajax_delete_scholarship, name='ajax_delete_scholarship'),
    path('scholarships/ajax/edit/<int:id>/', views.ajax_edit_scholarship, name='ajax_edit_scholarship'),
    path('api/scholarships/', views.scholarship_feed_api, name='scholarship_feed_api'),
    path('api/lostandfound/', views.lostandfound_feed_api, name='lostandfound_feed_api'),
    path('violation/<int:violation_id>/approve/', views.admin_approve_violation, name='admin_approve_violation'),
    path('violation/<int:violation_id>/decline/', views.admin_decline_violation, name='admin_decline_violation'),
    
    
    
    
    path('admin_goodmoral/<int:pk>/', views.admin_view_goodmoral, name='admin_view_goodmoral'),
    path('admin_goodmoral/<int:pk>/accept/', views.goodmoral_accept, name='goodmoral_accept'),
    path('admin_goodmoral/<int:pk>/decline/', views.goodmoral_decline, name='goodmoral_decline'),
    path('admin_goodmoral/<int:pk>/request-form/', views.goodmoral_request_form_pdf, name='goodmoral_request_form_pdf'),
    path("goodmoral/<int:pk>/view/", views.view_gmf, name="view_gmf"),
    path("admin_ackreq/<int:pk>/receipt.pdf", views.admin_ackreq_receipt_pdf, name="admin_ackreq_receipt_pdf"),
    path("admin_ackreq/<int:pk>/accept/",  views.admin_ackreq_accept,  name="admin_ackreq_accept"),
    path("admin_ackreq/<int:pk>/decline/", views.admin_ackreq_decline, name="admin_ackreq_decline"),
    

    
    ########################################guard
    path('get_student_by_id/<str:tupc_id>/', views.get_student_by_id, name='get_student_by_id'),
    path('submit/', views.submit_violation, name='submit_violation'),
    path('guard_report/download_pdf/', views.generate_guard_report_pdf, name='generate_guard_report_pdf'),




]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Prod (Render): explicitly serve media even when DEBUG=False
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': str(settings.MEDIA_ROOT)}),
]
