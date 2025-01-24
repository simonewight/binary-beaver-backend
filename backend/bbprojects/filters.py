from django_filters import rest_framework as filters
from .models import Snippet, Collection

class SnippetFilter(filters.FilterSet):
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    likes_min = filters.NumberFilter(field_name='likes', lookup_expr='count__gte')
    owner_username = filters.CharFilter(field_name='owner__username', lookup_expr='iexact')

    class Meta:
        model = Snippet
        fields = {
            'language': ['exact'],
            'is_public': ['exact'],
            'title': ['icontains'],
            'description': ['icontains'],
        }

class CollectionFilter(filters.FilterSet):
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    snippets_count = filters.NumberFilter(method='filter_snippets_count')
    owner_username = filters.CharFilter(field_name='owner__username', lookup_expr='iexact')

    class Meta:
        model = Collection
        fields = {
            'name': ['icontains'],
            'description': ['icontains'],
            'is_public': ['exact'],
        }

    def filter_snippets_count(self, queryset, name, value):
        return queryset.annotate(count=models.Count('snippets')).filter(count=value) 