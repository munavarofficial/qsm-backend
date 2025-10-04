from django.contrib import admin
from .models import Standard,StudentAttendance,Students,Subject,Term,Progress,DailyRoutine,Class_NotificationRead,Public_Notification,Public_NotificationRead,ClasswiseNotifications

# Register your models here.

admin.site.register(Standard)
admin.site.register(StudentAttendance)
admin.site.register(Students)
admin.site.register(Subject)
admin.site.register(Term)
admin.site.register(Progress)
admin.site.register(ClasswiseNotifications)
admin.site.register(Public_Notification)
admin.site.register(Public_NotificationRead)
admin.site.register(Class_NotificationRead)
admin.site.register(DailyRoutine)