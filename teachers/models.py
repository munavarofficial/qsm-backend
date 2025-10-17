from django.db import models
from django.db import models
from django.utils import timezone
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import datetime
from datetime import date, datetime
from django.contrib.auth.hashers import make_password, check_password

def get_current_time():
    return datetime.now().time()

# Create your models here.
class Teacher(models.Model):
    name = models.CharField(max_length=50)
    father_name = models.CharField(max_length=50)
    blood_grp = models.CharField(max_length=10)
    msr_no = models.CharField(max_length=20)
    salary= models.CharField(max_length=10)
    joined_date = models.DateField()  # DateField for better date handling
    islamic_qualification = models.CharField(max_length=50)
    academic_qualification = models.CharField(max_length=50)
    other_occupation = models.CharField(max_length=50, blank=True, null=True)
    phone_no = models.CharField(max_length=12)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    image = models.ImageField(upload_to='teachers', blank=True, null=True)
    place = models.CharField(max_length=50)
    reg_no = models.CharField(max_length=10, unique=True)
    password = models.CharField(max_length=128)  # hashed password

    def __str__(self):
        return f"{self.name}, {self.place}"

    def save(self, *args, **kwargs):
        # Normalize fields to reduce login errors
        if self.name:
            self.name = self.name.strip().title()
        if self.reg_no:
            self.reg_no = self.reg_no.strip().upper()

        # Hash password if not hashed already
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)

        # Compress image if >200KB
        if self.image and hasattr(self.image, "size") and self.image.size > 200 * 1024:
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img_io = BytesIO()
            img.save(img_io, format="JPEG", quality=70, optimize=True)
            self.image = ContentFile(img_io.getvalue(), name=self.image.name)

        super().save(*args, **kwargs)
    # Check password securely
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class TeacherAttendance(models.Model):
    """Model representing a teacher's daily attendance record with AM and PM sessions."""

    ATTENDANCE_STATUS = (
        ('present', 'Present'),
        ('absent', 'Absent'),
    )

    SESSION_CHOICES = (
        ('AM', 'AM'),
        ('PM', 'PM'),
    )

    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name='attendance_records'
    )
    date = models.DateField(default=timezone.now)
    session = models.CharField(max_length=2, choices=SESSION_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='present')
    attendance_comments = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher.name} - {self.date} ({self.session}) - {self.status}"

    class Meta:
        unique_together = ('teacher', 'date', 'session')  # Ensure no duplicate attendance records per day and session
        ordering = ['-date', 'session']

    @staticmethod
    def calculate_daily_attendance(teacher, date):
        """Calculate the daily attendance score for a teacher."""
        records = TeacherAttendance.objects.filter(teacher=teacher, date=date)
        score = sum(0.5 for record in records if record.status == 'present')  # Simplified calculation
        return score



class Staff_Notification(models.Model):
    text = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='notification', null=True, blank=True)
    voice = models.FileField(upload_to='voice_notifications', null=True, blank=True)  # Optional voice file
    date = models.DateField(default=date.today)  # Use date.today() to get only the date part
    time = models.TimeField(default=get_current_time)  # Use callable function to get current time

    def __str__(self):
        return f"{self.date} - {self.text[:20]}"



class Staff_NotificationRead(models.Model):
    notification = models.ForeignKey(Staff_Notification, on_delete=models.CASCADE, related_name='read_statuses')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='read_notifications', null=True)  # Make teacher field nullable for now
    read_at = models.DateTimeField(auto_now_add=True)  # Automatically records the time it was marked as read

    def __str__(self):
        return f"{self.teacher.name} read '{self.notification.text[:20]}' at {self.read_at}"



class Replay_Staff_Notification(models.Model):
    replay=models.TextField()
    notification=models.ForeignKey(Staff_Notification, on_delete=models.CASCADE ,related_name='replay_status', null=True)
    teacher=models.ForeignKey(Teacher ,on_delete=models.CASCADE)
    replay_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher.name} read '{self.replay}' at {self.replay_at}"