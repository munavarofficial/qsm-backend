from rest_framework import serializers
from .models import Teacher,TeacherAttendance,Staff_Notification,Staff_NotificationRead,Replay_Staff_Notification
from students.serializers import StandardSerializer


class TeacherSerializer(serializers.ModelSerializer):
   class_charges = StandardSerializer(many=True, read_only=True)  # Add related field

   class Meta:
        model = Teacher
        fields = '__all__'

def get_class_charges(self, obj):
        return [
            {"class_id": cls.id, "class_name": cls.std}
            for cls in obj.class_charges.all()
        ]

class TeacherOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ['id','name','phone_no','msr_no','islamic_qualification','academic_qualification','other_occupation','image','place','email']




class TeacherAttendanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = TeacherAttendance
        fields = '__all__'



# Serializer for the Notification model
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff_Notification
        fields = '__all__'  # Include all fields of the Notification model

# Serializer for the NotificationRead model
class NotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff_NotificationRead
        fields = '__all__'  # Include all fields of the NotificationRead model


class ReplayStaffNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Replay_Staff_Notification
        fields = ['id', 'replay', 'notification', 'teacher', 'replay_at']