from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from .models import StudentProfile, JobPosting, Application, Announcement
from .forms import StudentUserForm, ProfileForm
from .utils import (
    send_sms, 
    format_phone_e164, 
    notify_student_approval,
    notify_student_rejection,
    notify_application_update
)

# Helper function for E.164 phone formatting (kept for backward compatibility)
def format_phone_e164(phone):
    """Convert phone to E.164 format (e.g., +91767619xxxx)."""
    from .utils import format_phone_e164 as util_format
    return util_format(phone)

# --- 1. GENERAL VIEWS ---

def home(request):
    """Landing page of the portal."""
    return render(request, 'portal/home.html')

class CustomLoginView(LoginView):
    """Custom login handling with role-based redirection."""
    template_name = 'portal/login.html'

    def get_success_url(self):
        if self.request.user.is_staff:
            return '/admin-dash/' 
        return '/dashboard/'

def logout_view(request):
    """Logs out user and returns to home."""
    logout(request)
    return redirect('home')


# --- 2. STUDENT VIEWS ---

def register(request):
    """Handles student account creation and profile setup."""
    if request.method == 'POST':
        u_form = StudentUserForm(request.POST)
        p_form = ProfileForm(request.POST, request.FILES)
        if u_form.is_valid() and p_form.is_valid():
            user = u_form.save(commit=False)
            user.set_password(u_form.cleaned_data['password'])
            user.is_active = False # Deactivated until Admin approval
            user.save()
            profile = p_form.save(commit=False)
            profile.user = user
            profile.save()
            return render(request, 'portal/registration_success.html')
    else:
        u_form = StudentUserForm()
        p_form = ProfileForm()
    return render(request, 'portal/register.html', {'u_form': u_form, 'p_form': p_form})

@login_required
def student_dashboard(request):
    """Main student dashboard showing eligible drives and status."""
    profile = get_object_or_404(StudentProfile, user=request.user)
    if not profile.is_approved:
        return render(request, 'portal/pending_notice.html')
        
    jobs = JobPosting.objects.filter(
        min_cgpa__lte=profile.cgpa,
        deadline__gte=timezone.now()
    ).order_by('-posted_date')
    
    my_applications = Application.objects.filter(student=profile).order_by('-applied_on')
    announcements = Announcement.objects.all().order_by('-posted_on')[:5]
    
    return render(request, 'portal/student_dash.html', {
        'jobs': jobs, 
        'profile': profile,
        'announcements': announcements,
        'my_applications': my_applications,
    })

@login_required
def edit_profile(request):
    """Allows students to update their profile and resume."""
    profile = get_object_or_404(StudentProfile, user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_dash')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'portal/edit_profile.html', {'form': form})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import StudentProfile, JobPosting, Application

@login_required
def apply_now(request, job_id):
    """Handles student application with real-time eligibility checking."""
    profile = get_object_or_404(StudentProfile, user=request.user)
    job = get_object_or_404(JobPosting, id=job_id)

    # 1. Security Check: Only approved students can apply
    if not profile.is_approved:
        messages.error(request, "Your account is pending admin approval.")
        return redirect('student_dash')

    # 2. Eligibility Logic: Determine Qualification Summary
    # You can expand this logic to check for backlogs or department
    if profile.cgpa >= job.min_cgpa:
        eligibility_status = "✅ Eligible"
    else:
        eligibility_status = "⚠️ Low CGPA"

    # 3. Save Application: Use get_or_create to prevent duplicate entries
    # We store the eligibility_notes so the admin sees the status immediately
    app, created = Application.objects.get_or_create(
        student=profile, 
        job=job,
        defaults={'eligibility_notes': eligibility_status}
    )

    if not created:
        messages.info(request, f"You have already applied for {job.company}.")
        return redirect('student_dash')

    # 4. Success: Redirect to success page with the status notes
    return render(request, 'portal/apply_success.html', {
        'job': job,
        'notes': eligibility_status
    })

# --- 3. COMPREHENSIVE ADMIN DASHBOARD ---

@login_required
def admin_dashboard(request):
    """Central Admin dashboard with filtering, posting, and stats."""
    if not request.user.is_staff:
        return redirect('student_dash')

    # Capture Filter Parameters
    dept_filter = request.GET.get('dept', '')
    sem_filter = request.GET.get('sem', '')
    company_filter = request.GET.get('company', '')

    # HANDLE POST ACTIONS
    if request.method == 'POST':
        if 'send_announcement' in request.POST:
            title = request.POST.get('title')
            msg = request.POST.get('message')
            Announcement.objects.create(title=title, message=msg)
            messages.success(request, "Announcement published successfully!")
            
        elif 'add_drive' in request.POST:
            drive_id = request.POST.get('drive_id')
            data = {
                'title': request.POST.get('title'),
                'company': request.POST.get('company'),
                'description': request.POST.get('description'),
                'min_cgpa': request.POST.get('min_cgpa'),
                # FIXED: Mapping 'depts' from form to 'eligible_depts'
                'deadline': request.POST.get('deadline'),
                'job_type': request.POST.get('type'),
                'package_range': request.POST.get('package_range'),
                'official_link': request.POST.get('official_link'),
            }
            
            if drive_id:
                JobPosting.objects.filter(id=drive_id).update(**data)
                messages.success(request, "Drive updated successfully!")
            else:
                # FIXED: UnboundLocalError avoided by keeping logic in block
                JobPosting.objects.create(**data)
                messages.success(request, "New drive has been added!")
        
        return redirect('admin_dash') 

    # STATISTICS
    stats = {
        'total_students': StudentProfile.objects.count(),
        'pending_approvals': StudentProfile.objects.filter(is_approved=False).count(),
        'active_drives': JobPosting.objects.filter(deadline__gte=timezone.now()).count(),
        'total_apps': Application.objects.count(),
    }

    # APPLY FILTERS TO APPLICATIONS
    applications = Application.objects.all().order_by('-applied_on')
    if dept_filter:
        applications = applications.filter(student__department__icontains=dept_filter)
    if sem_filter:
        applications = applications.filter(student__semester=sem_filter)
    if company_filter:
        applications = applications.filter(job__company__icontains=company_filter)

    # APPLY FILTERS TO STUDENT LISTING
    students = StudentProfile.objects.all().order_by('-is_approved', 'user__first_name')
    if dept_filter:
        students = students.filter(department__icontains=dept_filter)
    if sem_filter:
        students = students.filter(semester=sem_filter)

    all_drives = JobPosting.objects.all().order_by('-posted_date')
    all_announcements = Announcement.objects.all().order_by('-posted_on')

    return render(request, 'admin/dashboard.html', {
        'stats': stats,
        'students': students,
        'applications': applications,
        'all_drives': all_drives,
        'all_announcements': all_announcements,
        'dept_filter': dept_filter,
        'sem_filter': sem_filter,
        'company_filter': company_filter,
    })

@login_required
def delete_broadcast(request, broadcast_id):
    if not request.user.is_staff:  # Security check to ensure only Admins can delete
        return redirect('student_dash')
        
    broadcast = get_object_or_404(Announcement, id=broadcast_id)
    broadcast.delete()
    messages.success(request, "Broadcast deleted successfully.")
    return redirect('admin_dash')
# --- 4. ADMIN ACTIONS & SMS NOTIFICATIONS ---

@login_required
def admin_approve_student(request, student_id):
    """Approves a student account and notifies them via SMS."""
    if not request.user.is_staff: 
        return redirect('login')
    
    profile = get_object_or_404(StudentProfile, id=student_id)
    profile.is_approved = True
    profile.user.is_active = True
    profile.user.save()
    profile.save()
    
    # SMS notification with improved error handling
    try:
        notify_student_approval(profile)
        messages.success(request, f"Student approved and SMS sent to {format_phone_e164(profile.phone)}")
    except Exception as e:
        messages.warning(request, f"Student approved successfully, but SMS notification failed: {str(e)}")

    return redirect('admin_dash')

@login_required
def admin_reject_student(request, student_id):
    """Rejects registration and deletes user account."""
    if not request.user.is_staff: 
        return redirect('login')
    
    profile = get_object_or_404(StudentProfile, id=student_id)
    
    # Send rejection SMS before deleting
    try:
        notify_student_rejection(profile)
    except Exception as e:
        # Log but don't fail - SMS is secondary to account deletion
        pass
        
    profile.user.delete() 
    messages.error(request, "Registration rejected and account deleted.")
    return redirect('admin_dash')

@login_required
def update_application_status(request, app_id, new_status):
    """Updates job application status and notifies student via SMS."""
    if not request.user.is_staff: 
        return redirect('student_dash')
    
    app = get_object_or_404(Application, id=app_id)
    app.status = new_status
    app.save()
    
    # Send notification with improved error handling
    try:
        notify_application_update(app)
        messages.success(request, "Status updated and student notified via SMS.")
    except Exception as e:
        messages.warning(request, f"Status updated successfully, but SMS notification failed: {str(e)}")
        
    return redirect('admin_dash')

@login_required
def delete_announcement(request, pk):
    """Removes a global announcement."""
    if not request.user.is_staff: return redirect('home')
    ann = get_object_or_404(Announcement, pk=pk)
    ann.delete()
    messages.info(request, "Announcement deleted.")
    return redirect('admin_dash')

@login_required
def delete_drive(request, pk):
    """Removes an active job drive."""
    if not request.user.is_staff: return redirect('home')
    drive = get_object_or_404(JobPosting, pk=pk)
    drive.delete()
    messages.info(request, "Drive deleted.")
    return redirect('admin_dash')

@login_required
def verification_page(request):
    """Dedicated page for student verification queue."""
    if not request.user.is_staff:
        return redirect('student_dash')

    # Fetch students, prioritizing those not yet approved
    students = StudentProfile.objects.all().order_by('is_approved', 'user__first_name')
    
    return render(request, 'admin/verification_queue.html', {
        'students': students,
    })

@login_required
def apply_now(request, job_id):
    profile = get_object_or_404(StudentProfile, user=request.user)
    job = get_object_or_404(JobPosting, id=job_id)
    
    if profile.is_approved:
        # Create Application
        app, created = Application.objects.get_or_create(
            student=profile, 
            job=job
        )
        
        if not created:
            messages.info(request, "You have already applied for this drive.")
        else:
            messages.success(request, "Application submitted successfully!")
            return render(request, 'portal/apply_success.html')
            
    return redirect('student_dash')