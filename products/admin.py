from django.contrib import admin
from .models import Product,Cart,Order,OrderItem,Wishlist,Payment,Review

admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Wishlist)
admin.site.register(Payment)
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'product',
        'user',
        'rating',
        'comment',
        'created_at',
    )

    list_filter = (
        'rating',
        'created_at',
    )

    search_fields = (
        'product__name',
        'user__username',
        'comment',
    )
# Register your models here.
