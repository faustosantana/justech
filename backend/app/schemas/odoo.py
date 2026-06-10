from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OdooHealthResponse(BaseModel):
    connected: bool
    read_only: bool = True
    version: str | None = None
    database: str | None = None
    message: str
    active_company_id: int | None = None
    active_company_name: str | None = None


class OdooCompanyResponse(BaseModel):
    id: int
    name: str
    currency_id: int | None = None
    currency_name: str | None = None
    partner_id: int | None = None
    is_active: bool = True
    selected_by_current_user: bool = False


class OdooCompaniesResponse(BaseModel):
    items: list[OdooCompanyResponse]
    connected: bool = True
    message: str | None = None


class OdooCompanyContextResponse(BaseModel):
    selected: bool = False
    odoo_company_id: int | None = None
    odoo_company_name: str | None = None
    is_default: bool = True
    selected_at: datetime | None = None
    message: str | None = None


class OdooCompanyContextUpdate(BaseModel):
    odoo_company_id: int


class OdooUserMappingResponse(BaseModel):
    id: UUID | None = None
    tenant_id: UUID
    jaios_user_id: UUID
    odoo_user_id: int
    odoo_login: str
    odoo_partner_id: int | None = None
    allowed_company_ids: list[int] = Field(default_factory=list)
    default_company_id: int | None = None
    is_active: bool = True
    last_verified_at: datetime | None = None


class OdooLinkUserRequest(BaseModel):
    odoo_login: str


class OdooMeResponse(BaseModel):
    jaios_user_id: UUID
    jaios_email: str
    jaios_name: str
    odoo_connected: bool
    read_only: bool = True
    company_context: OdooCompanyContextResponse
    user_mapping: OdooUserMappingResponse | None = None


class OdooSummaryResponse(BaseModel):
    customers: int = 0
    products: int = 0
    open_invoices: int = 0
    overdue_invoices: int = 0
    quotations: int = 0
    opportunities: int = 0
    projects: int = 0
    connected: bool = False
    company_id: int | None = None
    company_name: str | None = None


class OdooCustomerResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    vat: str | None = None
    city: str | None = None
    is_company: bool = False


class OdooProductResponse(BaseModel):
    id: int
    name: str
    default_code: str | None = None
    list_price: Decimal = Decimal("0")
    standard_price: Decimal = Decimal("0")
    qty_available: float = 0
    uom: str | None = None


class OdooSaleHistoryItem(BaseModel):
    id: int
    order_name: str
    order_date: str | None = None
    partner_id: int | None = None
    partner_name: str
    product_id: int | None = None
    product_name: str
    quantity: float
    unit_price: Decimal
    subtotal: Decimal
    margin: Decimal | None = None
    margin_pct: float | None = None


class OdooLastPriceResponse(BaseModel):
    product_name: str | None = None
    partner_name: str | None = None
    unit_price: Decimal | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    order_date: str | None = None
    order_name: str | None = None
    average_price: Decimal | None = None
    sales_count: int = 0


class OdooVendorResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    vat: str | None = None


class OdooProductPurchaseItem(BaseModel):
    id: int
    vendor_name: str
    order_name: str
    order_date: str | None = None
    quantity: float
    unit_price: Decimal
    subtotal: Decimal


class OdooProductSuppliedItem(BaseModel):
    product_id: int
    product_name: str
    last_cost: Decimal | None = None
    average_cost: Decimal | None = None
    total_qty: float = 0
    purchase_count: int = 0


class OdooInvoiceResponse(BaseModel):
    id: int
    name: str
    partner_name: str
    invoice_date: str | None = None
    due_date: str | None = None
    amount_total: Decimal
    amount_residual: Decimal
    currency: str = "DOP"
    state: str
    payment_state: str | None = None


class OdooQuotationLineResponse(BaseModel):
    product_id: int | None = None
    product_name: str
    description: str | None = None
    quantity: float = 0
    price_unit: Decimal = Decimal("0")
    discount: float = 0
    subtotal: Decimal = Decimal("0")
    taxes: list[str] = Field(default_factory=list)


class OdooQuotationResponse(BaseModel):
    id: int
    name: str
    partner_id: int | None = None
    partner_name: str
    date_order: str | None = None
    amount_total: Decimal
    currency: str = "DOP"
    state: str
    user_id: int | None = None
    salesperson_name: str | None = None
    company_id: int | None = None
    company_name: str | None = None
    validity_date: str | None = None


class OdooQuotationDetailResponse(OdooQuotationResponse):
    lines: list[OdooQuotationLineResponse] = Field(default_factory=list)
    connected: bool = True
    message: str | None = None


class OdooQuotationSearchParams(BaseModel):
    q: str | None = None
    quotation_number: str | None = None
    customer: str | None = None
    salesperson: str | None = None
    product: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    state: str | None = None
    company_id: int | None = None
    limit: int = 50


class OdooOpportunityResponse(BaseModel):
    id: int
    name: str
    partner_name: str | None = None
    expected_revenue: Decimal = Decimal("0")
    probability: float = 0
    stage: str | None = None
    date_deadline: str | None = None


class OdooProjectResponse(BaseModel):
    id: int
    name: str
    partner_name: str | None = None
    stage: str | None = None


class OdooTicketResponse(BaseModel):
    id: int
    name: str
    partner_name: str | None = None
    stage: str | None = None
    priority: str | None = None


class OdooPurchaseHistoryItem(BaseModel):
    id: int
    order_name: str
    order_date: str | None = None
    partner_name: str
    product_name: str
    quantity: float
    unit_price: Decimal
    subtotal: Decimal


class OdooQueryResponse(BaseModel):
    question: str
    answer: str
    data: dict[str, Any] = Field(default_factory=dict)
    query_type: str


class OdooListResponse(BaseModel):
    items: list[Any]
    total: int
    connected: bool = True
    message: str | None = None
    company_id: int | None = None


class OdooInvoiceLineResponse(BaseModel):
    id: int
    product_id: int | None = None
    product_name: str
    quantity: float
    unit_price: Decimal
    discount: float = 0
    tax_names: str | None = None
    subtotal: Decimal
    cost: Decimal | None = None
    margin: Decimal | None = None
    margin_pct: float | None = None


class OdooProductPurchasedItem(BaseModel):
    product_id: int
    product_name: str
    last_price: Decimal | None = None
    average_price: Decimal | None = None
    total_qty: float = 0
    sales_count: int = 0


class OdooCustomerDetailResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    vat: str | None = None
    city: str | None = None
    salesperson: str | None = None
    company_name: str | None = None
    connected: bool = True
    open_invoices: list[OdooInvoiceResponse] = Field(default_factory=list)
    overdue_invoices: list[OdooInvoiceResponse] = Field(default_factory=list)
    quotations: list[OdooQuotationResponse] = Field(default_factory=list)
    opportunities: list[OdooOpportunityResponse] = Field(default_factory=list)
    projects: list[OdooProjectResponse] = Field(default_factory=list)
    sales_history: list[OdooSaleHistoryItem] = Field(default_factory=list)
    products_purchased: list[OdooProductPurchasedItem] = Field(default_factory=list)
    total_sales_historical: Decimal = Decimal("0")
    total_due: Decimal = Decimal("0")
    total_overdue: Decimal = Decimal("0")
    message: str | None = None


class OdooProductBuyerItem(BaseModel):
    partner_id: int
    partner_name: str
    last_price: Decimal | None = None
    average_price: Decimal | None = None
    sales_count: int = 0


class OdooProductDetailResponse(BaseModel):
    id: int
    name: str
    default_code: str | None = None
    category: str | None = None
    list_price: Decimal = Decimal("0")
    standard_price: Decimal = Decimal("0")
    qty_available: float = 0
    uom: str | None = None
    connected: bool = True
    sales_history: list[OdooSaleHistoryItem] = Field(default_factory=list)
    purchase_history: list[OdooProductPurchaseItem] = Field(default_factory=list)
    buyers: list[OdooProductBuyerItem] = Field(default_factory=list)
    last_price: Decimal | None = None
    average_price: Decimal | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    estimated_margin_pct: float | None = None
    related_invoices: list[OdooInvoiceResponse] = Field(default_factory=list)
    related_quotations: list[OdooQuotationResponse] = Field(default_factory=list)
    message: str | None = None


class OdooInvoiceDetailResponse(BaseModel):
    id: int
    name: str
    partner_id: int
    partner_name: str
    invoice_date: str | None = None
    due_date: str | None = None
    amount_total: Decimal
    amount_residual: Decimal
    currency: str = "DOP"
    state: str
    payment_state: str | None = None
    lines: list[OdooInvoiceLineResponse] = Field(default_factory=list)
    total_margin: Decimal | None = None
    margin_pct: float | None = None
    odoo_url: str | None = None
    connected: bool = True
    message: str | None = None


class OdooVendorDetailResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    vat: str | None = None
    city: str | None = None
    connected: bool = True
    purchase_history: list[OdooPurchaseHistoryItem] = Field(default_factory=list)
    products_supplied: list[OdooProductSuppliedItem] = Field(default_factory=list)
    total_purchase_value: Decimal = Decimal("0")
    purchase_orders: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None
