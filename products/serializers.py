from rest_framework import serializers
from .models import Product,Cart,Wishlist,Order,OrderItem,Payment


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'brand',
            'discount',
            'is_active',
            'description',
            'price',
            'stock',
            'category',
            'image',
            'created_at',
            'updated_at',
        ]



class CartSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cart
        fields = [
            'id',
            'user',
            'product',
            'quantity',
            'added_at',
        ]
        read_only_fields = ['user', 'added_at']

class WishlistSerializer(serializers.ModelSerializer):

    class Meta:
        model = Wishlist
        fields = [
            'id',
            'user',
            'product',
            'added_at',
        ]
        read_only_fields = ['user', 'added_at']

class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'customer_name',
            'phone',
            'email',
            'address',
            'total_amount',
            'status',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'user',
            'total_amount',
            'status',
            'created_at',
        ]

class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order',
            'product',
            'quantity',
            'price',
        ]

        read_only_fields = [
            'price',
        ]

class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment

        fields = [
            'id',
            'order',
            'amount',
            'payment_method',
            'status',
            'transaction_id',
            'created_at',
        ]

        read_only_fields = [
            'id',
            'amount',
            'status',
            'transaction_id',
            'created_at',
        ]