from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from .models import Snippet, User, Collection
from .serializers import SnippetSerializer, UserSerializer, CollectionSerializer
from .permissions import IsOwnerOrReadOnly, IsUserOrReadOnly, IsPublicOrIsOwner
from django_filters import rest_framework as filters
from .filters import SnippetFilter, CollectionFilter
from django.core.exceptions import ObjectDoesNotExist
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
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'location']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # Show only public profiles to anonymous users
        if not self.request.user.is_authenticated:
            return User.objects.filter(is_public=True)
        return User.objects.all()

    @action(detail=True, methods=['get'])
    def snippets(self, request, pk=None):
        user = self.get_object()
        if user.is_public or request.user == user:
            snippets = user.snippets.filter(
                models.Q(is_public=True) | 
                models.Q(owner=request.user)
            )
            serializer = SnippetSerializer(snippets, many=True, context={'request': request})
            return Response(serializer.data)
        return Response(status=status.HTTP_403_FORBIDDEN)

class SnippetViewSet(viewsets.ModelViewSet):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
        IsPublicOrIsOwner
    ]
    filter_backends = [filters.DjangoFilterBackend, 
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

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        if not request.user.is_authenticated:
            return error_response(
                'Authentication required',
                status_code=status.HTTP_401_UNAUTHORIZED
            )
            
        try:
            snippet = self.get_object()
            if snippet.likes.filter(id=request.user.id).exists():
                snippet.likes.remove(request.user)
                message = 'Snippet unliked successfully'
            else:
                snippet.likes.add(request.user)
                message = 'Snippet liked successfully'
                
            return create_response(message=message)
        except Exception as e:
            return error_response(str(e))

    def get_throttles(self):
        if self.action == 'create':
            return [SnippetCreateThrottle()]
        return super().get_throttles()

class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend, 
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
