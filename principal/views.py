from datetime import date
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import  ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes,parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from .models import Principal
from teachers.models import Teacher, TeacherAttendance, Staff_Notification, Staff_NotificationRead, Replay_Staff_Notification
from teachers.serializers import TeacherSerializer, TeacherAttendanceSerializer, NotificationSerializer
from students.models import (
    Students, StudentAttendance, Progress, Standard, DailyRoutine,
    Term, Public_Notification, Public_NotificationRead,Subject
)
from students.serializers import (
    StudentSerializer, ProgressSerializer, PublicNotificationSerializer,StudentAttendanceSerializer,
    StandardSerializer, StandardOnlySerializer, DailyRoutineSerializer,SubjectSerializer
)
from dashboard.models import Gallery, Notice,Parents,Member
from dashboard.serializers import GallerySerializer, NoticeSerializer,ParentSerializer,MemberSerializer
from django.http import JsonResponse


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@csrf_protect
@permission_classes([AllowAny])
@api_view(['POST'])
def principal_login(request):
    reg_no = request.data.get('reg_no', '').strip()
    password = request.data.get('password', '').strip()

    if not reg_no or not password:
        return Response({'error': 'Registration number and password required'}, status=status.HTTP_400_BAD_REQUEST)

    # Find principal
    principal = Principal.objects.filter(reg_no__iexact=reg_no).first()
    if not principal or not principal.check_password(password):
        # Always return same error for security (prevents user enumeration)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    # Prevent session fixation attacks
    request.session.flush()
    request.session['principal_id'] = principal.id
    request.session['is_authenticated'] = True

    # Build safe response
    principal_data = {
        'id': principal.id,
        'name': principal.name,
        'place': principal.place,
        'number': principal.phone_no,
        'image': principal.image.url if principal.image else None,
    }

    return Response({'principal': principal_data}, status=status.HTTP_200_OK)



@csrf_protect
def principal_logout(request):
    if request.method == 'POST':
        if 'principal_id' in request.session:
            request.session.flush()
        return JsonResponse({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)  # ✅ Now works
    return JsonResponse({'error': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_teachers_attendance_summary(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    current_date = date.today()

    last_updated_record = TeacherAttendance.objects.filter(date=current_date).order_by('-timestamp').first()

    if not last_updated_record:
        return Response({
            "last_updated_session": None,
            "total_present": 0,
            "total_absent": 0,
        }, status=status.HTTP_200_OK)

    last_updated_session = last_updated_record.session

    total_present = TeacherAttendance.objects.filter(
        status='present', date=current_date, session=last_updated_session
    ).count()

    total_absent = TeacherAttendance.objects.filter(
        status='absent', date=current_date, session=last_updated_session
    ).count()

    return Response({
        "last_updated_session": last_updated_session,
        "total_present": total_present,
        "total_absent": total_absent,
    }, status=status.HTTP_200_OK)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_all_teachers_attendance(request, teacher_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    year = request.GET.get('year')
    month = request.GET.get('month')

    if year and month:
        year = int(year)
        month = int(month)
        records = TeacherAttendance.objects.filter(
            teacher_id=teacher_id,
            date__year=year,
            date__month=month
        )
    else:
        records = TeacherAttendance.objects.filter(teacher_id=teacher_id)

    serialized_records = TeacherAttendanceSerializer(records, many=True)
    return Response(serialized_records.data)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_student_attendance(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    class_id = request.query_params.get('class_id')
    student_id = request.query_params.get('student_id')

    if not class_id or not student_id:
        return Response({"error": "Both class_id and student_id are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        standard = get_object_or_404(Standard, id=class_id)
        student = get_object_or_404(Students, id=student_id, std=standard)

        attendance_records = StudentAttendance.objects.filter(student=student).order_by('-date')

        if not attendance_records.exists():
            return Response({"message": "No attendance records found."}, status=status.HTTP_404_NOT_FOUND)

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
def get_all_my_stds(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        students = Students.objects.all()
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data, safe=False, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_teachers(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        teachers = Teacher.objects.all()
        serializer = TeacherSerializer(teachers, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)




@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@parser_classes([MultiPartParser, FormParser])
@api_view(['GET', 'PUT'])
def edit_teacher_profile(request, teacher_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == 'GET':
        serializer = TeacherSerializer(teacher)
        return Response(serializer.data)

    elif request.method == 'PUT':
        print('Updated teacher info', request.data)
        serializer = TeacherSerializer(teacher, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def get_subjects_by_class_id(request, class_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        subjects = Subject.objects.filter(standard_id=class_id)
        serializer = SubjectSerializer(subjects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"message": "Error fetching subjects", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_classs_with_details(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
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




@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def add_student(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    if request.method == 'POST':
        serializer = StudentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Student added successfully!",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "Failed to add student",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@parser_classes([MultiPartParser, FormParser])
@api_view(['GET', 'PUT'])
def edit_students_profile(request, student_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    student = get_object_or_404(Students, id=student_id)

    if request.method == 'GET':
        serializer = StudentSerializer(student)
        return Response(serializer.data, status=200)

    elif request.method == 'PUT':
        serializer = StudentSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def mark_teacher_attendance(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    # Check if request.data is a list of attendance records
    if not isinstance(request.data, list):
        return Response({"error": "Expected a list of attendance records."}, status=400)

    try:
        # Loop through each attendance record in the list
        for attendance_record in request.data:
            teacher_id = attendance_record.get('teacher_id')
            date = attendance_record.get('date')
            session = attendance_record.get('session')
            status = attendance_record.get('status', 'absent')  # Default to 'absent' if not provided

            # Validate required fields
            if not all([teacher_id, date, session, status]):
                return Response({"error": "Missing required fields in attendance record."}, status=400)

            # Retrieve the teacher or respond with a 404 if not found
            teacher = get_object_or_404(Teacher, id=teacher_id)

            # Create or update attendance record for the teacher
            TeacherAttendance.objects.update_or_create(
                teacher=teacher,
                date=date,
                session=session,
                defaults={'status': status}
            )

        return Response({"message": "Attendance marked successfully!"}, status=200)

    except Exception as e:
        return Response({"error": "An error occurred: " + str(e)}, status=500)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_teacher_attendance_by_date_session(request):
    # Optional: check principal login
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    date = request.query_params.get('date')
    session = request.query_params.get('session')

    if not date or not session:
        return Response({'error': 'Date and session are required.'}, status=400)

    # Fetch attendance records
    attendance_records = TeacherAttendance.objects.filter(date=date, session=session)

    # Serialize and return (empty queryset returns empty list)
    serialized_data = TeacherAttendanceSerializer(attendance_records, many=True).data
    return Response(serialized_data)




@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def mark_attendance(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
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
        principal_id = request.session.get("principal_id")
        if not principal_id:
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
def get_all_student_progress(request, student_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
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
def get_terms(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    principal_id = request.session.get("principal_id")
    if not principal_id:
        return Response({"message": "Unauthorized"}, status=403)
    terms = Term.objects.all()  # Fetch all terms
    term_data = [{'id': term.id, 'name': term.name, 'year':term.year} for term in terms]
    return Response(term_data)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def create_progress(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    # Check if the combination of student, subject, and term already exists
    student_id = request.data.get('student')
    term_id = request.data.get('term')
    subject_id = request.data.get('subject')

    try:
        # Try to fetch the existing Progress record based on the student, subject, and term combination
        progress = Progress.objects.get(student_id=student_id, subject_id=subject_id, term_id=term_id)
        # If it exists, update the marks
        progress.marks = request.data.get('marks')
        progress.save()
        return Response(ProgressSerializer(progress).data, status=status.HTTP_200_OK)
    except Progress.DoesNotExist:
        # If it doesn't exist, create a new record
        serializer = ProgressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def add_notice(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    principal_id = request.session.get("principal_id")
    if not principal_id:
        return Response({"message": "Unauthorized"}, status=403)
    serializer = NoticeSerializer(data=request.data)
    print(serializer)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Notice added successfully!",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['DELETE'])
def notice_delete(request, image_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        notice = Notice.objects.get(id=image_id)
    except Notice.DoesNotExist:
        return Response({'detail': 'notice not found'}, status=status.HTTP_404_NOT_FOUND)

    notice.delete()
    return Response({'detail': 'notice deleted successfully'}, status=status.HTTP_204_NO_CONTENT)




@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def add_gallery(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    serializer = GallerySerializer(data=request.data)
    print(serializer)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Gallery added successfully!",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['DELETE'])
def gallery_delete(request, image_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        gallery = Gallery.objects.get(id=image_id)
    except Gallery.DoesNotExist:
        return Response({'detail': 'gallery not found'}, status=status.HTTP_404_NOT_FOUND)

    gallery.delete()
    return Response({'detail': 'gallery deleted successfully'}, status=status.HTTP_204_NO_CONTENT)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def create_notification_staff(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    if request.method == 'POST':
        # Get the text, image, and voice from the request data
        text = request.data.get('text', None)  # Optional field
        image = request.FILES.get('image', None)  # Optional file
        voice = request.FILES.get('voice', None)  # Optional file

        # Create a new notification, using only the provided fields
        notification = Staff_Notification.objects.create(
            text=text,
            image=image,
            voice=voice,
        )

        # Serialize and return the created notification
        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def create_notification_students(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    if request.method == 'POST':
        # Get the text, image, and voice from the request data
        text = request.data.get('text', None)  # Optional field
        image = request.FILES.get('image', None)  # Optional file
        voice = request.FILES.get('voice', None)  # Optional file

        # Create a new notification, using only the provided fields
        notification = Public_Notification.objects.create(
            text=text,
            image=image,
            voice=voice,
        )

        # Serialize and return the created notification
        serializer = PublicNotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_notification(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
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


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['DELETE'])
def delete_notification(request, notification_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Get the notification object by ID
        notification = Staff_Notification.objects.get(id=notification_id)

        # Delete the notification
        notification.delete()

        # Return a success response
        return Response({"message": "Notification deleted successfully!"}, status=status.HTTP_200_OK)

    except Staff_Notification.DoesNotExist:
        # Return an error response if the notification does not exist
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_notification_viewer(request, notifification_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        notification = Staff_Notification.objects.get(id=notifification_id)
        read_statuses = Staff_NotificationRead.objects.filter(notification=notification)

        viewers = [
            {
                "teacher_id": status.teacher.id,
                "teacher_name": status.teacher.name,
                "read_at": status.read_at
            }
            for status in read_statuses
        ]

        return Response({"notification_id": notifification_id, "viewers": viewers}, status=200)
    except Staff_Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_notification_replays(request, notification_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch the notification object
        notification = Staff_Notification.objects.get(id=notification_id)

        # Fetch related replay statuses
        replay_status = Replay_Staff_Notification.objects.filter(notification=notification)

        # Serialize replay data
        replays = [
            {
                "teacher": TeacherSerializer(status.teacher).data,
                "replay": status.replay,
                "reply_at": status.replay_at,
            }
            for status in replay_status
        ]

        return Response({"notification_id": notification_id, "replays": replays}, status=200)
    except Staff_Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_public_notification(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    search_query = request.query_params.get('search', None)
    date_filter = request.query_params.get('date', None)

    # Start with all notifications
    notifications = Public_Notification.objects.all()

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
    serializer = PublicNotificationSerializer(notifications, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_public_notification_viewer(request, notifification_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        notification = Public_Notification.objects.get(id=notifification_id)
        read_statuses = Public_NotificationRead.objects.filter(notification=notification)

        viewers = [
            {
                "student_id": status.student.id,
                "student_name": status.student.name,
                "read_at": status.read_at
            }
            for status in read_statuses
        ]

        return Response({"notification_id": notifification_id, "viewers": viewers}, status=200)
    except Public_Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['DELETE'])
def delete_public_notification(request, notification_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Get the notification object by ID
        notification = Public_Notification.objects.get(id=notification_id)

        # Delete the notification
        notification.delete()

        # Return a success response
        return Response({"message": "Notification deleted successfully!"}, status=status.HTTP_200_OK)

    except Public_Notification.DoesNotExist:
        # Return an error response if the notification does not exist
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)



@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['POST'])
def create_standard(request):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    serializer = StandardSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Standard created successfully!", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )
    return Response(
        {"message": "Failed to create Standard", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['PUT'])
def edit_std(request, class_id):

    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch the class using the class_id
        standard = Standard.objects.get(id=class_id)
    except Standard.DoesNotExist:
        return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)

    # Deserialize the data to update the standard
    print("Incoming data:", request.data)  # Debugging: Log incoming data
    serializer = StandardOnlySerializer(standard, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    print("Serializer errors:", serializer.errors)  # Debugging: Log serializer errors
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




from datetime import datetime, date

@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_daily_routine(request, student_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    # Get ?date= or use today's date as default
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        selected_date = date.today()

    # ✅ Filter for only the selected date
    daily_routines = DailyRoutine.objects.filter(
        student=student,
        date=selected_date
    ).order_by('-date')

    if not daily_routines.exists():
        return Response({"message": "No daily routines found for this student for this date."}, status=status.HTTP_404_NOT_FOUND)

    serializer = DailyRoutineSerializer(daily_routines, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)





@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_attendance_by_class(request, class_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
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
        principal_id = request.session.get("principal_id")
        if not principal_id:
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
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    # Get the Standard object or return a 404 error if not found
    std = get_object_or_404(Standard, id=class_id)
    print('selected class is ',std)
    # Retrieve the class teacher
    class_teacher = std.class_teacher
    print('result is',class_teacher,class_id)
    if class_teacher:
        # Serialize the full teacher details
        teacher_serializer = TeacherSerializer(class_teacher)
        return Response(teacher_serializer.data, status=200)
    else:
        return Response({"error": "Class teacher not assigned"}, status=404)


@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['DELETE'])
def remove_students(request, student_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    student.delete()
    return Response({"message": "Student removed successfully"}, status=status.HTTP_200_OK)




@csrf_protect
@permission_classes([AllowAny])
@api_view(['PUT'])
@authentication_classes([SessionAuthentication])
def pass_student(request, student_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        student = Students.objects.get(id=student_id)
    except Students.DoesNotExist:
        return Response({"message": "Student not found"}, status=404)

    try:
        current_std_num = int(student.std.std)
    except ValueError:
        return Response({"message": "Invalid current class format."}, status=400)

    if current_std_num >= 12:
        return Response({"message": "Student is already in the highest class (12)."}, status=400)

    next_std_num = current_std_num + 1

    try:
        next_std = Standard.objects.get(std=str(next_std_num))
    except Standard.DoesNotExist:
        return Response({"message": f"No class found for std {next_std_num}."}, status=400)

    student.std = next_std
    student.save()

    return Response({
        "message": f"{student.name} has been promoted to class {next_std.std}."
    }, status=200)


@permission_classes([AllowAny])
@api_view(['GET'])
@authentication_classes([SessionAuthentication])
def student_info(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch all classes and their related students
        classes = Standard.objects.prefetch_related('students').all()

        # Serialize the data
        data = [
            {
                "id": standard.id,
                "class": standard.std,
                "class_teacher": standard.class_teacher.name if standard.class_teacher else None,
                "students": [
                    {
                        "id": student.id,
                        "name": student.name,
                        "image": student.image.url if student.image else None,
                        "gender": student.gender,
                        "parent_name": student.parent_name,
                        "address": student.address,
                        "admission_no": student.admission_no,
                        "phone_no": student.phone_no,
                        "blood_grp": student.blood_grp,
                        "place": student.place,
                    }
                    for student in standard.students.all()
                ],
            }
            for standard in classes
        ]

        return Response(data, safe=False)  # ✅ Using JsonResponse instead of Response

    except Exception as e:
        return Response({"error": str(e)}, status=500)



@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_parents(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        parents = Parents.objects.all().order_by("name")  # 👈 ORDER BY NAME ASCENDING
        serializer = ParentSerializer(parents, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        return Response({"message": f"Error: {str(e)}"}, status=500)



@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_members_by_parents(request, parent_id):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        parent = Parents.objects.get(id=parent_id)
    except Parents.DoesNotExist:
        return Response({"message": "Parent not found"}, status=404)

    members = parent.members.all()  # uses related_name='members'
    serializer = MemberSerializer(members, many=True)
    return Response(serializer.data, status=200)




@csrf_protect
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def add_parents(request):
    if request.session.get("is_authenticated"):
        principal_id = request.session.get("principal_id")
        if not principal_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    serializer = ParentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Parent added successfully!", "data": serializer.data}, status=201)
    else:
        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=400)