from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, authentication_classes, permission_classes,parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import get_token
from datetime import date
from .models import Management
from .serializers import ManagementSerializer
from teachers.serializers import TeacherSerializer, TeacherAttendanceSerializer
from teachers.models import Teacher, TeacherAttendance
from principal.serializers import PrincipalSerializer
from principal.models import Principal
from students.models import Standard, Students, StudentAttendance, Progress
from dashboard.models import Gallery, Notice,Parents
from dashboard.serializers import GallerySerializer, NoticeSerializer,MemorialSerializer,ParentSerializer,MemberSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@api_view(['POST'])
@csrf_protect
@permission_classes([AllowAny])
def management_login(request):
    number = request.data.get('number', '').strip()
    password = request.data.get('password', '').strip()

    if not number or not password:
        return Response({'error': 'Number and password required'}, status=status.HTTP_400_BAD_REQUEST)

    management = Management.objects.filter(number__iexact=number).first()
    if not management or not management.check_password(password):
        # Same response → prevents username enumeration
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    # ✅ Prevent session fixation (rotate session ID)
    request.session.flush()
    request.session['management_id'] = management.id
    request.session['is_authenticated'] = True

    # ✅ Return safe management info
    return Response({
        'message': 'Login successful',
        'management': {
            'id': management.id,
            'name': management.name,
            'number': management.number,
            'place': management.place,
            'position': management.position,
            'image': management.image.url if management.image else None,
        }
    }, status=status.HTTP_200_OK)



@csrf_protect
def logout_view(request):
    if request.method == 'POST':
        if 'management_id' in request.session:
            request.session.flush()
        return JsonResponse({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)  # ✅ Now works
    return JsonResponse({'error': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_all_teachers_with_data(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        teachers = Teacher.objects.all()
        serializer = TeacherSerializer(teachers, many=True)
        print('data', serializer.data)
        return Response({"teachers": serializer.data})
    except Exception as e:
        return Response({"error": str(e)}, status=500)





@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_classs_with_students(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        # ✅ Order classes by standard number (assuming `std` is numeric or sortable)
        classes = (
            Standard.objects.prefetch_related('students')
            .select_related('class_teacher')
            .order_by('std')  # 👈 This line ensures fixed order 1,2,3,4,5...
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
        return Response({"error": str(e)}, status=500)




@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
def mark_teacher_attendance(request):

    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        data = request.data  # Let DRF parse JSON safely

        if not isinstance(data, list):
            return Response({"error": "Expected a list of attendance records."}, status=400)

        for attendance_record in data:
            teacher_id = attendance_record.get('teacher_id')
            date = attendance_record.get('date')
            session = attendance_record.get('session')
            status = attendance_record.get('status', 'absent')

            if not all([teacher_id, date, session, status]):
                return Response({"error": "Missing required fields in attendance record."}, status=400)

            teacher = get_object_or_404(Teacher, id=teacher_id)

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
@api_view(['GET'])
@authentication_classes([SessionAuthentication])
def get_teacher_attendance_by_date_session(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    # Extract query parameters
    date = request.query_params.get('date')
    session = request.query_params.get('session')
    # Validate date and session parameters
    if not date or not session:
        return Response({'error': 'Date and session are required.'}, status=400)

    # Fetch attendance records based on date and session
    attendance_records = TeacherAttendance.objects.filter(date=date, session=session)

    # Check if attendance records exist for the given date and session
    if not attendance_records.exists():
        return Response({'error': 'No attendance records found for the given date and session.'}, status=404)

    # Serialize the attendance data
    serialized_data = TeacherAttendanceSerializer(attendance_records, many=True).data
    return Response(serialized_data)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_principal(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    serializer = PrincipalSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Principal added successfully!",
            "data": serializer.data
        }, status=201)  # ✅ Use 201 for created

    print(serializer.errors)  # Debugging
    return Response({
        "message": "Failed to add principal.",
        "errors": serializer.errors
    }, status=400)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_principal(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        # Fetch all principals
        principals = Principal.objects.all()

        # Serialize the queryset
        serializer = PrincipalSerializer(principals, many=True)
        print(serializer.data)
        # Return the serialized data in the response
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    except Exception as e:
        # Handle any unexpected errors
        return Response({
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['DELETE'])
def delete_principal(request, principal_id):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        principal = Principal.objects.get(id=principal_id)
        principal.delete()
        return Response({'message': 'Principal deleted successfully'}, status=204)  # ✅ Use JsonResponse
    except Principal.DoesNotExist:
        return Response({'details': 'Principal not found'}, status=404)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_teacher(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        data = request.POST  # ✅ Access form text fields
        file = request.FILES.get('image')  # ✅ Handle file upload

        # ✅ Construct data dictionary for serializer
        teacher_data = {
            "name": data.get("name"),
            "father_name": data.get("father_name"),
            "blood_grp": data.get("blood_grp"),
            "msr_no": data.get("msr_no"),
            "salary": data.get("salary"),
            "joined_date": data.get("joined_date"),
            "islamic_qualification": data.get("islamic_qualification"),
            "academic_qualification": data.get("academic_qualification"),
            "other_occupation": data.get("other_occupation"),
            "phone_no": data.get("phone_no"),
            "email": data.get("email"),
            "address": data.get("address"),
            "place": data.get("place"),
            "reg_no": data.get("reg_no"),
            "password": data.get("password"),
        }

        serializer = TeacherSerializer(data=teacher_data)
        if serializer.is_valid():
            teacher = serializer.save(image=file)  # ✅ Save teacher with image
            return Response({
                "message": "Teacher added successfully!",
                "data": serializer.data
            }, status=201)
        else:
            return Response({
                "message": "Failed to add teacher.",
                "errors": serializer.errors  # ✅ Return validation errors
            }, status=400)
            print("Serializer Errors:", serializer.errors)


    except Exception as e:
        return Response({"error": str(e)}, status=500)




@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['DELETE'])
def delete_teacher(request, teacher_id):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        teacher = Teacher.objects.get(id=teacher_id)
    except Teacher.DoesNotExist:
        return Response({'details': 'teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    teacher.delete()
    return Response(status=status.HTTP_200_OK)  # ✅ No content




@csrf_protect
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@parser_classes([MultiPartParser, FormParser])
@api_view(['GET', 'PUT'])
def edit_teacher_profile(request, teacher_id):

    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
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





@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_management(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        data = request.POST
        file = request.FILES.get('image')

        management_data = {
            "name": data.get("name"),
            "position": data.get("position"),
            "number": data.get("number"),  # ✅ Ensure it matches the model
            "place": data.get("place"),
            "password": data.get("password"),
            "image": file
        }

        serializer = ManagementSerializer(data=management_data)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Management added successfully!",
                "data": serializer.data
            }, status=201)

        print(serializer.errors)  # Debugging
        return Response({
            "message": "Failed to add Management.",
            "errors": serializer.errors
        }, status=400)

    except Exception as e:
        return Response({"message": str(e)}, status=500)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_management(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        management = Management.objects.all()
        serializer = ManagementSerializer(management, many=True)  # ✅ Fix: Serialize multiple objects

        return Response({
            "message": "Management data fetched successfully",
            "data": serializer.data  # ✅ Send serialized data
        }, status=200)

    except Exception as e:
        return Response({"message": str(e)}, status=500)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['DELETE'])
def delete_management(request, management_id):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        management = Management.objects.get(id=management_id)
    except ObjectDoesNotExist:
        return Response({'message': 'Management not found'}, status=404)  # ✅ Standardize error message key

    management.delete()
    return Response({"message": "Management deleted successfully"}, status=200)  # ✅ Return 200 instead of 204



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_notice(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    # Extract form data
    event = request.POST.get('event', '')
    date = request.POST.get('date', '')
    time = request.POST.get('time', '')
    posters = request.FILES.get('posters', None)  # Handle optional image upload

    if not event or not date or not time:
        return Response({'message': 'Event, date, and time are required.'}, status=400)

    notice_data = {
        'event': event,
        'date': date,
        'time': time,
        'posters': posters  # Image (optional)
    }

    serializer = NoticeSerializer(data=notice_data)

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Notice added successfully!",
            "data": serializer.data
        }, status=201)

    return Response({"message": "Invalid data", "errors": serializer.errors}, status=400)



@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['POST'])
def add_gallery(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    # Handle image and title from FormData
    image = request.FILES.get('image')
    title = request.POST.get('title', '')

    if not image or not title:
        return Response({'message': 'Image and title are required.'}, status=400)

    # Serialize and save
    gallery_data = {'image': image, 'title': title}
    serializer = GallerySerializer(data=gallery_data)

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Gallery added successfully!",
            "data": serializer.data
        }, status=201)

    return Response({"message": "Invalid data", "errors": serializer.errors}, status=400)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['DELETE'])
def notice_delete(request, image_id):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        notice = Notice.objects.get(id=image_id)
    except Notice.DoesNotExist:
        return Response({'detail': 'notice not found'}, status=status.HTTP_404_NOT_FOUND)

    notice.delete()
    return Response({'detail': 'notice deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
@api_view(['DELETE'])
def gallery_delete(request, image_id):

    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        gallery = Gallery.objects.get(id=image_id)
    except Gallery.DoesNotExist:
        return Response({'detail': 'gallery not found'}, status=status.HTTP_404_NOT_FOUND)

    gallery.delete()
    return Response({'detail': 'gallery deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@api_view(['GET'])
def get_all_student_attendance(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
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
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_all_teachers_attendance_summary(request):

    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    current_date = date.today()  # Get today's date

    # Get the last updated attendance record (AM or PM)
    last_updated_record = TeacherAttendance.objects.filter(date=current_date).latest('timestamp')

    # Determine the session of the last updated record (AM or PM)
    last_updated_session = last_updated_record.session  # Assuming `session` indicates 'AM' or 'PM'

    # Calculate attendance summary for the last updated session
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
        management_id = request.session.get("management_id")
        if not management_id:
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

    # Fix: Set safe=False because serialized_records.data is a list
    return Response(serialized_records.data)



@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_attendance_by_class(request, class_id):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
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
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_class_teacher(request, class_id):

    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
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
@authentication_classes([SessionAuthentication])  # Required for CSRF + session auth
@api_view(['GET'])
def get_all_student_progress(request, student_id):

    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)
    try:
        student = Students.objects.get(id=student_id)

        year = request.GET.get('year', None)

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




@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
@csrf_protect
def add_memorial(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    serializer = MemorialSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)



@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_parents(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        parents = Parents.objects.all().order_by("name")  # 👈 ORDER BY NAME ASCENDING
        serializer = ParentSerializer(parents, many=True)
        return Response(serializer.data, status=200)
    except Exception as e:
        return JsonResponse({"message": f"Error: {str(e)}"}, status=500)




@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def get_members_by_parents(request, parent_id):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
            return Response({"message": "Unauthorized"}, status=403)
    else:
        return Response({"message": "Unauthorized"}, status=403)

    try:
        parent = Parents.objects.get(id=parent_id)
    except Parents.DoesNotExist:
        return JsonResponse({"message": "Parent not found"}, status=404)

    members = parent.members.all()  # uses related_name='members'
    serializer = MemberSerializer(members, many=True)
    return Response(serializer.data, status=200)



@csrf_protect
@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([SessionAuthentication])
def add_parents(request):
    if request.session.get("is_authenticated"):
        management_id = request.session.get("management_id")
        if not management_id:
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




