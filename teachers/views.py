from rest_framework.decorators import api_view,authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie,csrf_protect,csrf_exempt
from django.middleware.csrf import get_token
import logging
from django.utils import timezone
from rest_framework.exceptions import NotFound
import json
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from .models import (
    Teacher,
    Staff_Notification,
    Staff_NotificationRead,
    Replay_Staff_Notification
)
from .serializers import (
    NotificationSerializer,
    ReplayStaffNotificationSerializer,TeacherSerializer
)
from datetime import date
from students.models import (
    Students,
    StudentAttendance,
    Standard,
    Progress,
    ClasswiseNotifications,
    Class_NotificationRead,
    DailyRoutine,Term
)
from students.serializers import (
    StudentSerializer,
    ProgressSerializer,
    ClassNotificationSerializer,
    DailyRoutineSerializer,StudentAttendanceSerializer
)
from django.http import JsonResponse

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


@csrf_protect
@api_view(['POST'])
@permission_classes([AllowAny])
def teacher_login(request):
    try:
        reg_no = request.data.get('reg_no', '').strip()
        password = request.data.get('password', '').strip()

        if not reg_no or not password:
            return Response(
                {'error': 'Registration number and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Use .filter().first() to avoid exceptions
        teacher = Teacher.objects.filter(reg_no__iexact=reg_no).first()

        if not teacher or not teacher.check_password(password):
            # Always same error → prevents user enumeration
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ Prevent session fixation
        request.session.flush()
        request.session['teacher_id'] = teacher.id
        request.session['is_authenticated'] = True

        # ✅ Class & subjects data
        classes_data = []
        class_charges = teacher.class_charges.all()

        for cls in class_charges:
            subjects_data = [
                {"id": subj.id, "name": subj.name}
                for subj in cls.subjects.all()
            ]
            classes_data.append({
                "class_id": cls.id,
                "class_name": cls.std,
                "subjects": subjects_data,
            })

        # ✅ Teacher data
        teacher_data = {
            'id': teacher.id,
            'name': teacher.name,
            'father_name': teacher.father_name,
            'blood_grp': teacher.blood_grp,
            'msr_no': teacher.msr_no,
            'salary': str(teacher.salary),
            'islamic_qualification': teacher.islamic_qualification,
            'academic_qualification': teacher.academic_qualification,
            'other_occupation': teacher.other_occupation,
            'phone_no': teacher.phone_no,
            'email': teacher.email,
            'address': teacher.address,
            'place': teacher.place,
            'reg_no': teacher.reg_no,
            'image': teacher.image.url if teacher.image else None,
            'class_charges': classes_data
        }

        return Response({'teacher': teacher_data}, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@csrf_protect
def teacher_logout(request):
    if request.method == 'POST':
        if 'teacher_id' in request.session:
            request.session.flush()
        return JsonResponse({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)  # ✅ Now works
    return JsonResponse({'error': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_class_students(request, class_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)


    try:
        std = get_object_or_404(Standard, id=class_id)
        students = std.students.all()  # Ensure `.all()` is used for queryset
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)

    except Exception as e:
        logger.error("Error occurred while fetching students for class %s: %s", class_id, str(e))
        return Response({"error": f"An unexpected error occurred: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_teacher_attendance(request, teacher_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch teacher by ID
        teacher = get_object_or_404(Teacher, id=teacher_id)
        attendance_records = teacher.attendance_records.all()

        # Prepare attendance data for response
        attendance_data = [
            {
                "date": record.date.strftime("%Y-%m-%d"),
                "session": record.session,
                "status": record.status,
                "remarks": record.remarks or ""
            } for record in attendance_records
        ]

        # Initialize attendance summary counters
        full_days_present = 0
        partial_days_present = 0
        full_days_absent = 0

        # Group records by date
        grouped_records = {}
        for record in attendance_records:
            key = (record.date, record.teacher)
            if key not in grouped_records:
                grouped_records[key] = []
            grouped_records[key].append(record)

        # Analyze attendance records for summary
        for records in grouped_records.values():
            present_sessions = [r.status for r in records]
            if all(status == 'present' for status in present_sessions):
                full_days_present += 1
            elif any(status == 'present' for status in present_sessions):
                partial_days_present += 1
            else:
                full_days_absent += 1

        # Return the response with attendance data and summary
        return Response({
            "teacher_id": teacher.id,
            "teacher_name": teacher.name,
            "attendance_records": attendance_data,
            "attendance_summary": {
                "full_days_present": full_days_present,
                "partial_days_present": partial_days_present,
                "full_days_absent": full_days_absent,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error("Error occurred while fetching attendance data: %s", str(e))
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def mark_attendance(request):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    class_id = request.data.get('class_id')
    attendance = request.data.get('attendance')
    date = request.data.get('date')

    print(class_id,attendance,date)
    # Validate the input data
    if not class_id or not attendance or not date :
        return Response(
            {"error": "All fields (class_id, attendance, date, teacher_id) are required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    # Process each student's attendance record
    for student_id, attendance_status in attendance.items():
        try:
            student = Students.objects.get(id=student_id)

            # Create or update attendance record
            attendance_record, created = StudentAttendance.objects.update_or_create(
                student=student,
                date=date,
                defaults={'status': attendance_status}
            )
            if created:
                print(f"Created attendance record for {student.name} on {date}: {attendance_status}")
            else:
                print(f"Updated attendance record for {student.name} on {date}: {attendance_status}")

        except Students.DoesNotExist:
            print(f"Student with ID {student_id} does not exist.")
            return Response(
                {"error": f"Student with ID {student_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
    return Response({"message": "Attendance marked successfully!"}, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_students_attendance_by_date(request, class_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    date = request.query_params.get('date')
    if not date:
        return Response({'error': 'Date is required.'}, status=400)

    try:
        # Ensure class exists
        standard = Standard.objects.get(id=class_id)
    except Standard.DoesNotExist:
        return Response({'error': 'Class not found.'}, status=404)

    # Fetch all attendance records for students in this class on given date
    attendance_records = StudentAttendance.objects.filter(
        student__std=standard,
        date=date
    )

    # Serialize results
    serialized_data = StudentAttendanceSerializer(attendance_records, many=True).data
    return Response(serialized_data, status=200)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_student_attendance(request):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
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




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_terms(request):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    terms = Term.objects.all()  # Fetch all terms
    term_data = [{'id': term.id, 'name': term.name, 'year':term.year} for term in terms]
    return Response(term_data)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def create_progress(request):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    data = request.data
    print("Incoming data:", data)

    try:
        progress = Progress.objects.get(
            student=data['student'],
            subject=data['subject'],
            term=data['term']
        )
        # Update marks
        progress.marks = data['marks']
        progress.save()
        return Response(ProgressSerializer(progress).data, status=status.HTTP_200_OK)
    except Progress.DoesNotExist:
        # No existing record — now validate and create
        serializer = ProgressSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_student_progress(request, student_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        student = Students.objects.get(id=student_id)

        year = request.query_params.get('year', None)

        # Fetch progress records for the specific student, optionally filtering by year
        progress_records = Progress.objects.filter(student=student)
        if year:
            progress_records = progress_records.filter(term__year=year)

        # Sort progress records by the most recently updated term first
        progress_records = progress_records.order_by('-term__year', '-term__name')

        progress_data = [
            {
                'subject': record.subject.name,
                'marks': record.marks,
                'term': record.term.name,
                'year': record.term.year
            }
            for record in progress_records
        ]

        return Response({
            'student': student.name,
            'progress': progress_data
        })

    except Students.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_student_by_id(request, student_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
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
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_timetable(request, class_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Get the Standard (class) object
        std = get_object_or_404(Standard, id=class_id)

        # Check if files are present in the request
        timetable_file = request.FILES.get('time_table')
        exam_timetable_file = request.FILES.get('exam_time_table')

        if not timetable_file and not exam_timetable_file:
            return Response(
                {"error": "Please provide at least one file: timetable or exam timetable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save files to the respective fields
        if timetable_file:
            std.time_table = timetable_file
        if exam_timetable_file:
            std.exam_time_table = exam_timetable_file
        std.save()

        return Response(
            {"message": "Timetable(s) uploaded successfully!"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_notification(request):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    search_query = request.query_params.get('search', None)
    date_filter = request.query_params.get('date', None)

    # Start with all notifications
    notifications = Staff_Notification.objects.all()

    # Filter notifications by search term in the text field
    if search_query:
        notifications = notifications.filter(text__icontains=search_query)

    # Filter notifications by date
    if date_filter:
        try:
            notifications = notifications.filter(date=date_filter)
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Order notifications by 'date' in descending order to get the most recent one first
    notifications = notifications.order_by('-date','-time')  # Sort by date in descending order

    # Serialize the notifications
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def mark_notification_as_read(request, notification_id, teacher_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Validate teacher existence
        teacher = Teacher.objects.get(id=teacher_id)
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Validate notification existence
        notification = Staff_Notification.objects.get(id=notification_id)

        # Mark notification as read (assuming Staff_NotificationRead exists)
        Staff_NotificationRead.objects.get_or_create(notification=notification, teacher=teacher)
        return Response({'message': 'Notification marked as read.'}, status=status.HTTP_200_OK)

    except Staff_Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def submit_notification_replay(request):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    replay_text = request.data.get('replay')
    notification_id = request.data.get('notification')
    teacher_id = request.data.get('teacher')

    # Validate input data
    if not replay_text or not notification_id or not teacher_id:
        return Response(
            {'error': 'Missing required fields: replay, notification, or teacher.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate notification and teacher existence
    notification = Staff_Notification.objects.filter(id=notification_id).first()
    teacher = Teacher.objects.filter(id=teacher_id).first()

    if not notification:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not teacher:
        return Response({'error': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Create or update the reply
        replay, created = Replay_Staff_Notification.objects.update_or_create(
            notification=notification,
            teacher=teacher,
            defaults={'replay': replay_text}
        )

        # Serialize the response
        serializer = ReplayStaffNotificationSerializer(replay)
        message = 'Replay submitted successfully!' if created else 'Replay updated successfully!'
        return Response({'message': message, 'data': serializer.data}, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Handle unexpected errors
        return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_my_replies(request, teacher_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch teacher
        teacher = Teacher.objects.get(id=teacher_id)
    except Teacher.DoesNotExist:
        return Response({'error': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Fetch all replies submitted by the teacher
    replies = Replay_Staff_Notification.objects.filter(teacher=teacher)

    # Serialize the replies
    serializer = ReplayStaffNotificationSerializer(replies, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_class_wise_notification(request, class_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        print("Incoming request data:", request.data)
        print("Incoming request files:", request.FILES)

        # Retrieve the Standard instance
        std = get_object_or_404(Standard, id=class_id)
        print("Retrieved Standard instance:", std)

        # Extract fields from the request
        text = request.data.get('text')  # Optional text field
        image = request.FILES.get('image')  # Optional image file
        voice = request.FILES.get('voice')  # Optional voice file

        # Validate that at least one field is provided
        if not any([text, image, voice]):
            return Response(
                {"error": "At least one of text, image, or voice is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the current date and time, ensuring that we only pass the date portion
        current_time = timezone.localtime(timezone.now())
        date = current_time.date()  # Get the date (without time) for the 'date' field
        time = current_time.time()  # Get only the time portion for the 'time' field

        # Create the ClassNotification instance
        notification = ClasswiseNotifications.objects.create(
            std_id=std,
            text=text,
            image=image,
            voice=voice,
            date=date,  # Correct date format
            time=time,  # Correct time format
        )
        print("Created notification:", notification)

        # Serialize and return the created notification
        serializer = ClassNotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except ValueError as e:
        print("Error occurred:", str(e))
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print("Unexpected error occurred:", str(e))
        return Response(
            {"error": "An unexpected error occurred."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_your_class_notification(request, class_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    # Retrieve the class (Standard) or return a 404 if it doesn't exist
    standard = get_object_or_404(Standard, id=class_id)

    # Retrieve all notifications related to the class
    notifications = standard.class_notifications.all()

    # Serialize the notifications
    serializer = ClassNotificationSerializer(notifications, many=True)

    return Response({'class': standard.std, 'notifications': serializer.data})



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['DELETE'])
def delete_your_clas_notification(request, notification_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Get the notification object by ID
        notification = ClasswiseNotifications.objects.get(id=notification_id)

        # Delete the notification
        notification.delete()

        # Return a success response
        return Response({"message": "Notification deleted successfully!"}, status=status.HTTP_200_OK)

    except ClasswiseNotifications.DoesNotExist:
        # Return an error response if the notification does not exist
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_class_notification_viewer(request, notifification_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        notification = ClasswiseNotifications.objects.get(id=notifification_id)
        read_statuses = Class_NotificationRead.objects.filter(notification=notification)

        viewers = [
            {
                "student_id": status.student.id,
                "student_name": status.student.name,
                "read_at": status.read_at
            }
            for status in read_statuses
        ]

        return Response({"notification_id": notifification_id, "viewers": viewers}, status=200)
    except ClasswiseNotifications.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)




@permission_classes([AllowAny])  # Adjust permissions as needed
@authentication_classes([SessionAuthentication])  # Use session-based authentication
@api_view(['GET'])
def get_daily_routine(request, student_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
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



@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_attendance_by_class(request, class_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
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
@api_view(['POST'])
def mark_class_completed(request, class_id):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        standard = get_object_or_404(Standard, id=class_id)
        standard.last_completed_date = date.today()  # ✅ save only today’s date
        standard.save()
        return Response({"message": "Class marked as completed for today"}, status=200)

    except Exception as e:
        return Response(
            {"error": f"Something went wrong: {str(e)}"},
            status=500
        )



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_class_teacher(request, class_id):

    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
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





@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_classs_with_students(request):
    if request.session.get("is_authenticated"):
        teacher_id = request.session.get("teacher_id")
        if not teacher_id:
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
        print("API Error:", e)
        return Response({"error": str(e)}, status=500)

