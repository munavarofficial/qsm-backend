from django.urls import path
from .views import (student_login,get_csrf_token,get_student_by_id,student_logout,
                    get_all_student_attendance,
                    get_attendance_data,get_student_progressreport,
                    get_class_teacher,get_time_table,
                    get_exam_time_table,get_daily_routine,
                    get_attendance_by_class,mark_daily_routine,
                    get_public_notification,get_all_classes,
                    get_class_notification,mark_notification_as_read,mark_public_notification_as_read,
                    get_all_classs_with_details,get_class_teachers,get_attendance_by_class

                    )


urlpatterns = [
    path('csrf-token/',get_csrf_token,name='csrf-token'),
    path('login/',student_login,name='std-login'),
    path('logout/',student_logout,name='student-logout'),
    path('student_info_by_id/<int:student_id>/', get_student_by_id, name='studentInfo'),
    path('all-students-attendance/', get_all_student_attendance, name='students_attendance'),
    path('attendance-data/<int:student_id>/', get_attendance_data, name='get_attendance_data'),
    path('student-progress/<int:student_id>/', get_student_progressreport, name='get_student_progress'),
    path('class-teacher/<int:class_id>/', get_class_teacher, name='get_student_progress'),
    path('time-table/<int:class_id>/', get_time_table, name='time-table'),
    path('exam-time-table/<int:class_id>/', get_exam_time_table, name='exam-time-table'),
    path('get-attendnace-by-class/<int:class_id>/', get_attendance_by_class, name='attendance-class'),
    path('class-teacher/<int:class_id>/', get_class_teacher, name='get_student_progress'),
    path('public-notification/', get_public_notification, name='public-notification'),
    path('class-notification/<int:class_id>/',get_class_notification , name='public-notification'),
    path('read-clas-notification/<int:notification_id>/<int:student_id>/', mark_notification_as_read, name='mark-notification'),
    path('read-public-notification/<int:notification_id>/<int:student_id>/', mark_public_notification_as_read, name='mark-public-notification'),
    path('get-daily-routine/<int:student_id>/',get_daily_routine , name='daily-routine'),
    path('mark-daily-routine/<int:student_id>/',mark_daily_routine , name='mark-daily-routine'),
    path('classes/',get_all_classes , name='classes'),
    path('get-class-with-stds/',get_all_classs_with_details,name='all-class'),
]
