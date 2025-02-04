from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import models
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import Snippet, User, Collection
from .serializers import SnippetSerializer, UserSerializer, CollectionSerializer
from .permissions import IsOwnerOrReadOnly, IsUserOrReadOnly, IsPublicOrIsOwner
from django_filters.rest_framework import DjangoFilterBackend
from .filters import SnippetFilter, CollectionFilter
from .exceptions import (
    SnippetNotAccessibleError,
    CollectionNotAccessibleError,
    ResourceNotFoundError,
    DuplicateResourceError
)
from .utils import create_response, error_response
from .pagination import StandardResultsSetPagination, CursorSetPagination
from .validators import (
    SnippetValidationSerializer,
    CollectionValidationSerializer,
    SnippetActionSerializer
)
from .throttling import SnippetCreateThrottle, CollectionCreateThrottle

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsUserOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['username', 'location']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.filter(is_public=True)
        return User.objects.all()

    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get or update the authenticated user's profile."""
        print("Me endpoint called!")  # Debug print
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        
        # PATCH request
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='me/stats', permission_classes=[permissions.IsAuthenticated])
    def stats(self, request):
        """Get the authenticated user's stats."""
        print("Stats endpoint called!")  # Debug print
        try:
            print(f"Getting stats for user: {request.user.username}")
            user = request.user
            stats = {
                'snippets_count': user.snippets.count(),
                'collections_count': user.collections.count(),
                'likes_received': sum(snippet.likes.count() for snippet in user.snippets.all()),
                'likes_given': user.liked_snippets.count() if hasattr(user, 'liked_snippets') else 0,
            }
            print(f"Stats calculated: {stats}")  # Debug print
            return Response(stats)
        except Exception as e:
            print(f"Error in stats: {str(e)}")  # Debug print
            return Response(
                {"error": "Failed to get user stats"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='me/activity', permission_classes=[permissions.IsAuthenticated])
    def activity(self, request):
        """Get the authenticated user's recent activity."""
        print("Activity endpoint called!")  # Debug print
        try:
            print(f"Getting activity for user: {request.user.username}")
            user = request.user
            recent_snippets = user.snippets.order_by('-created_at')[:5]
            recent_collections = user.collections.order_by('-created_at')[:5]

            activity_data = {
                'recent_snippets': SnippetSerializer(recent_snippets, many=True).data,
                'recent_collections': CollectionSerializer(recent_collections, many=True).data,
            }
            print(f"Activity data prepared: {activity_data}")  # Debug print
            return Response(activity_data)
        except Exception as e:
            print(f"Error in activity: {str(e)}")  # Debug print
            return Response(
                {"error": "Failed to get user activity"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SnippetViewSet(viewsets.ModelViewSet):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
        IsPublicOrIsOwner
    ]
    filter_backends = [DjangoFilterBackend, 
                      filters.SearchFilter, 
                      filters.OrderingFilter]
    filterset_class = SnippetFilter
    search_fields = ['title', 'description', 'language']
    ordering_fields = ['created_at', 'likes', 'title']
    ordering = ['-created_at']
    pagination_class = CursorSetPagination

    def get_queryset(self):
        queryset = Snippet.objects.all()
        
        # Filter by language
        language = self.request.query_params.get('language', None)
        if language:
            queryset = queryset.filter(language=language)
            
        # Filter by visibility
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                models.Q(is_public=True) | 
                models.Q(owner=self.request.user)
            )
        else:
            queryset = queryset.filter(is_public=True)
            
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            # Validate request data
            validator = SnippetValidationSerializer(data=request.data)
            validator.is_valid(raise_exception=True)
            
            # Create snippet using validated data
            serializer = self.get_serializer(data=validator.validated_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return create_response(
                data=serializer.data,
                message='Snippet created successfully',
                status_code=status.HTTP_201_CREATED
            )
        except serializers.ValidationError as e:
            return error_response(
                message='Validation error',
                data=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(str(e))

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return create_response(
                data=serializer.data,
                message='Snippet updated successfully'
            )
        except Exception as e:
            return error_response(str(e))

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return create_response(
                message='Snippet deleted successfully',
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return error_response(str(e))

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        try:
            snippet = self.get_object()
            if snippet.likes.filter(id=request.user.id).exists():
                snippet.likes.remove(request.user)
                message = 'Snippet unliked successfully'
                is_liked = False
            else:
                snippet.likes.add(request.user)
                message = 'Snippet liked successfully'
                is_liked = True
                
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'is_liked': is_liked,
                    'likes_count': snippet.likes.count()
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_throttles(self):
        if self.action == 'create':
            return [SnippetCreateThrottle()]
        return super().get_throttles()

class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, 
                      filters.SearchFilter, 
                      filters.OrderingFilter]
    filterset_class = CollectionFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Collection.objects.all()
        
        if self.request.user.is_authenticated:
            return queryset.filter(
                models.Q(is_public=True) | 
                models.Q(owner=self.request.user)
            )
        return queryset.filter(is_public=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            # Validate request data
            validator = CollectionValidationSerializer(data=request.data)
            validator.is_valid(raise_exception=True)
            
            # Create collection using validated data
            serializer = self.get_serializer(data=validator.validated_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return create_response(
                data=serializer.data,
                message='Collection created successfully',
                status_code=status.HTTP_201_CREATED
            )
        except serializers.ValidationError as e:
            return error_response(
                message='Validation error',
                data=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(str(e))

    @action(detail=True, methods=['post'])
    def add_snippet(self, request, pk=None):
        try:
            # Validate snippet_id
            validator = SnippetActionSerializer(data=request.data)
            validator.is_valid(raise_exception=True)
            
            collection = self.get_object()
            snippet = Snippet.objects.get(id=validator.validated_data['snippet_id'])
            
            if not snippet.is_public and snippet.owner != request.user:
                raise SnippetNotAccessibleError()
                
            if collection.snippets.filter(id=snippet.id).exists():
                raise DuplicateResourceError('Snippet already in collection')
                
            collection.snippets.add(snippet)
            return create_response(message='Snippet added to collection successfully')
            
        except serializers.ValidationError as e:
            return error_response(
                message='Validation error',
                data=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Snippet.DoesNotExist:
            raise ResourceNotFoundError('Snippet not found')
        except Exception as e:
            return error_response(str(e))

    @action(detail=True, methods=['post'])
    def remove_snippet(self, request, pk=None):
        collection = self.get_object()
        try:
            snippet_id = request.data.get('snippet_id')
            if not snippet_id:
                raise ValueError('snippet_id is required')
                
            snippet = collection.snippets.get(id=snippet_id)
            collection.snippets.remove(snippet)
            return create_response(message='Snippet removed from collection successfully')
            
        except Snippet.DoesNotExist:
            raise ResourceNotFoundError('Snippet not found in collection')
        except Exception as e:
            return error_response(str(e))

    def get_throttles(self):
        if self.action == 'create':
            return [CollectionCreateThrottle()]
        return super().get_throttles()

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def reset_password(request):
    try:
        username = request.data.get('username')
        new_password = request.data.get('new_password')
        
        if not username or not new_password:
            return error_response(
                message='Username and new password are required.',
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return error_response(
                message='User not found.',
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Validate the new password
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return error_response(
                message=e.messages[0],
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Set the new password
        user.set_password(new_password)
        user.save()

        return create_response(
            message='Password reset successful.',
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return error_response(str(e))