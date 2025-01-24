from rest_framework import serializers
from django.core.validators import MinLengthValidator
from .models import Snippet

class SnippetValidationSerializer(serializers.Serializer):
    title = serializers.CharField(
        required=True,
        max_length=200,
        validators=[MinLengthValidator(3)]
    )
    code_content = serializers.CharField(
        required=True,
        min_length=1,
        error_messages={
            'min_length': 'Code content cannot be empty.',
            'required': 'Code content is required.'
        }
    )
    language = serializers.ChoiceField(
        choices=Snippet.LANGUAGE_CHOICES,
        required=True,
        error_messages={
            'invalid_choice': 'Please select a valid programming language.'
        }
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    is_public = serializers.BooleanField(default=True)

class CollectionValidationSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=True,
        max_length=200,
        validators=[MinLengthValidator(3)],
        error_messages={
            'min_length': 'Collection name must be at least 3 characters long.',
            'required': 'Collection name is required.'
        }
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    is_public = serializers.BooleanField(default=True)

class SnippetActionSerializer(serializers.Serializer):
    snippet_id = serializers.IntegerField(
        required=True,
        error_messages={
            'required': 'Snippet ID is required.',
            'invalid': 'Please provide a valid snippet ID.'
        }
    ) 