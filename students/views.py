from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import (StudentSerializer,DailyRoutineSerializer,
                          PublicNotificationSerializer,ClassNotificationSerializer)
from .models import (Students,StudentAttendance,Progress,DailyRoutine,
                     Public_Notification,ClasswiseNotifications,
                     Class_NotificationRead,Public_NotificationRead)
from students.models import Standard
import logging
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from teachers.serializers import TeacherSerializer
from datetime import date
import datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view ,authentication_classes, permission_classes
from rest_framework import status
from .models import DailyRoutine, Students
from .serializers import DailyRoutineSerializer
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from django.views.decorators.csrf import ensure_csrf_cookie,csrf_protect
from django.middleware.csrf import get_token
from django.http import JsonResponse
from rest_framework import status  # ✅ Import status from DRF

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})

@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_classes(request):
    classes = Standard.objects.all().values('id', 'std')
    return Response(list(classes), safe=False)

@csrf_protect
@permission_classes([AllowAny])
@api_view(['POST'])
def student_login(request):
    if request.method == 'POST':
        try:
            reg_no = request.data.get('reg_no', '').strip()
            password = request.data.get('password', '').strip()

            if not reg_no or not password:
                return Response(
                {'error': 'Registration number and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            # ✅ Use .filter().first() to avoid exceptions
            student = Students.objects.filter(reg_no__iexact=reg_no).first()

            if not student or not student.check_password(password):
                # Always same error → prevents user enumeration
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


            # ✅ Prevent session fixation
            request.session.flush()
            request.session['student_session_id'] = student.id
            request.session['is_authenticated'] = True

            # ✅ Student details
            student_data = {
                'id': student.id,
                'name': student.name,
                'gender': student.gender,
                'parent_name': student.parent_name,
                'parent_occupation': student.parent_occupation,
                'address': student.address,
                'std': student.std.id,  # Send only ID
                'former_school': student.former_school,
                'admission_no': student.admission_no,
                'admission_date': student.admission_date,
                'phone_no': student.phone_no,
                'place': student.place,
                'image': student.image.url if student.image else None,
            }
            return Response({'student': student_data}, status=200)

        except Exception as e:
            print(f"[LOGIN ERROR] {str(e)}")
            return Response({'error': f'An error occurred: {str(e)}'}, status=500)

    return Response({'error': 'Method not allowed'}, status=405)


@csrf_protect
def student_logout(request):
    if request.method == 'POST':
        if 'student_session_id' in request.session:
            request.session.flush()
        return JsonResponse({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)  # ✅ Now works

    return Response({'error': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)  # ✅ Now works




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_class_teacher(request, class_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    std = get_object_or_404(Standard, id=class_id)

    # Retrieve the class teacher
    class_teacher = std.class_teacher
    print('result is',class_teacher,class_id)
    if class_teacher:
        # Serialize the full teacher details
        teacher_serializer = TeacherSerializer(class_teacher)
        return Response(teacher_serializer.data, status=200)
    else:
        return Response({"error": "Class teacher not assigned"}, status=404)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_student_by_id(request, student_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Attempt to retrieve the student by ID
        student = Students.objects.get(id=student_id)
        # Serialize the student data
        serializer = StudentSerializer(student)
        return Response({"student": serializer.data}, status=status.HTTP_200_OK)

    except Students.DoesNotExist:
        # Return a 404 if the student does not exist
        raise NotFound(detail="Student not found")



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_all_student_attendance(request):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    class_id = request.query_params.get('class_id')
    student_id = request.query_params.get('student_id')
    selected_year = request.query_params.get('year')
    selected_month = request.query_params.get('month')

    # Ensure class_id and student_id are provided
    if not class_id or not student_id:
        return Response({"error": "Both class_id and student_id are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch the class and student
        standard = get_object_or_404(Standard, id=class_id)
        student = get_object_or_404(Students, id=student_id, std=standard)

        # Fetch attendance records for the student
        attendance_records = StudentAttendance.objects.filter(student=student).order_by('-date')
        print(attendance_records)
        # Apply date filtering if year and month are provided
        if selected_year:
            attendance_records = attendance_records.filter(date__year=selected_year)

        if selected_month and selected_month != 'all':
            attendance_records = attendance_records.filter(date__month=selected_month)

        # Check if records exist
        if not attendance_records.exists():
            return Response({"message": "No attendance records found."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare the data to return
        attendance_data = [
            {
                "date": record.date.strftime("%Y-%m-%d"),
                "status": record.status,
                "remarks": record.remarks or 'None',
            }
            for record in attendance_records
        ]

        return Response({
            "student_id": student.id,
            "name": student.name,
            "attendance_records": attendance_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

logger = logging.getLogger(__name__)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_attendance_data(request, student_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch student by ID
        student = get_object_or_404(Students, id=student_id)

        # Fetch attendance records associated with the student
        attendance_records = student.attendance_records.all()

        # Prepare attendance data for response
        attendance_data = [
            {
                "date": record.date.strftime("%Y-%m-%d"),  # Formatting date
                "status": record.status,
                "remarks": record.remarks
            }
            for record in attendance_records
        ]

        # Return the response with student ID and attendance records
        return Response({
            "student_id": student.id,
            "attendance_record": attendance_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error("Error occurred while fetching attendance data: %s", str(e))
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_student_progressreport(request, student_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    if not student_id:
        return Response({'error': 'Student ID not provided'}, status=400)

    try:
        student = Students.objects.get(id=student_id)
        progresses = Progress.objects.filter(student=student)

        if not progresses.exists():
            return Response({'error': 'No exams found for this student'}, status=404)

        report = {
            'student_name': student.name,
            'student_id': student.id,
            'class': student.std.std,
            'progress_report': [
                {
                    'subject_name': progress.subject.name,
                    'marks': progress.marks,
                    'term_name': progress.term.name,
                    'term_year': progress.term.year
                }
                for progress in progresses
            ]
        }
        return Response(report)
    except Students.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)





@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_time_table(request, class_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        standard = Standard.objects.get(id=class_id)
        timetable_url = standard.time_table.url if standard.time_table else None
        return Response({'class': standard.std, 'timetable_url': timetable_url})
    except Standard.DoesNotExist:
        return Response({'error': 'Class not found'}, status=404)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_exam_time_table(request, class_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        standard = Standard.objects.get(id=class_id)
        timetable_url = standard.exam_time_table.url if standard.exam_time_table else None
        return Response({'class': standard.std, 'timetable_url': timetable_url})
    except Standard.DoesNotExist:
        return Response({'error': 'Class not found'}, status=404)







@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_class_teachers(request, class_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    # Get the Standard object or return a 404 error if not found
    std = get_object_or_404(Standard, id=class_id)

    # Retrieve the class teacher
    class_teacher = std.class_teacher
    print('result is',class_teacher,class_id)
    if class_teacher:
        # Serialize the full teacher details
        teacher_serializer = TeacherSerializer(class_teacher)
        return Response(teacher_serializer.data, status=200)
    else:
        return Response({"error": "Class teacher not assigned"}, status=404)




@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_attendance_by_class(request, class_id):
    if request.session.get("is_authenticated"):
        student_session_id = request.session.get('student_session_id')
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    standard = get_object_or_404(Standard, id=class_id)
    today = date.today()

    attendance_records = StudentAttendance.objects.filter(
        student__std=standard,
        date=today
    )

    present_students = [
        {"name": r.student.name, "image": r.student.image.url if r.student.image else None}
        for r in attendance_records if r.status == "present"
    ]
    absent_students = [
        {"name": r.student.name, "image": r.student.image.url if r.student.image else None}
        for r in attendance_records if r.status == "absent"
    ]

    # ✅ Class status logic (day-wise)
    if standard.last_completed_date == today:
        class_status = "Class Completed"
    elif attendance_records.exists():
        class_status = "Class Going On"
    else:
        class_status = "Class Not Started"

    return Response({
        "class": standard.std,
        "class_status": class_status,
        "date": today,
        "present_students": present_students,
        "absent_students": absent_students,
    })




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_classs_with_details(request):
    if request.session.get("is_authenticated"):
        student_session_id = request.session.get('student_session_id')
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        classes = (
            Standard.objects.prefetch_related('students')
            .select_related('class_teacher')
            .order_by('std')  # 👈 This line ensures fixed order 1,2,3,4...
        )

        data = [
            {
                "id": standard.id,
                "class": standard.std,
                "class_teacher": standard.class_teacher.name if standard.class_teacher else None,
                "students": [
                    {
                        "id": student.id,
                        "name": student.name,
                        "image": student.image.url if student.image and hasattr(student.image, 'url') else None,
                        "gender": student.gender,
                        "parent_name": student.parent_name,
                        "address": student.address,
                        "admission_no": student.admission_no,
                        "phone_no": student.phone_no,
                        "blood_grp": getattr(student, 'blood_grp', None),
                        "place": student.place,
                    }
                    for student in standard.students.all()
                ],
            }
            for standard in classes
        ]

        return Response(data)

    except Exception as e:
        # log the exact error to console
        return Response({"error": str(e)}, status=500)





@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_public_notification(request):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Retrieve all public notifications, ordered by 'date' (latest first) and 'time' (latest first)
        public_notifications = Public_Notification.objects.all().order_by('-date', '-time')

        # Serialize the ordered notifications
        serializer = PublicNotificationSerializer(public_notifications, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Public_Notification.DoesNotExist:
        # If no notifications exist, return an appropriate message
        return Response(
            {"error": "No public notifications found."},
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        # Catch any other exceptions and return an error message
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_class_notification(request, class_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    # Retrieve the class (Standard) or return a 404 if it doesn't exist
    standard = get_object_or_404(Standard, id=class_id)

    # Retrieve all notifications related to the class
    notifications = standard.class_notifications.all().order_by('-date', '-time')  # Use .all() to fetch the related notifications

    # Serialize the notifications
    serializer = ClassNotificationSerializer(notifications, many=True)

    return Response({'class': standard.std, 'notifications': serializer.data})



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def mark_notification_as_read(request, notification_id, student_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Validate teacher existence
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({'error': 'student not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Validate notification existence
        notification = ClasswiseNotifications.objects.get(id=notification_id)

        # Mark notification as read (assuming Staff_NotificationRead exists)
        Class_NotificationRead.objects.get_or_create(notification=notification, student=student)
        return Response({'message': 'Notification marked as read.'}, status=status.HTTP_200_OK)

    except ClasswiseNotifications.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def mark_public_notification_as_read(request, notification_id, student_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Validate teacher existence
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({'error': 'student not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Validate notification existence
        notification = Public_Notification.objects.get(id=notification_id)

        # Mark notification as read (assuming Staff_NotificationRead exists)
        Public_NotificationRead.objects.get_or_create(notification=notification, student=student)
        return Response({'message': 'Notification marked as read.'}, status=status.HTTP_200_OK)

    except Public_Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)




@permission_classes([AllowAny])  # Adjust permissions as needed
@authentication_classes([SessionAuthentication])  # Use session-based authentication
@api_view(['GET'])
def get_daily_routine(request, student_id):
    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    selected_date = request.GET.get("date")
    if not selected_date:
        selected_date = date.today().isoformat()  # Defaults to today's date in YYYY-MM-DD format

    print('Selected date is', selected_date)

    daily_routines = DailyRoutine.objects.filter(student=student, date=selected_date)

    if not daily_routines.exists():
        return Response([], status=status.HTTP_200_OK)  # Return empty list if no data

    serializer = DailyRoutineSerializer(daily_routines, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def mark_daily_routine(request, student_id):

    if request.session.get("is_authenticated"):
        student_session_id = request.session.get("student_session_id")
        if not student_session_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Ensure the student exists
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    # Validate data sent in the request
    routine_data = request.data
    daily_routine, created = DailyRoutine.objects.get_or_create(
        student=student,
        date=datetime.date.today()  # Use today's date
    )

    # Update the existing or new record with the submitted data
    for field in [
        "subahi", "luhur", "asar", "maqrib", "isha",
        "thabaraka", "waqiha", "swalath", "haddad"
    ]:
        if field in routine_data:
            setattr(daily_routine, field, routine_data[field])

    daily_routine.save()

    return Response(DailyRoutineSerializer(daily_routine).data, status=status.HTTP_200_OK)


