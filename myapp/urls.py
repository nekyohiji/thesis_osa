from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='client_home'),
    path('login/', views.login_view, name='login'),
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
    path('admin_view_goodmoral/', views.admin_view_goodmoral_view, name='admin_view_CS'),
    path('admin_view_violation/', views.admin_view_violation_view, name='admin_view_violation'),
    path('admin_violation/', views.admin_violation_view, name='admin_violation'),
    path('admin_student/', views.admin_student_view, name='admin_student'),
    
    
    
    ########################################admin
    
    path('upload_student_csv/', views.upload_student_csv, name='upload_student_csv'),
    
    ########################################guard
    path('get_student_by_id/<str:tupc_id>/', views.get_student_by_id, name='get_student_by_id'),

    
    
    
]
