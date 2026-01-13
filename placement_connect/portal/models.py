from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    usn = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=100)
    semester = models.IntegerField(default=1)
    cgpa = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(10.0)])
    skills = models.TextField()
    resume = models.FileField(upload_to='resumes/')
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.usn})"

class JobPosting(models.Model):
    TYPE_CHOICES = [
        ('Job', 'Placement'), 
        ('Internship', 'Internship'), 
        ('Drive', 'Placement Drive')
    ]
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    package_range = models.CharField(max_length=100, help_text="e.g. 5 LPA - 8 LPA", blank=True, null=True)
    official_link = models.URLField(max_length=500, blank=True, null=True, help_text="Link to company's career page")
    min_cgpa = models.FloatField()
    deadline = models.DateTimeField()
    posted_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Application(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='Applied')
    applied_on = models.DateTimeField(auto_now_add=True)
    eligibility_notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.student.user.username} -> {self.job.title} ({self.status})"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    posted_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title