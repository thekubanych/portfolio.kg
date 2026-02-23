from rest_framework import serializers
from .models import Skill, Project, ContactMessage


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'icon', 'percent', 'category', 'order']


class ProjectSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'stack', 'status', 'status_display',
                  'github_url', 'demo_url', 'is_featured', 'order', 'created_at']


class ContactMessageSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
    def validate_message(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Сообщение слишком короткое")
        return value
