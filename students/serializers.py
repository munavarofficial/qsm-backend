from rest_framework import serializers
from .models import (Students,Standard,DailyRoutine,
                     Subject,StudentAttendance,
                     Progress,Public_Notification,
                     Public_NotificationRead,ClasswiseNotifications)






class StudentSerializer(serializers.ModelSerializer):
    # We can use a nested serializer to represent the standard (or use `PrimaryKeyRelatedField`)
    std = serializers.PrimaryKeyRelatedField(queryset=Standard.objects.all())

    class Meta:
        model = Students
        fields = '__all__'  # Include all fields in the model, or list them explicitly if necessary
        extra_kwargs = {
            "password": {"write_only": True}
        }


class StudentAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAttendance
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']

class StandardSerializer(serializers.ModelSerializer):
    students = StudentSerializer(many=True, read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    class_teacher_name = serializers.SerializerMethodField()

    student_count = serializers.SerializerMethodField()
    subject_count = serializers.SerializerMethodField()

    class Meta:
        model = Standard
        fields = '__all__'

    def get_class_teacher_name(self, obj):
        return obj.class_teacher.name if obj.class_teacher else "No assigned teacher"

    def get_student_count(self, obj):
        return obj.students.count()

    def get_subject_count(self, obj):
        return obj.subjects.count()



class StandardOnlySerializer(serializers.ModelSerializer):


    class Meta:
        model = Standard
        fields = ['id','std', 'class_teacher', 'time_table', 'exam_time_table']


class ProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Progress
        fields = ['student', 'subject', 'term', 'marks']


# Serializer for the Notification model
class PublicNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Public_Notification
        fields = '__all__'  # Include all fields of the Notification model

class Public_NotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Public_NotificationRead
        fields = '__all__'  # Include all fields of the NotificationRead model


class ClassNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=ClasswiseNotifications
        fields='__all__'

class DailyRoutineSerializer(serializers.ModelSerializer):
    class Meta:
        model=DailyRoutine
        fields='__all__'