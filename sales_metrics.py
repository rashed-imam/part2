import json
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

log_file = logs_dir / f"sales_calculator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DECIMAL_PLACES = Decimal('0.01')
HUNDRED = Decimal('100')
ZERO = Decimal('0')

class SalesCalculationError(Exception):
    """Base exception for sales calculation errors"""
    pass

@dataclass
class SalesMetrics:

    total_before_discount: Decimal
    total_after_discount: Decimal
    total_discount_amount: Decimal
    orders_with_discount: int
    total_orders: int
    average_discount_percentage: Decimal

    def to_dict(self) -> Dict[str, float]:
        return {
            "Total before discount": float(self.total_before_discount.quantize(DECIMAL_PLACES)),
            "Total after discount": float(self.total_after_discount.quantize(DECIMAL_PLACES)),
            "Total discount amount": float(self.total_discount_amount.quantize(DECIMAL_PLACES)),
            "Average discount percentage": float(self.average_discount_percentage.quantize(DECIMAL_PLACES))
        }

def load_json_data(file_path: str) -> List[Dict]:
    """Load and parse JSON file with error handling"""
    try:
        with Path(file_path).open('r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise SalesCalculationError(f"Missing required file: {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise SalesCalculationError(f"Invalid JSON format in {file_path}")

def to_decimal(value: str, label: str) -> Decimal:
    """Convert string to Decimal with error handling"""
    try:
        return Decimal(str(value)).quantize(DECIMAL_PLACES)
    except (InvalidOperation, TypeError) as e:
        logger.error(f"Invalid {label} value: {value}")
        raise SalesCalculationError(f"Invalid {label} value: {value}")

def calculate_sales_metrics(
    orders_data: List[Dict],
    products_data: List[Dict],
    discounts_data: List[Dict]
) -> SalesMetrics:
    """Calculate sales metrics with error handling and logging"""
    logger.info("Starting sales metrics calculation")
    
    try:
    
        products = {
            p["sku"]: to_decimal(p["price"], "price")
            for p in products_data
        }
        discounts = {
            d["key"]: to_decimal(d["value"], "discount")
            for d in discounts_data
        }

        # Initialize counters
        total_before = ZERO
        total_after = ZERO
        total_discount = ZERO
        orders_with_discount = 0
        total_orders = len(orders_data)

        # Process orders
        for order in orders_data:
            try:
                # Calculate order total
                order_total = sum(
                    products[item["sku"]] * to_decimal(item["quantity"], "quantity")
                    for item in order["items"]
                )

                # Apply stacking discounts if present
                discount_amount = ZERO
                if discount_codes := order.get("discount"):
                    # Split discount codes by comma and calculate total discount
                    codes = [code.strip() for code in discount_codes.split(",")]
                    total_discount_percentage = sum(
                        discounts[code] for code in codes if code in discounts
                    )
                    
                    if total_discount_percentage > ZERO:
                        discount_amount = order_total * total_discount_percentage
                        orders_with_discount += 1
                    else:
                        logger.warning(f"Invalid discount code(s): {discount_codes}")

                # Update totals
                total_before += order_total
                total_discount += discount_amount
                total_after += (order_total - discount_amount)

            except KeyError as e:
                logger.error(f"Missing required field in order {order.get('orderId', 'unknown')}: {e}")
                raise SalesCalculationError(f"Invalid order data: {e}")

        # Calculate average discount
        avg_discount = (
            (total_discount / total_before) * HUNDRED
            if total_before > ZERO and orders_with_discount > 0
            else ZERO
        )

        metrics = SalesMetrics(
            total_before_discount=total_before,
            total_after_discount=total_after,
            total_discount_amount=total_discount,
            orders_with_discount=orders_with_discount,
            total_orders=total_orders,
            average_discount_percentage=avg_discount
        )

        logger.info("Sales metrics calculation completed successfully")
        return metrics

    except Exception as e:
        logger.error(f"Error calculating sales metrics: {e}")
        raise SalesCalculationError(f"Failed to calculate sales metrics: {e}")

def main() -> None:
    try:
        logger.info("Loading sales data files")
        orders = load_json_data("data/orders.json")
        products = load_json_data("data/products.json")
        discounts = load_json_data("data/discounts.json")

        metrics = calculate_sales_metrics(orders, products, discounts)
        print(json.dumps(metrics.to_dict(), indent=2))
        logger.info("Process completed successfully")

    except SalesCalculationError as e:
        logger.error(f"Sales calculation failed: {e}")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()