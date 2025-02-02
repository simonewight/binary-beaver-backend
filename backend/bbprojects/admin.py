from django.contrib import admin
from .models import User, Snippet, Collection

@admin.register(Snippet)
class SnippetAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'language', 'created_at', 'is_public')
    list_filter = ('language', 'is_public', 'created_at')
    search_fields = ('title', 'description', 'owner__username')
    date_hierarchy = 'created_at'

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at', 'is_public')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'description', 'owner__username')
    date_hierarchy = 'created_at'

# If you're using a custom User model, register it too
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'date_joined', 'is_staff')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    date_hierarchy = 'date_joined'