from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Student Routes
    path('dashboard/', views.student_dashboard, name='student_dash'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('apply/<int:job_id>/', views.apply_now, name='apply_now'),
    
    # Admin Routes
    path('admin-dash/', views.admin_dashboard, name='admin_dash'),
    path('approve/<int:student_id>/', views.admin_approve_student, name='approve_student'),
    path('status-update/<int:app_id>/<str:new_status>/', views.update_application_status, name='update_status'),
    path('reject-registration/<int:student_id>/', views.admin_reject_student, name='reject_registration'),
    path('delete-announcement/<int:pk>/', views.delete_announcement, name='delete_announcement'),
    path('delete-drive/<int:pk>/', views.delete_drive, name='delete_drive'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-dash/verification/', views.verification_page, name='verification_page'),
    path('delete-broadcast/<int:broadcast_id>/', views.delete_broadcast, name='delete_broadcast'),
]