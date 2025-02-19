import pytest
from decimal import Decimal
from pathlib import Path
import json
from sales_metrics import (
    calculate_sales_metrics,
    load_json_data,
    to_decimal,
    SalesCalculationError,
    SalesMetrics
)

# Test data
SAMPLE_ORDERS = [
    {
        "orderId": "1",
        "items": [
            {"sku": "PROD1", "quantity": "2"},
            {"sku": "PROD2", "quantity": "1"}
        ],
        "discount": "SAVE10,WINTERMADNESS"
    },
    {
        "orderId": "2",
        "items": [
            {"sku": "PROD1", "quantity": "1"}
        ]
    }
]

SAMPLE_PRODUCTS = [
    {"sku": "PROD1", "price": "10.00"},
    {"sku": "PROD2", "price": "20.00"}
]

SAMPLE_DISCOUNTS = [
    {"key": "SAVE10", "value": "0.10"},
    {"key": "WINTERMADNESS", "value": "0.10"}
]

@pytest.fixture
def sample_data_files(tmp_path):
    """Create temporary JSON files with sample data"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    files = {
        "orders.json": SAMPLE_ORDERS,
        "products.json": SAMPLE_PRODUCTS,
        "discounts.json": SAMPLE_DISCOUNTS
    }
    
    for filename, data in files.items():
        file_path = data_dir / filename
        file_path.write_text(json.dumps(data))
    
    return tmp_path

def test_calculate_sales_metrics():
    """Test basic sales metrics calculation"""
    metrics = calculate_sales_metrics(SAMPLE_ORDERS, SAMPLE_PRODUCTS, SAMPLE_DISCOUNTS)
    
    assert isinstance(metrics, SalesMetrics)
    assert metrics.total_before_discount == Decimal('50.00')  # (2*10 + 1*20) + (1*10) = 50
    assert metrics.total_discount_amount == Decimal('8.00')   # 20% of 40 (first order has stacked discount)
    assert metrics.total_after_discount == Decimal('42.00')   # 50 - 8
    assert metrics.orders_with_discount == 1
    assert metrics.total_orders == 2
    assert metrics.average_discount_percentage == Decimal('16.00')  # (8/50)*100 = 16%

def test_to_decimal():
    """Test decimal conversion"""
    assert to_decimal("10.00", "price") == Decimal("10.00")
    assert to_decimal("0", "quantity") == Decimal("0.00")
    
    with pytest.raises(SalesCalculationError):
        to_decimal("invalid", "price")

def test_load_json_data(sample_data_files):
    """Test JSON data loading"""
    data_dir = sample_data_files / "data"
    
    orders = load_json_data(str(data_dir / "orders.json"))
    assert len(orders) == 2
    assert orders[0]["orderId"] == "1"
    
    with pytest.raises(SalesCalculationError):
        load_json_data("nonexistent.json")

def test_invalid_order_data():
    """Test handling of invalid order data"""
    invalid_orders = [
        {
            "orderId": "3",
            "items": [
                {"sku": "NONEXISTENT", "quantity": "1"}
            ]
        }
    ]
    
    with pytest.raises(SalesCalculationError):
        calculate_sales_metrics(invalid_orders, SAMPLE_PRODUCTS, SAMPLE_DISCOUNTS)

def test_stacking_discounts():
    """Test stacking discount functionality"""
    orders_with_stacking = [
        {
            "orderId": "1",
            "items": [
                {"sku": "PROD1", "quantity": "1"}
            ],
            "discount": "SAVE10,WINTERMADNESS"
        }
    ]
    
    metrics = calculate_sales_metrics(orders_with_stacking, SAMPLE_PRODUCTS, SAMPLE_DISCOUNTS)
    assert metrics.total_before_discount == Decimal('10.00')
    assert metrics.total_discount_amount == Decimal('2.00')  # 20% of 10
    assert metrics.total_after_discount == Decimal('8.00')
    assert metrics.average_discount_percentage == Decimal('20.00')

def test_invalid_discount_code():
    """Test handling of invalid discount code"""
    orders_with_invalid_discount = [
        {
            "orderId": "4",
            "items": [
                {"sku": "PROD1", "quantity": "1"}
            ],
            "discount": "INVALID,WINTERMADNESS"
        }
    ]
    
    # Should apply valid discount and log warning for invalid one
    metrics = calculate_sales_metrics(orders_with_invalid_discount, SAMPLE_PRODUCTS, SAMPLE_DISCOUNTS)
    assert metrics.orders_with_discount == 1
    assert metrics.total_discount_amount == Decimal('1.00')  # 10% from WINTERMADNESS only

def test_sales_metrics_to_dict():
    """Test conversion of SalesMetrics to dictionary"""
    metrics = SalesMetrics(
        total_before_discount=Decimal('100.00'),
        total_after_discount=Decimal('90.00'),
        total_discount_amount=Decimal('10.00'),
        orders_with_discount=1,
        total_orders=2,
        average_discount_percentage=Decimal('10.00')
    )
    
    result = metrics.to_dict()
    assert isinstance(result, dict)
    assert result["Total before discount"] == 100.00
    assert result["Total after discount"] == 90.00
    assert result["Total discount amount"] == 10.00
    assert result["Average discount percentage"] == 10.00 