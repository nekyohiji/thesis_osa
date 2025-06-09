from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='client_home'),
    path('login/', views.login_view, name='login'),
    path('guard_violation/', views.guard_violation_view, name='guard_violation'),
    path('guard_report/', views.guard_report_view, name='guard_report'),
    
   
]
