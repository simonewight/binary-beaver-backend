from rest_framework import serializers
from .models import Snippet, User, Collection
from dj_rest_auth.registration.serializers import RegisterSerializer

class CustomRegisterSerializer(RegisterSerializer):
    date_of_birth = serializers.DateField(required=False)
    bio = serializers.CharField(max_length=160, required=False)
    location = serializers.CharField(max_length=100, required=False)
    is_public = serializers.BooleanField(default=True, required=False)

    def custom_signup(self, request, user):
        user.date_of_birth = self.validated_data.get('date_of_birth', '')
        user.bio = self.validated_data.get('bio', '')
        user.location = self.validated_data.get('location', '')
        user.is_public = self.validated_data.get('is_public', True)
        user.save()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'bio', 'location', 'is_public', 'date_joined']
        read_only_fields = ['id', 'username', 'email', 'date_joined']

class SnippetSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Snippet
        fields = ('id', 'title', 'code_content', 'language', 'description',
                 'owner', 'is_public', 'created_at', 'updated_at', 
                 'likes_count', 'is_liked')
        read_only_fields = ('owner', 'created_at', 'updated_at')

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False 

class CollectionSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    snippets = SnippetSerializer(many=True, read_only=True)
    snippet_count = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = ('id', 'name', 'description', 'owner', 'snippets', 
                 'is_public', 'created_at', 'updated_at', 'snippet_count')
        read_only_fields = ('owner', 'created_at', 'updated_at')

    def get_snippet_count(self, obj):
        return obj.snippets.count()