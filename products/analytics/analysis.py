import pandas as pd
import numpy as np

from products.models import OrderItem


def sales_analysis():

    data = OrderItem.objects.select_related(
        'product',
        'order'
    ).values(
        'product__name',
        'product__category',
        'quantity',
        'price',
        'order__created_at'
    )

    df = pd.DataFrame(list(data))

    if df.empty:
        return {
            'total_revenue': 0,
            'total_items': 0,
            'average_order_value': 0,
            'top_product': 'No data'
        }

    # Pandas calculations
    df['sales'] = df['quantity'] * df['price']

    total_revenue = df['sales'].sum()

    total_items = df['quantity'].sum()

    average_order_value = df['sales'].mean()

    # NumPy calculation
    sales_values = np.array(df['sales'])

    sales_std = np.std(sales_values)

    # Top-selling product
    top_product = (
        df.groupby('product__name')['quantity']
        .sum()
        .sort_values(ascending=False)
        .index[0]
    )

    return {
        'total_revenue': round(float(total_revenue), 2),
        'total_items': int(total_items),
        'average_order_value': round(
            float(average_order_value), 2
        ),
        'sales_std': round(float(sales_std), 2),
        'top_product': top_product,
    }