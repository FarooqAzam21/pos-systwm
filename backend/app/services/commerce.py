from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.business import Business
from app.models.payment import Payment, PaymentMethod, PaymentReferenceType, PaymentType
from app.models.product import Product
from app.models.purchase import Purchase, PurchaseItem, PurchasePaymentStatus
from app.models.sale import Sale, SaleItem, SalePaymentStatus, SaleStatus
from app.models.sale_return import SaleReturn, SaleReturnItem
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.commerce import CustomerCreate, CustomerPaymentCreate, CustomerUpdate, PurchaseCreate, SaleCreate, SalePaymentCreate, SaleReturnCreate, SupplierPaymentCreate
from app.services.dates import business_datetime_bounds, get_business_timezone

CENT = Decimal("0.01")
ZERO = Decimal("0")


def money(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def allocate_amount(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    amount = money(amount)
    total_weight = sum(weights, ZERO)
    if amount == ZERO:
        return [ZERO for _ in weights]
    if total_weight <= ZERO:
        raise HTTPException(status_code=409, detail="Unable to allocate sale-level adjustments")

    total_cents = int(amount * 100)
    exact_cents = [Decimal(total_cents) * weight / total_weight for weight in weights]
    allocated_cents = [int(value.to_integral_value(rounding=ROUND_DOWN)) for value in exact_cents]
    remaining_cents = total_cents - sum(allocated_cents)
    order = sorted(
        range(len(weights)),
        key=lambda index: exact_cents[index] - allocated_cents[index],
        reverse=True,
    )
    for index in order[:remaining_cents]:
        allocated_cents[index] += 1
    return [Decimal(value) / 100 for value in allocated_cents]


def not_found(label: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def payment_status(paid: Decimal, total: Decimal) -> PurchasePaymentStatus | SalePaymentStatus:
    if paid == 0:
        return PurchasePaymentStatus.UNPAID
    if paid >= total:
        return PurchasePaymentStatus.PAID
    return PurchasePaymentStatus.PARTIAL


def serialize_sale(sale: Sale, customer_name: str | None = None, cashier_name: str | None = None) -> dict:
    return {
        "id": sale.id,
        "business_id": sale.business_id,
        "invoice_number": sale.invoice_number,
        "customer_id": sale.customer_id,
        "sale_date": sale.sale_date,
        "subtotal": sale.subtotal,
        "discount": sale.discount,
        "tax": sale.tax,
        "total_amount": sale.total_amount,
        "paid_amount": sale.paid_amount,
        "outstanding_amount": sale.outstanding_amount,
        "payment_status": sale.payment_status.value,
        "cogs_amount": sale.cogs_amount,
        "gross_profit": sale.gross_profit,
        "status": sale.status.value,
        "created_by": sale.created_by,
        "created_at": sale.created_at,
        "customer_name": customer_name,
        "cashier_name": cashier_name,
    }


def remove_sale_cost_details(sale_data: dict) -> dict:
    sale_data.pop("cogs_amount", None)
    sale_data.pop("gross_profit", None)
    for item in sale_data.get("items", []):
        item.pop("unit_cost", None)
        item.pop("cogs", None)
        item.pop("gross_profit", None)
    return sale_data


def serialize_payment(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "business_id": payment.business_id,
        "payment_type": payment.payment_type.value,
        "reference_type": payment.reference_type.value,
        "reference_id": payment.reference_id,
        "customer_id": payment.customer_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method.value,
        "payment_date": payment.payment_date,
        "reference_number": payment.reference_number,
        "notes": payment.notes,
        "received_by": payment.received_by,
        "created_at": payment.created_at,
    }


def serialize_return(record: SaleReturn) -> dict:
    return {
        "id": record.id,
        "business_id": record.business_id,
        "sale_id": record.sale_id,
        "refund_amount": record.refund_amount,
        "notes": record.notes,
        "created_by": record.created_by,
        "created_at": record.created_at,
    }


def create_customer(db: Session, business_id, payload: CustomerCreate) -> Customer:
    if payload.phone and db.scalar(select(Customer.id).where(
        Customer.business_id == business_id,
        Customer.phone == payload.phone,
    )):
        raise HTTPException(status_code=409, detail="A customer with this phone number already exists")
    customer = Customer(
        business_id=business_id,
        name=payload.name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        email=payload.email.strip().lower() if payload.email else None,
        address=payload.address.strip() if payload.address else None,
        city=payload.city.strip() if payload.city else None,
        tax_number=payload.tax_number.strip() if payload.tax_number else None,
        credit_limit=money(payload.credit_limit),
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(customer)
    db.flush()
    return customer


def update_customer(db: Session, customer: Customer, payload: CustomerUpdate) -> Customer:
    values = payload.model_dump(exclude_unset=True)
    if "current_balance" in values:
        raise HTTPException(status_code=422, detail="Customer balance is changed only by financial transactions")
    if values.get("phone"):
        duplicate = db.scalar(select(Customer.id).where(
            Customer.business_id == customer.business_id,
            Customer.phone == values["phone"],
            Customer.id != customer.id,
        ))
        if duplicate:
            raise HTTPException(status_code=409, detail="A customer with this phone number already exists")
    for field, value in values.items():
        if field == "credit_limit" and value is not None:
            value = money(value)
        if isinstance(value, str):
            value = value.strip()
            if field == "email":
                value = value.lower()
        setattr(customer, field, value)
    return customer


def create_purchase(db: Session, user: User, payload: PurchaseCreate) -> Purchase:
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == payload.supplier_id,
            Supplier.business_id == user.business_id,
            Supplier.is_active.is_(True),
        ).with_for_update()
    )
    if supplier is None:
        raise not_found("Supplier")
    invoice = payload.invoice_number.strip()
    if db.scalar(select(Purchase.id).where(Purchase.business_id == user.business_id, Purchase.invoice_number == invoice)):
        raise HTTPException(status_code=409, detail="A purchase with this invoice number already exists")

    product_ids = sorted({item.product_id for item in payload.items}, key=str)
    products = db.scalars(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.business_id == user.business_id,
            Product.is_active.is_(True),
        ).order_by(Product.id).with_for_update()
    ).all()
    product_by_id = {item.id: item for item in products}
    if len(product_by_id) != len(product_ids):
        raise not_found("Product")

    line_data = []
    subtotal = ZERO
    item_discounts = ZERO
    item_taxes = ZERO
    for row in payload.items:
        product = product_by_id[row.product_id]
        gross = money(row.quantity * row.unit_cost)
        line_discount = money(row.discount)
        line_tax = money(row.tax)
        if line_discount > gross:
            raise HTTPException(status_code=422, detail=f"Discount exceeds the purchase line amount for {product.name}")
        total = money(gross - line_discount + line_tax)
        subtotal += gross
        item_discounts += line_discount
        item_taxes += line_tax
        line_data.append((row, product, total))

    subtotal = money(subtotal)
    discount = money(item_discounts + payload.discount)
    tax = money(item_taxes + payload.tax)
    if discount > subtotal:
        raise HTTPException(status_code=422, detail="Purchase discount exceeds subtotal")
    total_amount = money(subtotal - discount + tax)
    paid = money(payload.paid_amount)
    if paid > total_amount:
        raise HTTPException(status_code=422, detail="Paid amount cannot exceed purchase total")
    outstanding = money(total_amount - paid)

    purchase = Purchase(
        business_id=user.business_id,
        supplier_id=supplier.id,
        invoice_number=invoice,
        purchase_date=payload.purchase_date or date.today(),
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total_amount=total_amount,
        paid_amount=paid,
        outstanding_amount=outstanding,
        payment_status=payment_status(paid, total_amount),
        notes=payload.notes.strip() if payload.notes else None,
        created_by=user.id,
    )
    db.add(purchase)
    db.flush()

    for row, product, total in line_data:
        quantity = Decimal(row.quantity)
        previous = Decimal(product.current_stock)
        old_cost = Decimal(product.cost_price)
        new_cost = Decimal(row.unit_cost)
        new_stock = previous + quantity
        weighted_cost = money(((previous * old_cost) + (quantity * new_cost)) / new_stock) if new_stock else new_cost
        product.current_stock = new_stock
        product.cost_price = weighted_cost
        db.add(PurchaseItem(
            business_id=user.business_id,
            purchase_id=purchase.id,
            product_id=product.id,
            quantity=quantity,
            unit_cost=new_cost,
            discount=money(row.discount),
            tax=money(row.tax),
            total=total,
        ))
        db.add(StockMovement(
            business_id=user.business_id,
            product_id=product.id,
            movement_type=MovementType.PURCHASE,
            quantity=quantity,
            previous_stock=previous,
            new_stock=new_stock,
            unit_cost=weighted_cost,
            reference_type="purchase",
            reference_id=str(purchase.id),
            notes=f"Purchase invoice {invoice}",
            created_by=user.id,
        ))
    if paid:
        db.add(Payment(
            business_id=user.business_id,
            payment_type=PaymentType.OUTGOING,
            reference_type=PaymentReferenceType.PURCHASE,
            reference_id=str(purchase.id),
            amount=paid,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            notes="Supplier payment",
            received_by=user.id,
        ))
    db.flush()
    return purchase


def checkout(db: Session, user: User, payload: SaleCreate) -> Sale:
    customer = None
    if payload.customer_id and payload.new_customer:
        raise HTTPException(status_code=422, detail="Choose an existing customer or add a new customer, not both")
    if payload.new_customer:
        customer = create_customer(db, user.business_id, payload.new_customer)
    elif payload.customer_id:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.business_id == user.business_id,
                Customer.is_active.is_(True),
            ).with_for_update()
        )
        if customer is None:
            raise not_found("Customer")

    product_ids = sorted({item.product_id for item in payload.items}, key=str)
    products = db.scalars(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.business_id == user.business_id,
            Product.is_active.is_(True),
        ).order_by(Product.id).with_for_update()
    ).all()
    product_by_id = {item.id: item for item in products}
    if len(product_by_id) != len(product_ids):
        raise not_found("Product")

    grouped_quantities: dict[object, Decimal] = {}
    subtotal = ZERO
    item_discounts = ZERO
    item_taxes = ZERO
    cogs = ZERO
    lines = []
    for row in payload.items:
        product = product_by_id[row.product_id]
        quantity = Decimal(row.quantity)
        grouped_quantities[product.id] = grouped_quantities.get(product.id, ZERO) + quantity
        unit_price = money(product.selling_price)
        unit_cost = money(product.cost_price)
        gross = money(quantity * unit_price)
        line_discount = money(row.discount)
        line_tax = money(row.tax)
        if line_discount > gross:
            raise HTTPException(status_code=422, detail=f"Discount exceeds the sale line amount for {product.name}")
        line_total = money(gross - line_discount + line_tax)
        line_cogs = money(quantity * unit_cost)
        subtotal += gross
        item_discounts += line_discount
        item_taxes += line_tax
        cogs += line_cogs
        lines.append((row, product, quantity, unit_price, unit_cost, line_discount, line_tax, line_total, line_cogs))

    for product_id, requested in grouped_quantities.items():
        product = product_by_id[product_id]
        if Decimal(product.current_stock) < requested:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for {product.name}; available {product.current_stock}, requested {requested}",
            )

    subtotal = money(subtotal)
    discount = money(item_discounts + payload.discount)
    tax = money(item_taxes + payload.tax)
    if discount > subtotal:
        raise HTTPException(status_code=422, detail="Sale discount exceeds subtotal")
    total = money(subtotal - discount + tax)
    paid = money(payload.paid_amount)
    if paid > total:
        raise HTTPException(status_code=422, detail="Paid amount cannot exceed sale total")
    outstanding = money(total - paid)
    if outstanding > 0 and customer is None:
        raise HTTPException(status_code=422, detail="Select a customer for a sale with an outstanding balance")

    sale = Sale(
        business_id=user.business_id,
        invoice_number=f"{user.business.invoice_prefix}-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}",
        customer_id=customer.id if customer else None,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total_amount=total,
        paid_amount=paid,
        outstanding_amount=outstanding,
        payment_status=payment_status(paid, total),
        cogs_amount=money(cogs),
        gross_profit=money(total - cogs),
        status=SaleStatus.COMPLETED,
        created_by=user.id,
    )
    db.add(sale)
    db.flush()

    for _, product, quantity, unit_price, unit_cost, line_discount, line_tax, line_total, line_cogs in lines:
        previous = Decimal(product.current_stock)
        new_stock = previous - quantity
        product.current_stock = new_stock
        db.add(SaleItem(
            business_id=user.business_id,
            sale_id=sale.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
            unit_cost=unit_cost,
            discount=line_discount,
            tax=line_tax,
            line_total=line_total,
            cogs=line_cogs,
            gross_profit=money(line_total - line_cogs),
        ))
        db.add(StockMovement(
            business_id=user.business_id,
            product_id=product.id,
            movement_type=MovementType.SALE,
            quantity=quantity,
            previous_stock=previous,
            new_stock=new_stock,
            unit_cost=unit_cost,
            reference_type="sale",
            reference_id=str(sale.id),
            notes=f"Sale {sale.invoice_number}",
            created_by=user.id,
        ))
    if paid:
        db.add(Payment(
            business_id=user.business_id,
            payment_type=PaymentType.INCOMING,
            reference_type=PaymentReferenceType.SALE,
            reference_id=str(sale.id),
            customer_id=customer.id if customer else None,
            amount=paid,
            payment_method=payload.payment_method,
            reference_number=payload.reference_number,
            notes=payload.notes,
            received_by=user.id,
        ))
    if customer and outstanding:
        customer.current_balance = money(Decimal(customer.current_balance) + outstanding)
    db.flush()
    return sale


def create_customer_payment(db: Session, user: User, payload: CustomerPaymentCreate) -> list[Payment]:
    customer = db.scalar(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.business_id == user.business_id,
            Customer.is_active.is_(True),
        ).with_for_update()
    )
    if customer is None:
        raise not_found("Customer")
    amount = money(payload.amount)
    if amount > Decimal(customer.current_balance):
        raise HTTPException(status_code=422, detail="Payment cannot exceed the customer's outstanding balance")
    open_sales = db.scalars(
        select(Sale).where(
            Sale.business_id == user.business_id,
            Sale.customer_id == customer.id,
            Sale.outstanding_amount > 0,
            Sale.status != SaleStatus.VOIDED,
        ).order_by(Sale.sale_date, Sale.created_at).with_for_update()
    ).all()
    remaining = amount
    payments = []
    for sale in open_sales:
        if remaining <= 0:
            break
        allocation = min(remaining, Decimal(sale.outstanding_amount))
        sale.paid_amount = money(Decimal(sale.paid_amount) + allocation)
        sale.outstanding_amount = money(Decimal(sale.total_amount) - Decimal(sale.paid_amount))
        sale.payment_status = payment_status(Decimal(sale.paid_amount), Decimal(sale.total_amount))
        payment = Payment(
            business_id=user.business_id,
            payment_type=PaymentType.INCOMING,
            reference_type=PaymentReferenceType.CUSTOMER_PAYMENT,
            reference_id=str(sale.id),
            customer_id=customer.id,
            amount=allocation,
            payment_method=payload.payment_method,
            payment_date=payload.payment_date or datetime.now(timezone.utc),
            reference_number=payload.reference_number,
            notes=payload.notes,
            received_by=user.id,
        )
        db.add(payment)
        payments.append(payment)
        remaining -= allocation
    if remaining > 0:
        raise HTTPException(status_code=409, detail="Customer balance does not match outstanding sale balances")
    customer.current_balance = money(Decimal(customer.current_balance) - amount)
    db.flush()
    return payments


def create_sale_payment(db: Session, user: User, payload: SalePaymentCreate) -> Payment:
    sale_scope = select(Sale).where(
        Sale.id == payload.sale_id,
        Sale.business_id == user.business_id,
    )
    sale = db.scalar(sale_scope)
    if sale is None:
        raise not_found("Sale")

    # Customer payments lock customer before sales; keep the same lock order to
    # avoid deadlocks when an account payment and invoice payment overlap.
    customer = None
    if sale.customer_id:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == sale.customer_id,
                Customer.business_id == user.business_id,
            ).with_for_update()
        )
    sale = db.scalar(sale_scope.with_for_update().execution_options(populate_existing=True))
    if sale is None:
        raise not_found("Sale")
    if sale.status == SaleStatus.VOIDED:
        raise HTTPException(status_code=422, detail="Cannot receive payment for a voided sale")

    amount = money(payload.amount)
    outstanding = Decimal(sale.outstanding_amount)
    if amount > outstanding:
        raise HTTPException(status_code=422, detail="Payment cannot exceed the sale outstanding balance")

    if customer and customer.id == sale.customer_id:
        customer.current_balance = money(max(ZERO, Decimal(customer.current_balance) - amount))

    sale.paid_amount = money(Decimal(sale.paid_amount) + amount)
    sale.outstanding_amount = money(outstanding - amount)
    sale.payment_status = payment_status(Decimal(sale.paid_amount), Decimal(sale.total_amount))
    payment = Payment(
        business_id=user.business_id,
        payment_type=PaymentType.INCOMING,
        reference_type=PaymentReferenceType.SALE,
        reference_id=str(sale.id),
        customer_id=sale.customer_id,
        amount=amount,
        payment_method=payload.payment_method,
        payment_date=payload.payment_date or datetime.now(timezone.utc),
        reference_number=payload.reference_number,
        notes=payload.notes,
        received_by=user.id,
    )
    db.add(payment)
    db.flush()
    return payment


def create_supplier_payment(db: Session, user: User, payload: SupplierPaymentCreate) -> Payment:
    purchase = db.scalar(
        select(Purchase)
        .where(Purchase.id == payload.purchase_id, Purchase.business_id == user.business_id)
        .with_for_update()
    )
    if purchase is None:
        raise not_found("Purchase")
    amount = money(payload.amount)
    outstanding = Decimal(purchase.outstanding_amount)
    if amount > outstanding:
        raise HTTPException(status_code=422, detail="Payment cannot exceed the purchase outstanding balance")

    purchase.paid_amount = money(Decimal(purchase.paid_amount) + amount)
    purchase.outstanding_amount = money(outstanding - amount)
    purchase.payment_status = payment_status(Decimal(purchase.paid_amount), Decimal(purchase.total_amount))
    payment = Payment(
        business_id=user.business_id,
        payment_type=PaymentType.OUTGOING,
        reference_type=PaymentReferenceType.PURCHASE,
        reference_id=str(purchase.id),
        amount=amount,
        payment_method=payload.payment_method,
        payment_date=payload.payment_date or datetime.now(timezone.utc),
        reference_number=payload.reference_number,
        notes=payload.notes or f"Supplier payment for {purchase.invoice_number}",
        received_by=user.id,
    )
    db.add(payment)
    db.flush()
    return payment


def process_return(db: Session, user: User, sale_id, payload: SaleReturnCreate) -> SaleReturn:
    sale = db.scalar(
        select(Sale).where(Sale.id == sale_id, Sale.business_id == user.business_id).with_for_update()
    )
    if sale is None:
        raise not_found("Sale")
    if sale.status in (SaleStatus.RETURNED, SaleStatus.VOIDED):
        raise HTTPException(status_code=409, detail="This sale cannot accept additional returns")

    requested_ids = {entry.sale_item_id for entry in payload.items}
    if len(requested_ids) != len(payload.items):
        raise HTTPException(status_code=422, detail="Each sale item may appear only once in a return")
    sale_items = db.scalars(
        select(SaleItem).where(
            SaleItem.sale_id == sale.id,
            SaleItem.business_id == user.business_id,
        ).with_for_update()
    ).all()
    by_id = {item.id: item for item in sale_items}
    if not requested_ids.issubset(by_id):
        raise not_found("Sale item")

    item_discounts = sum((Decimal(item.discount) for item in sale_items), ZERO)
    item_taxes = sum((Decimal(item.tax) for item in sale_items), ZERO)
    global_discount = Decimal(sale.discount) - item_discounts
    global_tax = Decimal(sale.tax) - item_taxes
    if global_discount < ZERO or global_tax < ZERO:
        raise HTTPException(status_code=409, detail="Sale adjustment totals do not match its items")
    discount_weights = [
        max(ZERO, money(Decimal(item.quantity) * Decimal(item.unit_price)) - Decimal(item.discount))
        for item in sale_items
    ]
    tax_weights = [
        money(Decimal(item.quantity) * Decimal(item.unit_price))
        for item in sale_items
    ]
    if sum(tax_weights, ZERO) == ZERO:
        tax_weights = [Decimal(item.quantity) for item in sale_items]
    allocated_discounts = allocate_amount(global_discount, discount_weights)
    allocated_taxes = allocate_amount(global_tax, tax_weights)
    adjustment_by_item = {
        item.id: (allocated_discounts[index], allocated_taxes[index])
        for index, item in enumerate(sale_items)
    }

    products = db.scalars(
        select(Product).where(
            Product.id.in_({item.product_id for item in sale_items}),
            Product.business_id == user.business_id,
        ).order_by(Product.id).with_for_update()
    ).all()
    product_by_id = {item.id: item for item in products}
    return_lines = []
    refund_total = ZERO
    cogs_total = ZERO
    for request in payload.items:
        line = by_id[request.sale_item_id]
        quantity = Decimal(request.quantity)
        previous_returned = Decimal(line.returned_quantity)
        available = Decimal(line.quantity) - Decimal(line.returned_quantity)
        if quantity > available:
            raise HTTPException(status_code=422, detail="Return quantity exceeds the quantity remaining for return")
        new_returned = previous_returned + quantity
        prior_line_value = (
            Decimal(line.line_total)
            if previous_returned == Decimal(line.quantity)
            else money(Decimal(line.line_total) * previous_returned / Decimal(line.quantity))
        )
        returned_line_value = (
            Decimal(line.line_total)
            if new_returned == Decimal(line.quantity)
            else money(Decimal(line.line_total) * new_returned / Decimal(line.quantity))
        )
        prior_cogs = (
            Decimal(line.cogs)
            if previous_returned == Decimal(line.quantity)
            else money(Decimal(line.cogs) * previous_returned / Decimal(line.quantity))
        )
        returned_cogs_total = (
            Decimal(line.cogs)
            if new_returned == Decimal(line.quantity)
            else money(Decimal(line.cogs) * new_returned / Decimal(line.quantity))
        )
        refund = money(returned_line_value - prior_line_value)
        returned_cogs = money(returned_cogs_total - prior_cogs)
        allocated_discount, allocated_tax = adjustment_by_item[line.id]
        prior_discount = (
            allocated_discount
            if previous_returned == Decimal(line.quantity)
            else money(allocated_discount * previous_returned / Decimal(line.quantity))
        )
        returned_discount = (
            allocated_discount
            if new_returned == Decimal(line.quantity)
            else money(allocated_discount * new_returned / Decimal(line.quantity))
        )
        prior_tax = (
            allocated_tax
            if previous_returned == Decimal(line.quantity)
            else money(allocated_tax * previous_returned / Decimal(line.quantity))
        )
        returned_tax = (
            allocated_tax
            if new_returned == Decimal(line.quantity)
            else money(allocated_tax * new_returned / Decimal(line.quantity))
        )
        refund = money(refund - (returned_discount - prior_discount) + (returned_tax - prior_tax))
        refund_total += refund
        cogs_total += returned_cogs
        return_lines.append((line, product_by_id[line.product_id], quantity, refund, returned_cogs))

    refund_total = money(refund_total)
    old_outstanding = Decimal(sale.outstanding_amount)
    debt_reduction = min(refund_total, old_outstanding)
    cash_refund = money(refund_total - debt_reduction)
    sale.total_amount = money(Decimal(sale.total_amount) - refund_total)
    sale.outstanding_amount = money(max(ZERO, old_outstanding - debt_reduction))
    sale.paid_amount = money(max(ZERO, Decimal(sale.paid_amount) - cash_refund))
    sale.cogs_amount = money(max(ZERO, Decimal(sale.cogs_amount) - cogs_total))
    sale.gross_profit = money(Decimal(sale.total_amount) - Decimal(sale.cogs_amount))
    sale.payment_status = payment_status(Decimal(sale.paid_amount), Decimal(sale.total_amount))

    return_record = SaleReturn(
        business_id=user.business_id,
        sale_id=sale.id,
        refund_amount=refund_total,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(return_record)
    db.flush()
    for line, product, quantity, refund, returned_cogs in return_lines:
        previous = Decimal(product.current_stock)
        product.current_stock = previous + quantity
        line.returned_quantity = Decimal(line.returned_quantity) + quantity
        db.add(SaleReturnItem(
            business_id=user.business_id,
            return_id=return_record.id,
            sale_item_id=line.id,
            product_id=product.id,
            quantity=quantity,
            refund_amount=refund,
            cogs=returned_cogs,
        ))
        db.add(StockMovement(
            business_id=user.business_id,
            product_id=product.id,
            movement_type=MovementType.RETURN,
            quantity=quantity,
            previous_stock=previous,
            new_stock=product.current_stock,
            unit_cost=line.unit_cost,
            reference_type="sale_return",
            reference_id=str(return_record.id),
            notes=f"Return for {sale.invoice_number}",
            created_by=user.id,
        ))
    if sale.customer_id and debt_reduction:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == sale.customer_id,
                Customer.business_id == user.business_id,
            ).with_for_update()
        )
        if customer is not None:
            customer.current_balance = money(max(ZERO, Decimal(customer.current_balance) - debt_reduction))
    if cash_refund:
        db.add(Payment(
            business_id=user.business_id,
            payment_type=PaymentType.OUTGOING,
            reference_type=PaymentReferenceType.REFUND,
            reference_id=str(return_record.id),
            customer_id=sale.customer_id,
            amount=cash_refund,
            payment_method=payload.payment_method,
            notes=f"Refund for {sale.invoice_number}",
            received_by=user.id,
        ))
    db.flush()
    remaining = db.scalar(
        select(func.count()).select_from(SaleItem).where(
            SaleItem.sale_id == sale.id,
            SaleItem.returned_quantity < SaleItem.quantity,
        )
    ) or 0
    sale.status = SaleStatus.PARTIALLY_RETURNED if remaining else SaleStatus.RETURNED
    db.flush()
    return return_record


def list_sales(db: Session, business_id, *, search: str | None, payment_status_filter: str | None,
               start_date: date | None, end_date: date | None, page: int, limit: int) -> dict:
    stmt = select(Sale).where(Sale.business_id == business_id)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.outerjoin(Customer, Customer.id == Sale.customer_id).where(
            or_(Sale.invoice_number.ilike(term), Customer.name.ilike(term))
        )
    if payment_status_filter:
        stmt = stmt.where(Sale.payment_status == SalePaymentStatus(payment_status_filter))
    if start_date:
        start_at, _ = business_datetime_bounds(db, business_id, start_date, start_date)
        stmt = stmt.where(Sale.sale_date >= start_at)
    if end_date:
        _, end_at = business_datetime_bounds(db, business_id, end_date, end_date)
        stmt = stmt.where(Sale.sale_date < end_at)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    sales = db.scalars(stmt.options(joinedload(Sale.items)).order_by(Sale.created_at.desc()).offset((page - 1) * limit).limit(limit)).unique().all()
    results = []
    for sale in sales:
        customer_name = db.scalar(select(Customer.name).where(
            Customer.id == sale.customer_id,
            Customer.business_id == business_id,
        )) if sale.customer_id else None
        cashier_name = db.scalar(select(User.name).where(
            User.id == sale.created_by,
            User.business_id == business_id,
        )) if sale.created_by else None
        results.append(serialize_sale(sale, customer_name, cashier_name))
    return {"items": results, "total": total, "page": page, "limit": limit}


def sale_details(db: Session, business_id, sale_id) -> dict:
    sale = db.scalar(
        select(Sale).where(Sale.id == sale_id, Sale.business_id == business_id).options(joinedload(Sale.items))
    )
    if sale is None:
        raise not_found("Sale")
    result = serialize_sale(
        sale,
        db.scalar(select(Customer.name).where(
            Customer.id == sale.customer_id,
            Customer.business_id == business_id,
        )) if sale.customer_id else None,
        db.scalar(select(User.name).where(
            User.id == sale.created_by,
            User.business_id == business_id,
        )) if sale.created_by else None,
    )
    if sale.customer_id:
        customer = db.scalar(select(Customer).where(
            Customer.id == sale.customer_id,
            Customer.business_id == business_id,
        ))
        result["customer_phone"] = customer.phone if customer else None
        result["customer_address"] = customer.address if customer else None
    else:
        result["customer_phone"] = None
        result["customer_address"] = None
    result["items"] = []
    for item in sale.items:
        product = db.scalar(select(Product).where(Product.id == item.product_id, Product.business_id == business_id))
        result["items"].append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product.name if product else "Product",
            "sku": product.sku if product else "",
            "quantity": item.quantity,
            "returned_quantity": item.returned_quantity,
            "unit_price": item.unit_price,
            "unit_cost": item.unit_cost,
            "discount": item.discount,
            "tax": item.tax,
            "line_total": item.line_total,
            "cogs": item.cogs,
            "gross_profit": item.gross_profit,
        })
    result["payments"] = [serialize_payment(payment) for payment in db.scalars(select(Payment).where(
        Payment.business_id == business_id,
        Payment.reference_type.in_((PaymentReferenceType.SALE, PaymentReferenceType.CUSTOMER_PAYMENT)),
        Payment.reference_id == str(sale.id),
    ).order_by(Payment.payment_date))]
    result["returns"] = [serialize_return(record) for record in db.scalars(select(SaleReturn).where(
        SaleReturn.business_id == business_id,
        SaleReturn.sale_id == sale.id,
    ).order_by(SaleReturn.created_at.desc()))]
    return result


def customer_detail(db: Session, business_id, customer_id) -> dict:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.business_id == business_id))
    if customer is None:
        raise not_found("Customer")
    sales = db.scalars(select(Sale).where(Sale.business_id == business_id, Sale.customer_id == customer.id).order_by(Sale.created_at.desc())).all()
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.business_id == business_id, Payment.customer_id == customer.id,
        Payment.payment_type == PaymentType.INCOMING,
    )) or ZERO
    result = {column.name: getattr(customer, column.name) for column in Customer.__table__.columns}
    result["total_purchases"] = money(sum((Decimal(sale.total_amount) for sale in sales), ZERO))
    result["total_paid"] = money(paid)
    result["transaction_count"] = len(sales)
    result["sales"] = [serialize_sale(sale) for sale in sales]
    result["payments"] = [serialize_payment(payment) for payment in db.scalars(select(Payment).where(
        Payment.business_id == business_id, Payment.customer_id == customer.id,
    ).order_by(Payment.payment_date.desc()).limit(100))]
    return_records = db.scalars(select(SaleReturn).join(Sale, Sale.id == SaleReturn.sale_id).where(
        SaleReturn.business_id == business_id, Sale.customer_id == customer.id,
    ).order_by(SaleReturn.created_at.desc()).limit(100)).all()
    result["returns"] = []
    for record in return_records:
        sale = db.scalar(select(Sale).where(Sale.id == record.sale_id, Sale.business_id == business_id))
        return_items = db.scalars(select(SaleReturnItem).where(
            SaleReturnItem.return_id == record.id,
            SaleReturnItem.business_id == business_id,
        )).all()
        items = []
        for return_item in return_items:
            product = db.scalar(select(Product).where(
                Product.id == return_item.product_id,
                Product.business_id == business_id,
            ))
            items.append({
                "product_id": return_item.product_id,
                "product_name": product.name if product else "Product",
                "quantity": return_item.quantity,
                "refund_amount": return_item.refund_amount,
            })
        result["returns"].append({
            **serialize_return(record),
            "invoice_number": sale.invoice_number if sale else None,
            "items": items,
        })
    return result


def dashboard_overview(db: Session, business_id, start_date: date, end_date: date) -> dict:
    business_tz = get_business_timezone(db, business_id)
    start_at, end_at = business_datetime_bounds(db, business_id, start_date, end_date)
    today = datetime.now(timezone.utc).astimezone(business_tz).date()
    today_start, today_end = business_datetime_bounds(db, business_id, today, today)
    today_sales = db.scalars(select(Sale).where(Sale.business_id == business_id, Sale.sale_date >= today_start, Sale.sale_date < today_end, Sale.status != SaleStatus.VOIDED)).all()
    outstanding = db.scalar(select(func.coalesce(func.sum(Customer.current_balance), 0)).where(
        Customer.business_id == business_id,
    )) or ZERO
    products = db.scalars(select(Product).where(Product.business_id == business_id, Product.is_active.is_(True))).all()
    inventory_value = sum((Decimal(p.current_stock) * Decimal(p.cost_price) for p in products), ZERO)
    low_stock = sum(1 for p in products if Decimal(p.current_stock) > 0 and Decimal(p.current_stock) <= Decimal(p.minimum_stock))
    out_of_stock = sum(1 for p in products if Decimal(p.current_stock) == ZERO)

    range_sales = db.scalars(select(Sale).where(
        Sale.business_id == business_id, Sale.sale_date >= start_at, Sale.sale_date < end_at, Sale.status != SaleStatus.VOIDED,
    )).all()
    sales_trend: dict[str, dict] = {}
    for sale in range_sales:
        sale_timestamp = sale.sale_date
        if sale_timestamp.tzinfo is None:
            sale_timestamp = sale_timestamp.replace(tzinfo=timezone.utc)
        sale_local_date = sale_timestamp.astimezone(business_tz).date()
        day = sale_local_date.isoformat()
        record = sales_trend.setdefault(day, {"date": day, "sales": ZERO, "gross_profit": ZERO})
        record["sales"] += Decimal(sale.total_amount)
        record["gross_profit"] += Decimal(sale.gross_profit)

    top_line_rows = db.execute(
        select(SaleItem, Sale, Product.id, Product.name, Product.sku)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .where(
            SaleItem.business_id == business_id,
            Sale.sale_date >= start_at,
            Sale.sale_date < end_at,
            Sale.status != SaleStatus.VOIDED,
        )
    ).all()
    top_products: dict[object, dict] = {}
    items_by_sale: dict[object, list[tuple[SaleItem, object, str, str]]] = {}
    sale_by_id: dict[object, Sale] = {}
    for item, sale, product_id, product_name, product_sku in top_line_rows:
        items_by_sale.setdefault(sale.id, []).append((item, product_id, product_name, product_sku))
        sale_by_id[sale.id] = sale
    for sale_id, sale_items in items_by_sale.items():
        sale = sale_by_id[sale_id]
        global_discount = Decimal(sale.discount) - sum(
            (Decimal(item.discount) for item, _, _, _ in sale_items), ZERO
        )
        global_tax = Decimal(sale.tax) - sum(
            (Decimal(item.tax) for item, _, _, _ in sale_items), ZERO
        )
        if global_discount < ZERO or global_tax < ZERO:
            raise HTTPException(status_code=409, detail="Sale adjustment totals do not match its items")
        discount_weights = [
            max(ZERO, money(Decimal(item.quantity) * Decimal(item.unit_price)) - Decimal(item.discount))
            for item, _, _, _ in sale_items
        ]
        tax_weights = [
            money(Decimal(item.quantity) * Decimal(item.unit_price))
            for item, _, _, _ in sale_items
        ]
        if sum(tax_weights, ZERO) == ZERO:
            tax_weights = [Decimal(item.quantity) for item, _, _, _ in sale_items]
        discounts = allocate_amount(global_discount, discount_weights)
        taxes = allocate_amount(global_tax, tax_weights)
        for index, (item, product_id, product_name, product_sku) in enumerate(sale_items):
            quantity = Decimal(item.quantity)
            returned = Decimal(item.returned_quantity)
            remaining_quantity = quantity - returned
            if remaining_quantity <= ZERO:
                continue
            remaining_line_total = money(Decimal(item.line_total) * remaining_quantity / quantity)
            remaining_discount = discounts[index] - money(discounts[index] * returned / quantity)
            remaining_tax = taxes[index] - money(taxes[index] * returned / quantity)
            product_totals = top_products.setdefault(
                product_id,
                {"name": product_name, "sku": product_sku, "quantity": ZERO, "revenue": ZERO},
            )
            product_totals["quantity"] += remaining_quantity
            product_totals["revenue"] += remaining_line_total - remaining_discount + remaining_tax
    top_products_list = sorted(
        (
            {
                "name": product["name"],
                "sku": product["sku"],
                "quantity": product["quantity"],
                "revenue": money(product["revenue"]),
            }
            for product in top_products.values()
        ),
        key=lambda product: product["revenue"],
        reverse=True,
    )[:5]
    payment_rows = db.execute(
        select(Payment.payment_method, func.sum(Payment.amount))
        .where(Payment.business_id == business_id, Payment.payment_type == PaymentType.INCOMING,
               Payment.payment_date >= start_at, Payment.payment_date < end_at)
        .group_by(Payment.payment_method)
    ).all()
    recent = db.scalars(select(Sale).where(Sale.business_id == business_id).order_by(Sale.created_at.desc()).limit(8)).all()
    recent_sales = [
        serialize_sale(sale, db.scalar(select(Customer.name).where(Customer.id == sale.customer_id)) if sale.customer_id else None)
        for sale in recent
    ]
    return {
        "today": {
            "sales": money(sum((Decimal(s.total_amount) for s in today_sales), ZERO)),
            "cogs": money(sum((Decimal(s.cogs_amount) for s in today_sales), ZERO)),
            "gross_profit": money(sum((Decimal(s.gross_profit) for s in today_sales), ZERO)),
            "transactions": len(today_sales),
        },
        "outstanding_customer_balance": money(outstanding),
        "inventory_value": money(inventory_value),
        "low_stock_products": low_stock,
        "out_of_stock_products": out_of_stock,
        "sales_trend": sorted(
            ({"date": value["date"], "sales": money(value["sales"]), "gross_profit": money(value["gross_profit"])} for value in sales_trend.values()),
            key=lambda item: item["date"],
        ),
        "top_products": top_products_list,
        "payment_methods": [{"method": row[0].value, "amount": row[1] or ZERO} for row in payment_rows],
        "recent_sales": recent_sales,
    }
