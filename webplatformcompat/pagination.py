"""Pagination for webplatformcompat viewsets."""
# -*- coding: utf-8 -*-

from rest_framework.pagination import PageNumberPagination


class Pagination(PageNumberPagination):
    """Allow overriding the page size."""
    page_size_query_param = 'page_size'
    max_page_size = 1000
