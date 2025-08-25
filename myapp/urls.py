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
    path('guard_violation/', views.guard_violation_view, name='guard_violation'),
    path('guard_report/', views.guard_report_view, name='guard_report'),
    path('client_goodmoral/', views.client_goodmoral_view, name='client_goodmoral'),
    path('client_scholarships/', views.client_scholarships_view, name='client_scholarships'),
    path('client_CS/', views.client_CS_view, name='client_CS'),
    path('client_SurrenderingID/', views.client_SurrenderingID_view, name='client_SurrenderingID'),
    path('client_studentAssistantship/', views.client_studentAssistantship_view, name='client_studentAssistantship'),
    path('client_ACSO/', views.client_ACSO_view, name='client_ACSO'),
    path('client_lostandfound/', views.client_lostandfound_view, name='client_lostandfound'),
    path('client_view_election/', views.client_view_election_view, name='client_view_election'),
    path('client_election/', views.client_election_view, name='client_election'),
    path('client_view_CS/', views.client_view_CS_view, name='client_view_CS'),
    path('client_clearance/', views.client_clearance_view, name='client_clearance'),
    path("clearance/", views.clearance_request_view, name="clearance_request"),

    
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin_accounts/', views.admin_accounts_view, name='admin_accounts'),
    # --- name edit ---
    path('edit-account/<str:user_email>/', views.edit_account, name='edit_account'),

    # --- email change (OTP → verify → apply) ---
    path('email-change/request/', views.email_change_request, name='email_change_request'),
    path('email-change/verify/',  views.email_change_verify,  name='email_change_verify'),
    path('email-change/apply/',   views.email_change_apply,   name='email_change_apply'),

    # --- password change (OTP required) ---
    path('password-otp/request/', views.password_otp_request, name='password_otp_request'),
    path('password-otp/verify/',  views.password_otp_verify,  name='password_otp_verify'),
    path('change-password/<str:email>/', views.change_password, name='change_password'),
    
    
    path('admin_ackreq/', views.admin_ackreq_view, name='admin_ackreq'),
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
    
    path('admin_election/', views.admin_election_view, name='admin_election'),
    
    path('admin_lostandfound/', views.admin_lostandfound_view, name='admin_lostandfound'),
    path('admin_report/', views.admin_report_view, name='admin_report'),
    path('admin_scholarships/', views.admin_scholarships_view, name='admin_scholarships'),
    path('admin_view_ackreq/<int:pk>/', views.admin_view_ackreq_view, name='admin_view_ackreq'),
    
    path('admin_clearance/', views.admin_clearance, name='admin_clearance'),
    path('admin_clearance/<int:pk>/', views.admin_view_clearance_view, name='admin_view_clearance'),
    
    path('admin_goodmoral/', views.admin_goodmoral_view, name='admin_goodmoral'),
    path('admin_view_goodmoral/', views.admin_view_goodmoral_view, name='admin_view_goodmoral'),
    
    path('admin_view_violation/', views.admin_view_violation, name='admin_view_violation'),
    path('admin_violation/', views.admin_violation_view, name='admin_violation'),
    path('admin_violations/<int:violation_id>/apology/settled', views.mark_apology_settled, name='mark_apology_settled'),
    path('admin_old_violation/', views.admin_old_violation_view, name='admin_old_violation'),
    
    
    path('admin_student/', views.admin_student_view, name='admin_student'),
    path('admin_removedstud/', views.admin_removedstud_view, name='admin_removedstud'),
    path('admin_election_manage/', views.admin_election_manage_view, name='admin_election_manage'),
    path('admin_election_results/', views.admin_election_results_view, name='admin_election_results'),
    



    
    
    
    
    
    
    
    
    
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
    




    #########################################elections
    path('add-candidate/', views.add_candidate, name='add_candidate'),
    path('get-candidates/', views.get_candidates, name='get_candidates'),
    path('delete-candidate/<int:candidate_id>/', views.delete_candidate, name='delete_candidate'),
    path('get-academic-years/', views.get_academic_years, name='get_academic_years'),
    
    
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
