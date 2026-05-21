from rest_framework import serializers
from .models import Repository, ResearchSession, Finding


class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = [
            'id',
            'url',
            'name'
        ]


class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finding
        fields = [
            'id',
            'tool_name', 
            'input_data',
            'output_data',
            'conclusion',
            'created_at',
        ]


class ResearchSessionInputSerializer(serializers.Serializer):
    repository_url = serializers.URLField(
        write_only=True
    )
    repository_name = serializers.CharField(
        max_length=255, required=False
    )
    question = serializers.CharField(
        max_length=255
    )


class ResearchSessionSerializer(serializers.ModelSerializer):
    repository = RepositorySerializer(
        read_only=True
    )
    findings = FindingSerializer(
        many=True, read_only=True
    )

    class Meta:
        model = ResearchSession
        fields = [
            'id',
            'repository',
            'question', 
            'final_answer',
            'token_usage',
            'findings',
            'created_at',
        ]
        read_only_fields = [
            'final_answer',
            'token_usage',
        ]
