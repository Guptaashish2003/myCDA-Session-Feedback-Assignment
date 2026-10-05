# File: backend/core/pagination.py
# Purpose: Project-wide pagination class.
# Contents:
#   - StandardPagination: page-number pagination (default 20, max 100 via page_size) whose
#     response is {count, page, page_size, results}.

"""
Standard pagination for the CDA unified backend.

All list endpoints use this unless explicitly overridden.
The response shape is:
{
    "count": <total>,
    "page": <current_page>,
    "page_size": <items_per_page>,
    "results": [...]
}
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "results": data,
            }
        )
