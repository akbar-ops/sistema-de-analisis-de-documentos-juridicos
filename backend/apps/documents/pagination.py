# apps/documents/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DocumentPagination(PageNumberPagination):
    """
    Paginación personalizada para documentos
    
    Parámetros de query:
    - page: número de página (por defecto 1)
    - page_size: cantidad de items por página (por defecto 20, máximo 100)
    
    Respuesta:
    {
        "count": total de documentos,
        "next": URL de la siguiente página (null si no hay),
        "previous": URL de la página anterior (null si no hay),
        "total_pages": número total de páginas,
        "current_page": página actual,
        "page_size": items por página,
        "results": [... documentos ...]
    }
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Personaliza la respuesta de paginación para incluir información adicional
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'results': data
        })
