from django.urls import path
from . import views

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
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin_accounts/', views.admin_accounts_view, name='admin_accounts'),
    path('admin_ackreq/', views.admin_ackreq_view, name='admin_ackreq'),
    path('admin_ACSO/', views.admin_ACSO_view, name='admin_ACSO'),
    path('admin_assistantship/', views.admin_assistantship_view, name='admin_assistantship'),
    path('admin_CS/', views.admin_CS_view, name='admin_CS'),
    path('admin_election/', views.admin_election_view, name='admin_election'),
    path('admin_goodmoral/', views.admin_goodmoral_view, name='admin_goodmoral'),
    path('admin_lostandfound/', views.admin_lostandfound_view, name='admin_lostandfound'),
    path('admin_report/', views.admin_report_view, name='admin_report'),
    path('admin_scholarships/', views.admin_scholarships_view, name='admin_scholarships'),
    path('admin_view_ackreq/', views.admin_view_ackreq_view, name='admin_view_ackreq'),
    path('admin_view_CS/', views.admin_view_CS_view, name='admin_view_CS'),
    path('admin_view_goodmoral/', views.admin_view_goodmoral_view, name='admin_view_goodmoral'),
    path('admin_view_violation/', views.admin_view_violation, name='admin_view_violation'),
    path('admin_violation/', views.admin_violation_view, name='admin_violation'),
    path('admin_student/', views.admin_student_view, name='admin_student'),
    path('admin_removedstud/', views.admin_removedstud_view, name='admin_removedstud'),
    path('admin_election_manage/', views.admin_election_manage_view, name='admin_election_manage'),
    path('admin_election_results/', views.admin_election_results_view, name='admin_election_results'),
    
    
    
    
    
    
    
    
    
    
    
    
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
    path('settlement/<int:settlement_id>/settle/', views.mark_settlement_as_settled, name='mark_settlement_as_settled'),

    ##########################################elections
    path('add-candidate/', views.add_candidate, name='add_candidate'),
    path('get-candidates/', views.get_candidates, name='get_candidates'),
    path('delete-candidate/<int:candidate_id>/', views.delete_candidate, name='delete_candidate'),
    path('get-academic-years/', views.get_academic_years, name='get_academic_years'),
    
    
    ########################################guard
    path('get_student_by_id/<str:tupc_id>/', views.get_student_by_id, name='get_student_by_id'),
    path('submit/', views.submit_violation, name='submit_violation'),
    path('guard_report/download_pdf/', views.generate_guard_report_pdf, name='generate_guard_report_pdf'),
    
    
]
