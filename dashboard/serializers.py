from rest_framework import serializers
from .models import Gallery,SchoolDetails,Notice,TopScorer,SchoolCommittee,Memorial,Member,Parents



class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model=Gallery
        fields='__all__'

class SchoolDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model=SchoolDetails
        fields='__all__'

class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = '__all__'

class TopScorerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopScorer
        fields = '__all__'

class CommitteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolCommittee
        fields = '__all__'





class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'job', 'age', 'relation', 'martial_status']


class ParentSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True)  # ✅ writable
    members_count = serializers.SerializerMethodField()    # ✅ Properly defined

    class Meta:
        model = Parents
        fields = [
            'id',
            'name',
            'place',
            'age',
            'job',
            'number',
            'position',
            'members',        # List of members
            'members_count',  # Count of members
        ]

    def get_members_count(self, obj):
        return obj.members.count()

    def create(self, validated_data):
        members_data = validated_data.pop('members', [])
        parent = Parents.objects.create(**validated_data)
        for member_data in members_data:
            Member.objects.create(parent=parent, **member_data)
        return parent


class MemorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Memorial
        fields = '__all__'