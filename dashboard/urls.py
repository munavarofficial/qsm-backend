from django.urls import path
from . import views

urlpatterns = [
    path("school-details/", views.get_school_details ,name='school-name'),
    path('all-students-count/',views.get_students_count,name='students-count'),
    path('all-teachers-count/',views.get_teachers_count,name='teacher-count'),
    path('get-notice/',views.get_notice,name='get-notice'),
    path('attendance-summery/',views.get_attendance_summary,name='attendnace-summery'),
    path('class-attendance-summery/<int:class_id>/',views.class_attendance_summary,name='attendnace-summery'),
    path('get-attendance-topers/',views.get_top_students_in_attendance,name='attendance-topers'),
    path('get-exam-topers/',views.get_top_scorers,name='attendance-topers'),
    path('get-all-classes/',views.get_all_classes,name='classes'),
    path('routine-topers/',views.get_top_students_in_daily_routine,name='routine-topers'),
    path('committee/',views.get_committee,name='committee'),
    path('all-teachers-only/',views.get_all_teachers_only,name='all-tchr-only'),
    path('memorial/',views.get_memorial,name='memorial'),
    path('gallery/',views.get_gallery,name='gallery'),
    path('numbers/',views.get_numbers,name='numbers'),

]
