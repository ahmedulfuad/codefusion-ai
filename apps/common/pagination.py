from rest_framework.pagination import CursorPagination


class CustomCursorPagination(CursorPagination):
    page_size = 20    # Number of results per page as settings
    ordering = '-created_at'    # Tells DRF to use your 'created_at' field!
    page_size_query_param = 'page_size'     # Enable the client to control page size via ?page_size=...
    max_page_size = 50    # Set a hard limit so clients can't crash your server
