from django.conf import settings
from django.core.paginator import Paginator


def paginate_me(pagination_list, request):
    paginator = Paginator(pagination_list, settings.PAGE_ROWS_COUNT)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
