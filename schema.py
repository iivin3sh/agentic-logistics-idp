from pydantic import BaseModel, Field
from typing import List

# ==========================================
# 1. BILL OF LADING BLUEPRINTS
# ==========================================
class ContainerItem(BaseModel):
    container_number: str = Field(description="The unique identification marking code printed on the container body")
    seal_number: str = Field(description="The high-security custom seal clip lock reference code")

class BillOfLadingSchema(BaseModel):
    bl_number: str = Field(description="The unique Bill of Lading tracking bill number reference")
    shipper_name: str = Field(description="The exporter/supplier loading the cargo manifest")
    consignee_name: str = Field(description="The buyer or delivery receiver of the cargo")
    vessel_name: str = Field(description="The maritime vessel transport freight cargo ship name")
    voyage_number: str = Field(description="The scheduled operational transport voyage tracking code")
    port_of_loading: str = Field(description="The origin seaport where the goods are loaded onboard")
    port_of_discharge: str = Field(description="The final target seaport warehouse arrival location")
    total_weight_kg: float = Field(description="The total registered weight mass of all cargo metrics combined")
    containers: List[ContainerItem] = Field(description="The collection list of individual shipping containers linked")

# ==========================================
# 2. COMMERCIAL INVOICE BLUEPRINTS
# ==========================================
class InvoiceItem(BaseModel):
    description: str = Field(description="Detailed text description of the product or item sold")
    quantity: int = Field(description="The exact number of item units supplied")
    unit_price: float = Field(description="The individual price of a single unit item")

class CommercialInvoiceSchema(BaseModel):
    invoice_number: str = Field(description="The unique tracking invoice identification reference code")
    invoice_date: str = Field(description="The official issuance date printed on the document layout")
    vendor_name: str = Field(description="The seller, manufacturer, or supplier corporate name")
    buyer_name: str = Field(description="The buyer, importer, or purchasing company entity name")
    currency: str = Field(description="The transaction billing currency format abbreviation, e.g., QAR, USD, EUR")
    grand_total: float = Field(description="The final total summary billing settlement cost calculated")
    items: List[InvoiceItem] = Field(description="The comprehensive line item breakdown parsed from invoice tables")

# ==========================================
# 3. PACKING LIST BLUEPRINTS
# ==========================================
class PackingItem(BaseModel):
    package_type: str = Field(description="Type of outer containment, e.g., Pallet, Crate, Carton, Box")
    package_count: int = Field(description="The total number of units for this package row block")
    item_description: str = Field(description="Clear breakdown description of the items stored within")
    net_weight_kg: float = Field(description="The exact mass weight of the goods alone excluding packing materials")
    gross_weight_kg: float = Field(description="The total gross weight of the items including packing boxes/pallets")

class PackingListSchema(BaseModel):
    packing_list_number: str = Field(description="The unique tracking document id code for this packing manifest")
    bl_reference: str = Field(description="The associated cross-linked Bill of Lading reference tracker code")
    total_packages: int = Field(description="The combined sum total count of all individual package items loaded")
    total_gross_mass: float = Field(description="The total aggregate bulk weight indicator across all item rows")
    packages: List[PackingItem] = Field(description="Detailed step-by-step breakdown grid rows of individual packages")

# ==========================================
# 4. SUPPLIER QUOTATION BLUEPRINTS
# ==========================================
class QuoteItemLine(BaseModel):
    item_number: str = Field(description="The row or sequence position index number from the table grid, e.g., '10', '20'")
    product_code: str = Field(description="The material product part code, catalog index, or reference number, e.g., '911401844585'")
    description: str = Field(description="Full item text description of the lighting fixtures or supply specifications")
    quantity: int = Field(description="The quantity requirement or quoted count allocated for this line row")
    unit_price: float = Field(description="The standard net unit price of the item row after structural discounts")
    total_price: float = Field(description="The computed total net price for this row block line (quantity x unit price)")

class SupplierQuotationSchema(BaseModel):
    quote_number: str = Field(description="The primary Quote identification reference reference number, e.g., '177784.2'")
    project_name: str = Field(description="The project name background context listed on the header, e.g., 'IMC CLINICS @ JEDDAH'")
    date: str = Field(description="The creation generation date of the quotation, e.g., '07-APR-26'")
    currency: str = Field(description="The currency format tracking key utilized for row prices, e.g., SAR, QAR, USD")
    grand_total: float = Field(description="The complete summarized Quote Commercial Value statement summary")
    items: List[QuoteItemLine] = Field(description="The list of nested item rows parsed perfectly from the multi-page document grid")

# ==========================================
# 5. NEW LOGISTICS OPERATIONAL ARCHITECTURES
# ==========================================

class CertificateOfOriginSchema(BaseModel):
    coo_certificate_number: str = Field(description="The unique Certificate of Origin legal serial reference identification number")
    country_of_origin: str = Field(description="The formal manufacturing origin country location certification, e.g., 'Made in Oman', 'Germany'")
    exporter_details: str = Field(description="The registered commercial exporter or supplier firm profile text details")

class DeliveryNoteItemLine(BaseModel):
    item_number: str = Field(description="Line position increment tracker sequence index matching delivery receipt")
    product_code: str = Field(description="The inventory material identifier code printed on the arrival sheet")
    actual_received_quantity: int = Field(description="The hard physical unit quantity counted and verified at warehouse intake")
    damaged_shortage_notes: str = Field(description="Specific written notes detailing anomalies, count differences, or product cracks. Use 'None' if clear.")

class DeliveryNoteSchema(BaseModel):
    delivery_note_number: str = Field(description="The unique delivery docket or warehouse receiving ticket voucher string reference")
    received_date: str = Field(description="The physical date stamp when logistics assets arrived at delivery facility location")
    items: List[DeliveryNoteItemLine] = Field(description="The array list capturing individual incoming material item allocations parsed from delivery documents")

class WaybillSchema(BaseModel):
    awb_number: str = Field(description="The core 11-digit master shipping transport identification key tracking code or sea waybill track indicator")
    flight_or_vessel_number: str = Field(description="The specific air cargo flight configuration code identifier, or maritime line identity track number")
    flight_or_vessel_date: str = Field(description="The designated departure calendar timeline date tracking the movement framework")
    chargeable_weight: float = Field(description="The commercial chargeable weight assessment factor utilized for transport cost structures")

class CustomsDeclarationItemLine(BaseModel):
    item_number: str = Field(description="The row item grid map alignment sequence tracker number index")
    hs_code: str = Field(description="The exact 8-to-10 digit Harmonized System international code applied for classification profiles")

class CustomsDeclarationSchema(BaseModel):
    declaration_number: str = Field(description="The government system reference identification clearance tracking log number, e.g., Al-Nadeeb platform log")
    duty_fees_paid: float = Field(description="The numeric currency tariff custom charge parameters calculated by port border framework control nodes")
    tax_fees_paid: float = Field(description="The secondary tax parameters assessed upon entry calculations during terminal staging")
    items: List[CustomsDeclarationItemLine] = Field(description="The complete multi-line array logging item codes processed on government submission paperwork")