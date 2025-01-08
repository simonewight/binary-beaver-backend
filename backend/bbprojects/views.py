from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from .models import Snippet, User, Collection
from .serializers import SnippetSerializer, UserSerializer, CollectionSerializer
from .permissions import IsOwnerOrReadOnly, IsUserOrReadOnly, IsPublicOrIsOwner

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsUserOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'location']

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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'language']
    ordering_fields = ['created_at', 'likes']
    ordering = ['-created_at']

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

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        snippet = self.get_object()
        if snippet.likes.filter(id=request.user.id).exists():
            snippet.likes.remove(request.user)
            return Response({'status': 'unliked'})
        else:
            snippet.likes.add(request.user)
            return Response({'status': 'liked'})

class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

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

    @action(detail=True, methods=['post'])
    def add_snippet(self, request, pk=None):
        collection = self.get_object()
        try:
            snippet_id = request.data.get('snippet_id')
            snippet = Snippet.objects.get(id=snippet_id)
            
            # Check if user has access to the snippet
            if not snippet.is_public and snippet.owner != request.user:
                return Response(
                    {'error': 'Snippet not accessible'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            collection.snippets.add(snippet)
            return Response({'status': 'snippet added'})
        except Snippet.DoesNotExist:
            return Response(
                {'error': 'Snippet not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_snippet(self, request, pk=None):
        collection = self.get_object()
        try:
            snippet_id = request.data.get('snippet_id')
            snippet = collection.snippets.get(id=snippet_id)
            collection.snippets.remove(snippet)
            return Response({'status': 'snippet removed'})
        except Snippet.DoesNotExist:
            return Response(
                {'error': 'Snippet not found in collection'},
                status=status.HTTP_404_NOT_FOUND
            )
