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
    
   
]
