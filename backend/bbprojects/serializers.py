from rest_framework import serializers
from .models import Snippet, User, Collection
from dj_rest_auth.registration.serializers import RegisterSerializer

class CustomRegisterSerializer(RegisterSerializer):
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(max_length=160, required=False, allow_blank=True)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_public = serializers.BooleanField(default=True, required=False)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            'date_of_birth': self.validated_data.get('date_of_birth', None),
            'bio': self.validated_data.get('bio', ''),
            'location': self.validated_data.get('location', ''),
            'is_public': self.validated_data.get('is_public', True),
        })
        print("Cleaned data:", data)  # Debug print
        return data

    def save(self, request):
        print("CustomRegisterSerializer save method called")  # Debug print
        print("Validated data:", self.validated_data)  # Debug print
        user = super().save(request)
        cleaned_data = self.get_cleaned_data()
        
        user.bio = cleaned_data.get('bio', '')
        user.location = cleaned_data.get('location', '')
        user.date_of_birth = cleaned_data.get('date_of_birth')
        user.is_public = cleaned_data.get('is_public', True)
        user.save()
        
        print("User after save - bio:", user.bio)  # Debug print
        return user

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