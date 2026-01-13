from django import forms
from .models import StudentProfile, JobPosting
from django.contrib.auth.models import User

class StudentUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['usn', 'phone', 'department', 'semester', 'cgpa', 'skills', 'resume']
    
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            if not resume.name.endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
        return resume

class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = '__all__'
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        
        