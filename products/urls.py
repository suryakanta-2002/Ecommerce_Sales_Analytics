from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet,CartViewSet,WishlistViewSet,OrderViewSet,OrderItemViewSet,PaymentViewSet

router = DefaultRouter()
router.register(r'api/products', ProductViewSet, basename='product-api')
router.register(r'api/cart', CartViewSet, basename='cart-api')
router.register(r'api/wishlist',WishlistViewSet,basename='wishlist-api')
router.register(r'api/orders',OrderViewSet,basename='order-api')
router.register(r'api/order-items',OrderItemViewSet,basename='order-item-api')
router.register(r'api/payments',PaymentViewSet,basename='payment-api')
urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('product/<int:pk>/',views.product_detail,name='product_detail'),
    path('add-to-cart/<int:pk>/',views.add_to_cart,name='add_to_cart'),
    path('cart/',views.cart_view,name='cart'),
    path('cart/increase/<int:pk>/',views.increase_cart,name='increase_cart'),
    path('cart/decrease/<int:pk>/',views.decrease_cart,name='decrease_cart'),
    path('cart/remove/<int:pk>/',views.remove_from_cart,name='remove_from_cart'),
    path('checkout/',views.checkout,name='checkout'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    path('order-success/<int:pk>/',views.order_success,name='order_success'),
    path('orders/',views.order_list,name='order_list'),
    path('orders/cancel/<int:pk>/',views.cancel_order,name='cancel_order'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('analytics/',views.sales_analytics,name='sales_analytics'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:pk>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:pk>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('about/',views.about,name='about'),
]
urlpatterns +=router.urls