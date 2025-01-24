from rest_framework.exceptions import APIException
from rest_framework import status

class SnippetNotAccessibleError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to access this snippet.'
    default_code = 'snippet_not_accessible'

class CollectionNotAccessibleError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to access this collection.'
    default_code = 'collection_not_accessible'

class ResourceNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'

class DuplicateResourceError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This resource already exists.'
    default_code = 'duplicate_resource' 