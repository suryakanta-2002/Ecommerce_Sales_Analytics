from django.shortcuts import render,get_object_or_404,redirect
from.models import Product,Cart,Order,OrderItem,Wishlist,Payment,Review
from django.core.paginator import Paginator
from django.db.models import Sum,Count,Avg,F,ExpressionWrapper,DecimalField
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login 
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .serializers import ProductSerializer,CartSerializer,WishlistSerializer,OrderSerializer,OrderItemSerializer,PaymentSerializer
from rest_framework.permissions import BasePermission, SAFE_METHODS,IsAuthenticated,IsAdminUser
from django.db import transaction
import uuid
from .forms import ReviewForm
from .mongodb import user_activity
from datetime import datetime
from .analytics.analysis import sales_analysis
from .analytics.charts import create_sales_chart
def product_list(request):
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort = request.GET.get('sort', '')

    products = Product.objects.all()

    # Search filter
    if search:
        products = products.filter(
            name__icontains=search
        )
    if request.user.is_authenticated:
        user_activity.insert_one({
            'user_id': request.user.id,
            'username': request.user.username,
            'activity': 'search',
            'search_term': search,
            'timestamp': datetime.now()
        })
    # Category filter
    if category:
        products = products.filter(
            category=category
        )

    # Minimum price filter
    if min_price:
        products = products.filter(
            price__gte=min_price
        )

    # Maximum price filter
    if max_price:
        products = products.filter(
            price__lte=max_price
        )

    # Sorting
    if sort == 'price_low':
        products = products.order_by('price')

    elif sort == 'price_high':
        products = products.order_by('-price')

    elif sort == 'newest':
        products = products.order_by('-created_at')

    elif sort == 'name':
        products = products.order_by('name')
    # Pagination
    paginator = Paginator(products, 12)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)
    # Categories
    categories = Product.objects.values_list(
        'category',
        flat=True
    ).distinct()

    return render(
        request,
        'products/product_list.html',
        {
            'products': products,
            'search': search,
            'categories': categories,
            'selected_category': category,
            'min_price': min_price,
            'max_price': max_price,
            'sort': sort,
            'products':page_obj,
            'page_obj':page_obj
        }
    )
@login_required
def product_detail(request, pk):

    product = get_object_or_404(Product, pk=pk)

    reviews = Review.objects.filter(
        product=product
    ).select_related('user').order_by('-created_at')

    if request.method == 'POST':

        form = ReviewForm(request.POST)

        if form.is_valid():

            review = form.save(commit=False)

            review.user = request.user
            review.product = product

            review.save()

            return redirect(
                'product_detail',
                pk=product.pk
            )

    else:
        form = ReviewForm()
    user_activity.insert_one({
        'user_id': request.user.id if request.user.is_authenticated else None,
        'username': request.user.username if request.user.is_authenticated else 'Guest',
        'activity': 'product_view',
        'product_id': product.id,
        'product_name': product.name,
        'timestamp': datetime.now()
    })

    return render(
        request,
        'products/product_detail.html',
        {
            'product': product,
            'reviews': reviews,
            'form': form,
        }
    )

from django.contrib.auth.decorators import login_required

@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.stock > 0:
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            cart_item.quantity += 1
            cart_item.save()

    return redirect('product_list')
@login_required
def cart(request):
    cart_items = Cart.objects.filter(user=request.user)

    return render(request, 'products/cart.html', {
        'cart_items': cart_items
    })
def cart_view(request):
    cart_items = Cart.objects.select_related('product').filter(user=request.user)

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    return render(
        request,
        'products/cart.html',
        {
            'cart_items': cart_items,
            'total': total,
        }
    )
def increase_cart(request, pk):
    cart_item = get_object_or_404(Cart, pk=pk,user=request.user)

    if cart_item.quantity < cart_item.product.stock:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart')
def decrease_cart(request, pk):
    cart_item = get_object_or_404(Cart, pk=pk,user=request.user)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    return redirect('cart')

def remove_from_cart(request, pk):
    cart_item = get_object_or_404(Cart, pk=pk,user=request.user)
    cart_item.delete()

    return redirect('cart')

def checkout(request):
    cart_items = Cart.objects.select_related('product').filter(user=request.user)

    if not cart_items.exists():
        return redirect('cart')

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    if request.method == 'POST':

        customer_name = request.POST.get('customer_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')

        order = Order.objects.create(
            user=request.user,
            customer_name=customer_name,
            phone=phone,
            email=email,
            address=address,
            total_amount=total
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            item.product.stock -= item.quantity
            item.product.save()

        cart_items.delete()

        return redirect('payment',order_id=order.pk)

    return render(
        request,
        'products/checkout.html',
        {
            'cart_items': cart_items,
            'total': total
        }
    )

@login_required
@transaction.atomic
def payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if request.method == 'POST':

        payment_method = request.POST.get('payment_method')

        if payment_method not in ['COD', 'UPI']:
            return render(
                request,
                'products/payment.html',
                {
                    'order': order,
                    'error': 'Please select a valid payment method.'
                }
            )

        transaction_id = (
            'TXN' +
            str(uuid.uuid4()).replace('-', '')[:10].upper()
        )

        if payment_method == 'COD':
            payment_status = 'Pending'
        else:
            payment_status = 'Success'

        Payment.objects.create(
            order=order,
            amount=order.total_amount,
            payment_method=payment_method,
            status=payment_status,
            transaction_id=transaction_id
        )

        order.status = 'Confirmed'
        order.save()

        return redirect(
            'order_success',
            pk=order.pk
        )

    return render(
        request,
        'products/payment.html',
        {
            'order': order
        }
    )
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk,user=request.user)

    return render(
        request,
        'products/order_success.html',
        {
            'order': order
        }
    )

@login_required
def order_list(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'products/order_list.html',
        {
            'orders': orders
        }
    )
@login_required
def dashboard(request):

    # All products are public
    total_products = Product.objects.count()

    # Current user's cart only
    total_cart_items = Cart.objects.filter(
        user=request.user
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    # Current user's orders only
    user_orders = Order.objects.filter(
        user=request.user
    )

    total_orders = user_orders.count()

    # Current user's sales
    total_sales = user_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # Current user's order items
    total_items_sold = OrderItem.objects.filter(
        order__in=user_orders
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    # Current user's average order value
    average_order_value = user_orders.aggregate(
        average=Avg('total_amount')
    )['average'] or 0

    return render(
        request,
        'products/dashboard.html',
        {
            'total_products': total_products,
            'total_cart_items': total_cart_items,
            'total_orders': total_orders,
            'total_sales': total_sales,
            'total_items_sold': total_items_sold,
            'average_order_value': average_order_value,
        }
    )
def sales_analytics(request):

    # Check if user is logged in
    if not request.user.is_authenticated:
        return render(
            request,
            'products/analytics_access_denied.html'
        )

    # Only admin/staff can view analytics
    if not request.user.is_staff:
        return render(
            request,
            'products/analytics_access_denied.html'
        )

    total_sales = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    total_orders = Order.objects.count()

    total_items_sold = OrderItem.objects.aggregate(
        total=Sum('quantity')
    )['total'] or 0

    average_order_value = Order.objects.aggregate(
        average=Avg('total_amount')
    )['average'] or 0

    category_sales = (
        OrderItem.objects
        .values('product__category')
        .annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum(
                ExpressionWrapper(
                    F('price') * F('quantity'),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2
                    )
                )
            )
        )
        .order_by('-total_sales')
    )

    analytics = sales_analysis()

    create_sales_chart()

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_items_sold': total_items_sold,
        'average_order_value': average_order_value,
        'category_sales': category_sales,
        'analytics': analytics,
    }

    return render(
        request,
        'products/sales_analytics.html',
        context
    )

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {
        'form': form
    })

@login_required
def add_to_wishlist(request, pk):
    product = get_object_or_404(Product, pk=pk)

    Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    user_activity.insert_one({
        'user_id': request.user.id,
        'username': request.user.username,
        'activity': 'add_to_wishlist',
        'product_id': product.id,
        'product_name': product.name,
        'timestamp': datetime.now()
    })
    return redirect('product_list')

@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product').order_by('-added_at')

    return render(
        request,
        'products/wishlist.html',
        {
            'wishlist_items': wishlist_items
        }
    )

@login_required
def remove_from_wishlist(request, pk):
    Wishlist.objects.filter(
        user=request.user,
        product_id=pk
    ).delete()

    return redirect('wishlist')




class IsAdminOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_staff


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer

    def get_permissions(self):
        if self.request.user.is_staff:
            return [IsAdminUser()]

        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Cart.objects.all().select_related('product', 'user')

        return Cart.objects.filter(
            user=self.request.user
        ).select_related('product', 'user')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(
            user=self.request.user
        ).select_related('product')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().prefetch_related(
                'items__product'
            ).order_by('-created_at')

        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related(
            'items__product'
        ).order_by('-created_at')

    @transaction.atomic
    def perform_create(self, serializer):

        cart_items = Cart.objects.filter(
            user=self.request.user
        ).select_related('product')

        if not cart_items.exists():
            raise ValidationError({
                'cart': 'Your cart is empty.'
            })

        # Check stock before creating the order
        for item in cart_items:

            if item.quantity > item.product.stock:
                raise ValidationError({
                    'stock': (
                        f'Not enough stock for {item.product.name}. '
                        f'Available stock: {item.product.stock}, '
                        f'Requested: {item.quantity}.'
                    )
                })

        # Calculate total
        total = sum(
            item.product.price * item.quantity
            for item in cart_items
        )

        # Create order
        order = serializer.save(
            user=self.request.user,
            total_amount=total
        )

        # Create order items and reduce stock
        for item in cart_items:

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            item.product.stock -= item.quantity
            item.product.save()

        # Clear cart
        cart_items.delete()

class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]

        return [IsAdminUser()]

    def get_queryset(self):
        if self.request.user.is_staff:
            return OrderItem.objects.all().select_related(
                'order',
                'product'
            )

        return OrderItem.objects.filter(
            order__user=self.request.user
        ).select_related(
            'order',
            'product'
        )

    def perform_create(self, serializer):
        product = serializer.validated_data['product']

        serializer.save(
            price=product.price
        )

class PaymentViewSet(viewsets.ModelViewSet):

    serializer_class = PaymentSerializer

    def get_permissions(self):

        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]

        return [IsAdminUser()]

    def get_queryset(self):

        if self.request.user.is_staff:
            return Payment.objects.all().select_related(
                'order',
                'order__user'
            ).order_by('-created_at')

        return Payment.objects.filter(
            order__user=self.request.user
        ).select_related(
            'order'
        ).order_by('-created_at')

    def perform_create(self, serializer):

        order_id = self.request.data.get('order')

        order = get_object_or_404(
            Order,
            id=order_id,
            user=self.request.user
        )

        serializer.save(
            order=order,
            amount=order.total_amount,
            status='Success',
            transaction_id='TXN' + str(
            uuid.uuid4()
            ).replace('-', '')[:10].upper()
        )

@login_required
@transaction.atomic
def cancel_order(request, pk):

    order = get_object_or_404(
        Order,
        pk=pk,
        user=request.user
    )

    # Already cancelled order ku puni cancel karibani
    if order.status == 'Cancelled':
        return redirect('order_list')

    # Order items retrieve kara
    order_items = OrderItem.objects.select_related(
        'product'
    ).filter(
        order=order
    )

    # Stock feri product ku add kara
    for item in order_items:

        item.product.stock += item.quantity
        item.product.save()

    # Order status change kara
    order.status = 'Cancelled'
    order.save()

    return redirect('order_list')

def about(request):
    return render(
        request,
        'products/about.html'
    )
# Create your views here.
