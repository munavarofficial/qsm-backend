from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from datetime import datetime
from datetime import date
from .models import SchoolDetails,Notice,SchoolCommittee,Memorial,Gallery
from .serializers import SchoolDetailsSerializer,NoticeSerializer,CommitteeSerializer,MemorialSerializer,GallerySerializer
from students.models import Students,StudentAttendance,Standard,DailyRoutine,Progress
from students.serializers import StandardOnlySerializer
from teachers.models import Teacher
from teachers.serializers import TeacherOnlySerializer
from principal.models import Principal
from django.db.models import Sum


@api_view(['GET'])
@permission_classes([AllowAny])
def get_school_details(request):
    try:
        school_details = SchoolDetails.objects.all()
        serializer = SchoolDetailsSerializer(school_details, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_students_count(request):
    try:
        students_count = Students.objects.count()  # Simplified query
        return Response({'all_students_count': students_count}, status=status.HTTP_200_OK)
    except Exception as e:
        # Log the error and provide a meaningful response
        return Response({'error': 'An error occurred while fetching the student count.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_teachers_count(request):
    try:
        teachers_count = Teacher.objects.count()  # Simplified query
        return Response({'teachers_count': teachers_count}, status=status.HTTP_200_OK)
    except Exception as e:
        # Log the error and provide a meaningful response
        return Response({'error': 'An error occurred while fetching the student count.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_notice(request):
    now = datetime.now()
    end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59)

    Notice.objects.filter(date__lt=end_of_today).delete()

    notices = Notice.objects.all()
    events_count = notices.count()

    serialized_data = NoticeSerializer(notices, many=True)

    return Response({
        "notices": serialized_data.data,
        "events_count": events_count
    }, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_top_students_in_attendance(request):
    try:
        students = Students.objects.all()

        top_students = []

        for student in students:
            total_classes = StudentAttendance.objects.filter(student=student).count()

            if total_classes == 0:
                attendance_percentage = 0
            else:
                total_present = StudentAttendance.objects.filter(student=student, status='present').count()
                attendance_percentage = (total_present / total_classes) * 100

            top_students.append({

                'name': student.name,
                'father_name': student.parent_name,
                'attendance_percentage': attendance_percentage,
                'class_name': student.std.std,
            })

        # Sort the students by attendance percentage and take the top 10
        top_students_sorted = sorted(top_students, key=lambda x: x['attendance_percentage'], reverse=True)[:5]

        return Response(top_students_sorted)

    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_attendance_summary(request):
    """
    Fetch the overall attendance summary for all students for the current day.
    """
    current_date = date.today()  # Get today's date
    total_present = StudentAttendance.objects.filter(status='present', date=current_date).count()
    total_absent = StudentAttendance.objects.filter(status='absent', date=current_date).count()
    total_late = StudentAttendance.objects.filter(status='late', date=current_date).count()

    total_records = total_present + total_absent + total_late

    if total_records == 0:
        return Response({
            "message": "Attendance not marked yet",
            "attendance_marked": False
        }, status=status.HTTP_200_OK)

    return Response({
        "total_present": total_present,
        "total_absent": total_absent,
        "total_late": total_late,
        "attendance_marked": True
    }, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([AllowAny])
def class_attendance_summary(request, class_id):
    """
    Fetch class-specific attendance data for the current day.
    """
    current_date = date.today()
    try:
        total_present = StudentAttendance.objects.filter(
            student__std_id=class_id,
            status='present',
            date=current_date
        ).count()

        total_absent = StudentAttendance.objects.filter(
            student__std_id=class_id,
            status='absent',
            date=current_date
        ).count()

        return Response({
            "present": total_present,
            "absent": total_absent,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_top_scorers(request):
    """
    Return top 3 students (based on total marks) from each class
    along with their parent name and total marks.
    """

    # Annotate each student's total marks
    student_totals = (
        Progress.objects
        .values(
            'student',
            'student__name',
            'student__parent_name',
            'student__std__std'
        )
        .annotate(total_marks=Sum('marks'))
        .order_by('student__std__std', '-total_marks')
    )

    # Prepare data grouped by class
    class_top_scorers = {}
    for record in student_totals:
        std_name = record['student__std__std']
        if std_name not in class_top_scorers:
            class_top_scorers[std_name] = []

        # Limit to top 3 students per class
        if len(class_top_scorers[std_name]) < 3:
            class_top_scorers[std_name].append({
                "student_name": record['student__name'],
                "father_name": record['student__parent_name'],
                "total_marks": record['total_marks']
            })

    # Convert dict into a list format for frontend
    result = [
        {
            "class": std_name,
            "top_scorers": class_top_scorers[std_name]
        }
        for std_name in sorted(class_top_scorers.keys())
    ]

    return Response(result)




@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_classes(request):
    """
    Retrieve all classes with their respective students and subjects.
    """
    try:
        classes = Standard.objects.all()
        serializer = StandardOnlySerializer(classes, many=True)
        return Response({"classes": serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_top_students_in_daily_routine(request):
    try:
        top_students = []

        students = Students.objects.all()

        for student in students:
            student_routines = DailyRoutine.objects.filter(student=student)

            total_points = 0
            daily_points_breakdown = []

            for routine in student_routines:
                completed_routines = sum([
                    routine.subahi, routine.luhur, routine.asar, routine.maqrib,
                    routine.isha, routine.thabaraka, routine.waqiha, routine.swalath, routine.haddad
                ])

                total_points += completed_routines

                daily_points_breakdown.append({
                    "date": routine.date,
                    "completed_routines": completed_routines,
                    "routine_details": [
                        field_name for field_name, field_value in {
                            'subahi': routine.subahi,
                            'luhur': routine.luhur,
                            'asar': routine.asar,
                            'maqrib': routine.maqrib,
                            'isha': routine.isha,
                            'thabaraka': routine.thabaraka,
                            'waqiha': routine.waqiha,
                            'swalath': routine.swalath,
                            'haddad': routine.haddad
                        }.items() if field_value
                    ]
                })

            total_days = len(student_routines)
            attendance_percentage = (total_points / (total_days * 9)) * 100 if total_days > 0 else 0
            class_name = student.std.std if student.std else "Not Assigned"

            top_students.append({
                "name": student.name,
                "parent_name": student.parent_name,
                "class_name": class_name,
                "total_points": total_points,
                "attendance_percentage": round(attendance_percentage, 2),
                "daily_points_breakdown": daily_points_breakdown
            })

        # ✅ Sort by total_points and return top 5
        top_students_sorted = sorted(top_students, key=lambda x: x['total_points'], reverse=True)[:5]

        return Response({"top_students": top_students_sorted})

    except Exception as e:
        return Response({'error': str(e)}, status=500)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_committee(request):
    try:
        committee = SchoolCommittee.objects.all()
        serializer = CommitteeSerializer(committee, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_teachers_only(request):
    try:
        teachers = Teacher.objects.all()
        serializer = TeacherOnlySerializer(teachers, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_memorial(request):
    try:
        memorials = Memorial.objects.all()
        serializer = MemorialSerializer(memorials, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_gallery(request):
    try:
        gallery=Gallery.objects.all()
        serializer=GallerySerializer(gallery ,many=True)
        return Response({"gallery": serializer.data}, status=status.HTTP_200_OK)

    except Gallery.DoesNotExist:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_numbers(request):
    try:
        principal = Principal.objects.first()
        school = SchoolDetails.objects.first()  # get first school instance

        if principal and school:
            return Response({
                "principal_phone_no": principal.phone_no,
                "school_phone_no": school.phone_number
            })
        elif principal and not school:
            return Response({
                "principal_phone_no": principal.phone_no,
                "school_phone_no": None
            })
        elif school and not principal:
            return Response({
                "principal_phone_no": None,
                "school_phone_no": school.phone_number
            })
        else:
            return Response({"error": "No principal or school found"}, status=404)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


