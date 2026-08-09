from .models import Cart
from django.db.models import Sum

def cart_count(request):
    count = Cart.objects.aggregate(
        total=Sum('quantity')
    )['total'] or 0

    return {
        'cart_count': count
    }