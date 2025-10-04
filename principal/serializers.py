from rest_framework import serializers
from .models import Principal


class PrincipalSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = Principal
        fields = '__all__'


