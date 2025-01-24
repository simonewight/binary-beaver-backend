from rest_framework.throttling import UserRateThrottle

class SnippetCreateThrottle(UserRateThrottle):
    rate = '100/day'
    scope = 'snippet_create'

class CollectionCreateThrottle(UserRateThrottle):
    rate = '50/day'
    scope = 'collection_create' 