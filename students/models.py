from django.db import models
from django.utils import timezone
from teachers.models import Teacher
from datetime import date, datetime
from datetime import datetime, date
from django.db import models
from datetime import date, datetime
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password, check_password


class Standard(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Class Not Started'),
        ('ongoing', 'Class Going On'),
        ('ended', 'Class Ended'),
    ]
    std = models.CharField(max_length=20, unique=True ,help_text="Name of the class or grade (e.g., '5th Grade', '10th Grade')")
    time_table = models.ImageField(upload_to='time-tables', null=True, blank=True, help_text="Upload the class's timetable")
    exam_time_table = models.ImageField(upload_to='exam-time-tables', null=True, blank=True, help_text="Upload the exam timetable for this class")
    last_completed_date = models.DateField(null=True, blank=True)

    class_teacher = models.ForeignKey(
        Teacher,
        related_name='class_charges',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The teacher assigned as the class in-charge"
    )

    def __str__(self):
        return f"{self.std}"

    class Meta:
        verbose_name_plural = "Standards"


# Students Model
class Students(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    parent_name = models.CharField(max_length=50)
    parent_occupation = models.CharField(max_length=50)
    address = models.TextField()
    std = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='students')
    former_school = models.CharField(max_length=50, blank=True, null=True)
    admission_no = models.CharField(max_length=20, unique=True)
    admission_date = models.CharField(max_length=50)
    image = models.ImageField(upload_to='students', blank=True, null=True)
    phone_no = models.CharField(max_length=12)
    place = models.CharField(max_length=50)
    reg_no = models.CharField(max_length=10, unique=True)
    password=models.CharField(max_length=128 )

    def __str__(self):
        return f"{self.name},{self.std} {self.place}"

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

# Student Attendance Model
class StudentAttendance(models.Model):
    ATTENDANCE_STATUS = (
        ('present', 'Present'),
        ('absent', 'Absent'),
    )

    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='present')
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date']

# Subject Model
class Subject(models.Model):
    name = models.CharField(max_length=100)
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='subjects')

    def __str__(self):
        return f"class {self.standard.std} - {self.name}"

    class Meta:
        verbose_name_plural = "Subjects"
        ordering = ['name']

# Term Model
class Term(models.Model):
    name = models.CharField(max_length=50)  # E.g., "Term 1", "Term 2"
    year = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} - {self.year}"

    class Meta:
        unique_together = ('name', 'year')  # Ensure unique term names per year
        ordering = ['-year', 'name']  # Order by year descending and name ascending


class Progress(models.Model):
    """Model representing a student's marks in a subject during a particular term."""
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='exams_result')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    marks = models.FloatField()

    class Meta:
        unique_together = ('student', 'subject', 'term')
        ordering = ['-term__year', '-term__name', 'subject']
        verbose_name_plural = "Progress Records"

    def __str__(self):
        return f"{self.student.name} -  {self.term.name}-{self.term.year} - {self.subject.name} : {self.marks} marks"


# Function to get the current time (returns a time object)
def get_current_time():
    return datetime.now().time()

class Public_Notification(models.Model):
    text = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='notification', null=True, blank=True)
    voice = models.FileField(upload_to='voice_notifications', null=True, blank=True)  # Optional voice file
    date = models.DateField(default=date.today)  # Use date.today() to get only the date part
    time = models.TimeField(default=get_current_time)  # Use callable function to get current time

    def __str__(self):
        return f"{self.date} - {self.text[:20]}"


class Public_NotificationRead(models.Model):
    notification = models.ForeignKey(Public_Notification, on_delete=models.CASCADE, related_name='read_statuses_public')
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='read_notifications_public', null=True)  # Make teacher field nullable for now
    read_at = models.DateTimeField(auto_now_add=True)  # Automatically records the time it was marked as read


    def __str__(self):
        return f"{self.student.name} read '{self.notification.text[:20]}' at {self.read_at}"




class ClasswiseNotifications(models.Model):
    std_id = models.ForeignKey(Standard, on_delete=models.CASCADE, null=True ,related_name='class_notifications')
    text = models.TextField()
    image = models.CharField(max_length=100, blank=True, null=True)
    voice = models.CharField(max_length=100, blank=True, null=True)

    # Use a method to get the current time
    def get_current_time():
        return timezone.localtime(timezone.now()).time()

    # Use the method in the default value
    time = models.TimeField(default=get_current_time)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f'Notification for {self.std_id}'



class Class_NotificationRead(models.Model):
    notification = models.ForeignKey(ClasswiseNotifications, on_delete=models.CASCADE, related_name='read_statuses_class')
    student = models.ForeignKey(Students, on_delete=models.CASCADE, related_name='read_notifications_class', null=True)  # Make teacher field nullable for now
    read_at = models.DateTimeField(auto_now_add=True)  # Automatically records the time it was marked as read


    def __str__(self):
        return f"{self.student.name} read '{self.notification.text[:20]}' at {self.read_at}"



class DailyRoutine(models.Model):
    student = models.ForeignKey("Students", on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)  # Track attendance by date
    subahi = models.BooleanField(default=False)
    luhur = models.BooleanField(default=False)
    asar = models.BooleanField(default=False)
    maqrib = models.BooleanField(default=False)
    isha = models.BooleanField(default=False)
    thabaraka = models.BooleanField(default=False)
    waqiha = models.BooleanField(default=False)
    swalath = models.BooleanField(default=False)
    haddad = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name}'s Routine on {self.date}"
