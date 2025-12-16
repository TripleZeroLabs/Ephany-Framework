from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    # Default page size if the client does not specify one
    page_size = 50

    # Allow the client to override page size: ?page_size=100
    page_size_query_param = "page_size"

    # Safety cap so nobody requests 1M rows in one call
    max_page_size = 200
