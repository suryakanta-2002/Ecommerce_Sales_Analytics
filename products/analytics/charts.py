import os
import pandas as pd
import matplotlib.pyplot as plt

from django.conf import settings
from products.models import OrderItem


def create_sales_chart():

    data = OrderItem.objects.select_related(
        'product'
    ).values(
        'product__name',
        'quantity'
    )

    df = pd.DataFrame(list(data))

    if df.empty:
        return None

    sales = (
        df.groupby('product__name')['quantity']
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # Create media/analytics folder
    chart_dir = os.path.join(
        settings.MEDIA_ROOT,
        'analytics'
    )

    os.makedirs(chart_dir, exist_ok=True)

    chart_path = os.path.join(
        chart_dir,
        'sales_chart.png'
    )

    plt.figure(figsize=(10, 5))

    sales.plot(kind='bar')

    plt.title('Top 10 Selling Products')
    plt.xlabel('Product')
    plt.ylabel('Items Sold')

    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    plt.savefig(chart_path)
    plt.close()

    return chart_path