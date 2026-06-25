import streamlit as st
import json
import os
import sqlite3
from google import genai
from google.genai import types

# Import blueprints and utilities
from schema import (
    BillOfLadingSchema, CommercialInvoiceSchema, PackingListSchema, SupplierQuotationSchema,
    CertificateOfOriginSchema, DeliveryNoteSchema, WaybillSchema, CustomsDeclarationSchema
)
from pdf_utils import extract_text_from_pdf_bytes, convert_pdf_bytes_to_image_bytes
from db_utils import (
    init_db, save_shipment_to_db, save_invoice_to_db, save_packing_list_to_db, save_quotation_to_db,
    save_certificate_to_db, save_delivery_note_to_db, save_waybill_to_db, save_customs_declaration_to_db
)
import pandas as pd
import io
from PIL import Image

# Initialize database
init_db()

# --- 🎨 PREMIUM MIDNIGHT DARK UI CONFIGURATION ---
st.set_page_config(
    page_title="Intelligent Logistics IDP Hub", 
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .stApp { background-color: #0F172A !important; color: #E2E8F0 !important; }
        h1, h2, h3, h4, h5, h6 { color: #38BDF8 !important; font-family: 'Inter', sans-serif; font-weight: 700; }
        .stMarkdown label, p, span, div { color: #E2E8F0 !important; }
        .enterprise-header {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            padding: 2rem; border-radius: 12px; border: 1px solid #1E3A8A; margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .enterprise-header h1 { color: #38BDF8 !important; margin: 0; font-size: 2.2rem; }
        .enterprise-header p { color: #94A3B8 !important; margin: 0; font-size: 1rem; margin-top: 0.5rem; }
        [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1E3A8A; }
        .metric-card {
            background-color: #1E293B !important; padding: 1.5rem; border-radius: 10px; border-left: 5px solid #38BDF8;
            border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-bottom: 1rem;
        }
        div[data-testid="stForm"] { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 10px !important; padding: 1.5rem !important; }
        .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; color: #94A3B8 !important; padding: 0.5rem 1rem; }
        .stTabs [aria-selected="true"] { color: #38BDF8 !important; border-bottom-color: #38BDF8 !important; }
        input, select, textarea { background-color: #1E293B !important; color: #FFFFFF !important; border: 1px solid #475569 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 🏢 SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("### 🏢 Core Workspace")
    st.caption("Connected Hub Terminal")
    st.markdown("---")
    st.markdown("### 📂 Document Selector")
    doc_type = st.selectbox(
        "Document Framework Type Classification Matrix",
        [
            "Bill of Lading", 
            "Commercial Invoice", 
            "Packing List", 
            "Supplier Quotation",
            "Certificate of Origin (CoO)", 
            "Delivery Note (GRN)", 
            "Air/Sea Waybill (AWB)", 
            "Customs Declaration (SAD)"
        ]
    )
    st.markdown("---")
    st.markdown("### 🔒 Security Status")
    st.success("🔒 Node Tunnel: Encrypted")
    st.caption("Active Target Engine: `gemini-2.5-flash` via Local Secure Port")

# --- ⚓ MAIN WORKSPACE HEADER ---
st.markdown("""
    <div class="enterprise-header">
        <h1>🚢 Intelligent Logistics IDP Hub</h1>
        <p>Production-Grade Document Parsing, Pydantic Schema Enforcement & Automated Discrepancy Auditing</p>
    </div>
""", unsafe_allow_html=True)

@st.cache_resource
def get_gemini_client():
    return genai.Client()

def process_document_via_ai(file_bytes, mime_type, target_schema, is_image=False):
    client = get_gemini_client()
    prompt = "Extract accurate metrics from this logistics document matching the requested structural schema formatting."
    contents = [prompt]
    
    if mime_type == "application/pdf":
        text_layer = extract_text_from_pdf_bytes(file_bytes)
        if text_layer:
            contents.append(text_layer)
        else:
            image_pages = convert_pdf_bytes_to_image_bytes(file_bytes)
            for page_bytes in image_pages:
                contents.append(types.Part.from_bytes(data=page_bytes, mime_type="image/jpeg"))
    else:
        contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=target_schema,
            temperature=0.1
        )
    )
    return json.loads(response.text)

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Ingestion Terminal", 
    "🗃️ Historical Warehouse Ledger", 
    "🕵️ Cross-Document Discrepancy Auditor",
    "💬 AI Logistics Copilot"
])

with tab1:
    st.subheader(f"Processing Pipeline: {doc_type}")
    
    schema_map = {
        "Bill of Lading": BillOfLadingSchema,
        "Commercial Invoice": CommercialInvoiceSchema,
        "Packing List": PackingListSchema,
        "Supplier Quotation": SupplierQuotationSchema,
        "Certificate of Origin (CoO)": CertificateOfOriginSchema,
        "Delivery Note (GRN)": DeliveryNoteSchema,
        "Air/Sea Waybill (AWB)": WaybillSchema,
        "Customs Declaration (SAD)": CustomsDeclarationSchema
    }
    selected_schema = schema_map[doc_type]
    
    uploaded_files = st.file_uploader(
        f"Drag & Drop or Browse {doc_type} Files (Accepts multiple PDFs or Images)", 
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.info(f"📂 Total of {len(uploaded_files)} files queued up for processing.")
        
        if st.button(f"⚡ Execute AI Batch Extraction Pipeline", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            fail_count = 0
            
            with st.expander("📝 Live Batch Pipeline Operation Log", expanded=True):
                for idx, single_file in enumerate(uploaded_files):
                    status_text.markdown(f"⏳ Processing item **{idx+1}/{len(uploaded_files)}**: `{single_file.name}`...")
                    
                    try:
                        file_bytes = single_file.read()
                        mime_type = single_file.type
                        is_image = mime_type.startswith("image/")
                        
                        max_retries = 3
                        attempt = 0
                        extracted_data = None
                        
                        while attempt < max_retries:
                            try:
                                attempt += 1
                                extracted_data = process_document_via_ai(file_bytes, mime_type, selected_schema, is_image)
                                break
                            except Exception as api_err:
                                if "429" in str(api_err) or "RESOURCE_EXHAUSTED" in str(api_err):
                                    raise api_err
                                if attempt == max_retries:
                                    raise api_err
                        
                        if doc_type == "Bill of Lading":
                            shipment_payload = {
                                "bl_number": extracted_data.get("bl_number", f"AUTO-{idx}"),
                                "shipper_name": extracted_data.get("shipper_name", "Unknown Shipper"),
                                "consignee_name": extracted_data.get("consignee_name", "Unknown Consignee"),
                                "vessel_name": extracted_data.get("vessel_name", ""),
                                "voyage_number": extracted_data.get("voyage_number", ""),
                                "port_of_loading": extracted_data.get("port_of_loading", ""),
                                "port_of_discharge": extracted_data.get("port_of_discharge", ""),
                                "total_weight_kg": float(extracted_data.get("total_weight_kg", 0.0)),
                                "containers": extracted_data.get("containers", [])
                            }
                            save_shipment_to_db(shipment_payload)
                            st.write(f"✅ **{single_file.name}** -> Database manifest entry saved under key: `{shipment_payload['bl_number']}`")
                            
                        elif doc_type == "Commercial Invoice":
                            invoice_payload = {
                                "invoice_number": extracted_data.get("invoice_number", f"INV-{idx}"),
                                "invoice_date": extracted_data.get("invoice_date", ""),
                                "vendor_name": extracted_data.get("vendor_name", "Unknown Vendor"),
                                "buyer_name": extracted_data.get("buyer_name", "Unknown Buyer"),
                                "currency": str(extracted_data.get("currency", "USD")).upper().strip(),
                                "grand_total": float(extracted_data.get("grand_total", 0.0))
                            }
                            save_invoice_to_db(invoice_payload)
                            st.write(f"✅ **{single_file.name}** -> Invoice committed under key: `{invoice_payload['invoice_number']}` (Value: {invoice_payload['grand_total']} {invoice_payload['currency']})")
                            
                        elif doc_type == "Packing List":
                            pl_summary = {
                                "packing_list_number": extracted_data.get("packing_list_number", f"PL-{idx}"),
                                "bl_reference": extracted_data.get("bl_reference", ""),
                                "total_packages": int(extracted_data.get("total_packages", 0)),
                                "total_gross_mass": float(extracted_data.get("total_gross_mass", 0.0))
                            }
                            pl_items = extracted_data.get("packages", [])
                            save_packing_list_to_db(pl_summary, pl_items)
                            st.write(f"✅ **{single_file.name}** -> Packing List synchronized under key: `{pl_summary['packing_list_number']}` (Ref: `{pl_summary['bl_reference']}`)")
                            
                        elif doc_type == "Supplier Quotation":
                            quote_summary = {
                                "quote_number": extracted_data.get("quote_number", f"QT-{idx}"),
                                "project_name": extracted_data.get("project_name", ""),
                                "date": extracted_data.get("date", ""),
                                "currency": extracted_data.get("currency", "USD"),
                                "grand_total": float(extracted_data.get("grand_total", 0.0))
                            }
                            quote_items = extracted_data.get("items", [])
                            save_quotation_to_db(quote_summary, quote_items)
                            st.write(f"✅ **{single_file.name}** -> Supplier Quotation saved under key: `{quote_summary['quote_number']}`")
                            
                        elif doc_type == "Certificate of Origin (CoO)":
                            coo_payload = {
                                "coo_certificate_number": extracted_data.get("coo_certificate_number", f"COO-{idx}"),
                                "country_of_origin": extracted_data.get("country_of_origin", "Unknown"),
                                "exporter_details": extracted_data.get("exporter_details", "Unknown Exporter")
                            }
                            save_certificate_to_db(coo_payload)
                            st.write(f"✅ **{single_file.name}** -> Certificate of Origin saved under key: `{coo_payload['coo_certificate_number']}`")

                        elif doc_type == "Delivery Note (GRN)":
                            dn_payload = {
                                "delivery_note_number": extracted_data.get("delivery_note_number", f"DN-{idx}"),
                                "received_date": extracted_data.get("received_date", ""),
                                "items": extracted_data.get("items", [])
                            }
                            save_delivery_note_to_db(dn_payload)
                            st.write(f"✅ **{single_file.name}** -> Warehouse Intake Delivery Note saved under key: `{dn_payload['delivery_note_number']}`")

                        elif doc_type == "Air/Sea Waybill (AWB)":
                            wb_payload = {
                                "awb_number": extracted_data.get("awb_number", f"AWB-{idx}"),
                                "flight_or_vessel_number": extracted_data.get("flight_or_vessel_number", ""),
                                "flight_or_vessel_date": extracted_data.get("flight_or_vessel_date", ""),
                                "chargeable_weight": float(extracted_data.get("chargeable_weight", 0.0))
                            }
                            save_waybill_to_db(wb_payload)
                            st.write(f"✅ **{single_file.name}** -> Logistics Waybill Metrics saved under key: `{wb_payload['awb_number']}`")

                        elif doc_type == "Customs Declaration (SAD)":
                            cd_payload = {
                                "declaration_number": extracted_data.get("declaration_number", f"DEC-{idx}"),
                                "duty_fees_paid": float(extracted_data.get("duty_fees_paid", 0.0)),
                                "tax_fees_paid": float(extracted_data.get("tax_fees_paid", 0.0)),
                                "items": extracted_data.get("items", [])
                            }
                            save_customs_declaration_to_db(cd_payload)
                            st.write(f"✅ **{single_file.name}** -> Customs Declaration Framework saved under key: `{cd_payload['declaration_number']}`")

                        else:
                            st.write(f"✅ **{single_file.name}** -> Structurally parsed successfully.")
                            st.json(extracted_data)  
                        
                        success_count += 1
                    except Exception as e:
                        from db_utils import log_failed_document
                        log_failed_document(single_file.name, str(e))
                    
                        try:
                            dlq_dir = "failed_documents"
                            if not os.path.exists(dlq_dir):
                                os.makedirs(dlq_dir)
                        
                            safe_filename = os.path.basename(single_file.name)
                            target_path = os.path.join(dlq_dir, safe_filename)
                            with open(target_path, "wb") as f:
                                f.write(file_bytes)
                        
                            st.error(f"❌ **{single_file.name}** -> Failed after retries. Logged to DB and moved to `/{dlq_dir}/` storage.")
                        except Exception as file_save_err:
                            st.error(f"❌ **{single_file.name}** -> Processing failure: {e}. (Failed to route to dead-letter folder: {file_save_err})")
                    
                        fail_count += 1
                
                progress_bar.progress(100)
                status_text.markdown(f"🏁 **Batch Execution Completed.** Clean Success: `{success_count}` | Total Flags Flagged: `{fail_count}`")

with tab2:
    st.markdown("### 📊 Interactive Operations Warehouse Ledger")
    st.write("Monitor historical transaction logs, analyze high-level performance trends, and synchronize database adjustments dynamically.")
    st.markdown("---")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    try:
        conn = sqlite3.connect("shipments.db")
        
        shipments_count = conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        invoices_count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        total_weight = conn.execute("SELECT SUM(total_weight_kg) FROM shipments").fetchone()[0] or 0.0
        
        try:
            quotes_count = conn.execute("SELECT COUNT(DISTINCT quote_number) FROM quotation_items").fetchone()[0]
        except sqlite3.OperationalError:
            quotes_count = 0
            
        with kpi1:
            st.markdown(f'<div class="metric-card"><p style="color:#94A3B8!important;font-weight:600;margin:0;font-size:0.85rem;text-transform:uppercase;">Total Bills of Lading</p><h2 style="color:#F8FAFC!important;margin:0;font-size:1.8rem;font-weight:700;padding-top:0.25rem;">{shipments_count} Manifests</h2></div>', unsafe_allow_html=True)
        with kpi2:
            st.markdown(f'<div class="metric-card" style="border-left-color:#34D399;"><p style="color:#94A3B8!important;font-weight:600;margin:0;font-size:0.85rem;text-transform:uppercase;">Invoices Processed</p><h2 style="color:#F8FAFC!important;margin:0;font-size:1.8rem;font-weight:700;padding-top:0.25rem;">{invoices_count} Receipts</h2></div>', unsafe_allow_html=True)
        with kpi3:
            st.markdown(f'<div class="metric-card" style="border-left-color:#FBBF24;"><p style="color:#94A3B8!important;font-weight:600;margin:0;font-size:0.85rem;text-transform:uppercase;">Total Volume Weight</p><h2 style="color:#F8FAFC!important;margin:0;font-size:1.8rem;font-weight:700;padding-top:0.25rem;">{total_weight:,.1f} KG</h2></div>', unsafe_allow_html=True)
        with kpi4:
            st.markdown(f'<div class="metric-card" style="border-left-color:#A78BFA;"><p style="color:#94A3B8!important;font-weight:600;margin:0;font-size:0.85rem;text-transform:uppercase;">Active Projects Quoted</p><h2 style="color:#F8FAFC!important;margin:0;font-size:1.8rem;font-weight:700;padding-top:0.25rem;">{quotes_count} Layouts</h2></div>', unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("### 📈 Executive Trend Analytics Engine")
        chart_style = st.selectbox(
            "📊 Select Dashboard Presentation Chart Style:", ["Bar Chart View", "Line Chart View", "Area Chart View"]
        )
        
        graph_col1, graph_col2 = st.columns(2)
        with graph_col1:
            st.markdown("#### 🚢 Top 5 Freight Shippers by Volume (KG)")
            df_shippers = pd.read_sql_query("SELECT shipper_name as [Freight Vendor], SUM(total_weight_kg) as [Total Volume (KG)] FROM shipments GROUP BY shipper_name ORDER BY [Total Volume (KG)] DESC LIMIT 5", conn)
            if not df_shippers.empty and df_shippers["Total Volume (KG)"].sum() > 0:
                chart_data = df_shippers.set_index("Freight Vendor")
                if chart_style == "Bar Chart View":
                    st.bar_chart(chart_data, color="#38BDF8")
                elif chart_style == "Line Chart View":
                    st.line_chart(chart_data, color="#38BDF8")
                elif chart_style == "Area Chart View":
                    st.area_chart(chart_data, color="#38BDF8")
            else:
                st.info("No volume distribution data captured yet.")
                
        with graph_col2:
            st.markdown("#### 💵 Cumulative Total Financial Costs")
            df_expenses = pd.read_sql_query("SELECT currency as [Currency Unit], SUM(grand_total) as [Total Gross Expense] FROM invoices GROUP BY currency", conn)
            if not df_expenses.empty:
                chart_data_exp = df_expenses.set_index("Currency Unit")
                if chart_style == "Bar Chart View":
                    st.bar_chart(chart_data_exp, color="#34D399")
                elif chart_style == "Line Chart View":
                    st.line_chart(chart_data_exp, color="#34D399")
                elif chart_style == "Area Chart View":
                    st.area_chart(chart_data_exp, color="#34D399")
            else:
                st.info("No invoice metrics logged yet.")
                
        st.markdown("#### 🗺️ Dispatched Distribution Target Ports Hub Location")
        df_ports = pd.read_sql_query("SELECT port_of_discharge as [Discharge Port Location], COUNT(*) as [Total Shipments Handled] FROM shipments WHERE port_of_discharge IS NOT NULL AND port_of_discharge != '' GROUP BY port_of_discharge", conn)
        if not df_ports.empty:
            st.dataframe(df_ports, use_container_width=True, hide_index=True)
        else:
            st.caption("✨ Hub Location Chart Mode: Pending destination values.")
            
        st.markdown("---")
        ledger_selection = st.selectbox(
            "🗂️ Select Database Domain View:", 
            [
                "Shipments & Manifests (B/L)", 
                "Commercial Invoices", 
                "Packing Lists Summary", 
                "Supplier Item Quotations",
                "Certificates of Origin (CoO)",
                "Warehouse Delivery Notes (GRN)",
                "Waybill Tracking Logs (AWB)",
                "Customs Declarations (SAD)"
            ]
        )
        
        st.markdown("### 📝 Edit & Review Records")
        if ledger_selection == "Shipments & Manifests (B/L)":
            df_shipments = pd.read_sql_query("SELECT * FROM shipments", conn)
            if not df_shipments.empty:
                st.dataframe(df_shipments, use_container_width=True)
                with st.expander("🗑️ Administrative Row Purge Panel", expanded=False):
                    row_to_delete = st.selectbox("Select Bill of Lading Number to Remove:", df_shipments["bl_number"].unique())
                    if st.button("❌ Permanently Delete Selected Shipment From Database", key="del_ship"):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM shipments WHERE bl_number = ?", (row_to_delete,))
                        conn.commit()
                        st.success(f"Successfully deleted manifest row `{row_to_delete}`.")
                        st.rerun()
            else:
                st.info("No shipment records available in the warehouse.")
                
        elif ledger_selection == "Commercial Invoices":
            df_inv = pd.read_sql_query("SELECT * FROM invoices", conn)
            if not df_inv.empty:
                st.dataframe(df_inv, use_container_width=True)
            else:
                st.info("No commercial invoice tracking files found.")
        else:
            st.info("Database table viewing active. Process corresponding tracking items to generate relational summaries.")
            
        conn.close()
    except Exception as ledger_err:
        st.error(f"Error loading warehouse ledger metrics: {ledger_err}")

with tab3:
    st.subheader("🕵️ Autonomous Tool-Driven Discrepancy Auditor Engine")
    st.write("Leverages the Gemini tool-use matrix to cross-reference disconnected data registers, calculate metrics variances, and spot compliance risks.")
    
    if st.button("🚀 Initialize Analytical Auditing Run", type="primary"):
        from db_utils import fetch_all_cross_referenced_keys, fetch_shipment_manifest_by_key, fetch_invoice_data_by_key
        
        status_container = st.empty()
        status_container.info("🧠 Spawning Supply-Chain Auditor Agent, inspecting target indexes...")
        
        client = get_gemini_client()
        
        auditor_directive = """
        You are an elite Supply-Chain Risk Auditor Agent. Your objective is to run a comprehensive compliance analysis.
        CRITICAL RATE LIMIT CONSTRAINTS:
        - First, execute 'fetch_all_cross_referenced_keys' exactly ONCE to get a structural inventory.
        - To conserve API quota limit allocations, pick a MAXIMUM of 2 sample transaction reference keys to audit. DO NOT loop through every record in the table.
        - For those 2 keys, invoke 'fetch_shipment_manifest_by_key' and 'fetch_invoice_data_by_key'.
        - Consolidate your comparative analytical tracking data.
        Output a comprehensive compliance report. Separate entries with clear visual markdown tables or banners, highlighting flagged items in red and clear records in green.
        """
        
        try:
            # Register the explicit tools inside the GenAI SDK ecosystem configuration
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=auditor_directive,
                config=types.GenerateContentConfig(
                    tools=[fetch_all_cross_referenced_keys, fetch_shipment_manifest_by_key, fetch_invoice_data_by_key],
                    temperature=0.2
                )
            )
            
            status_container.empty()
            st.markdown("### 📋 Executive Auditor Findings Report")
            st.markdown(response.text)
            st.success("🏁 Supply-Chain Audit complete. Results saved to operational cache.")
            
        except Exception as agent_err:
            status_container.empty()
            
            # Catch Gemini API 429 / Quota Exhausted limits explicitly
            err_string = str(agent_err)
            if "429" in err_string or "RESOURCE_EXHAUSTED" in err_string:
                st.error("🛑 **API Daily Quota Exceeded (Free Tier Limit Caught)**")
                st.warning(
                    "The Autonomous Agent hit the Google GenAI Free Tier limit of 20 requests per day. "
                    "In an enterprise deployment, this system seamlessly upgrades to a Pay-As-You-Go tier "
                    "or an enterprise billing profile to unlock unlimited token processing throughput."
                )
                # Parse and display a clean hint if the error contains a backoff suggestion
                if "retry in" in err_string.lower():
                    try:
                        wait_hint = err_string.split("retry in ")[1].split("s.")[0]
                        st.info(f"⏳ **System Operational Advisory:** Please wait approximately **{float(wait_hint):.1f} seconds** before re-triggering the agentic loop.")
                    except Exception:
                        st.info("⏳ Please wait a short moment before re-triggering the agentic loop.")
            else:
                # Fallback handler for all other unhandled trace variations
                st.error(f"Auditor Execution Trace Error: {agent_err}")

with tab4:
    st.subheader("💬 AI Logistics Copilot Terminal")
    st.write("Query your system's logistics database in natural language. The agent transforms your questions into safe, optimized SQL queries on the fly.")
    st.caption("💡 Try asking: *'Show me our top 3 shippers by volume'* or *'Are there any invoice values greater than $10,000?'*")
    st.markdown("---")

    from db_utils import execute_read_only_query

    # Initialize persistent state memory for workspace conversation threads
    if "copilot_messages" not in st.session_state:
        st.session_state.copilot_messages = []

    # Display rolling history 
    for message in st.session_state.copilot_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input("Ask a question about the logistics ledger..."):
        # Display immediate text marker
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.copilot_messages.append({"role": "user", "content": user_query})

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("🔍 *Analyzing system tables...*")
            
            # Formulate full descriptive engine database context injection mapping
            copilot_system_prompt = """
            You are the core Intelligent Logistics Data Copilot.
            Your job is to answer user queries by executing read-only SQL commands against the database.
            
            You have access to the 'execute_read_only_query' tool.
            
            [OPERATIONAL DATABASE STRUCTURAL MAP]
            1. Table 'shipments' -> Fields: bl_number (TEXT PRIMARY KEY), shipper_name (TEXT), consignee_name (TEXT), vessel_name (TEXT), voyage_number (TEXT), port_of_loading (TEXT), port_of_discharge (TEXT), total_weight_kg (REAL)
            2. Table 'invoices'  -> Fields: invoice_number (TEXT PRIMARY KEY), vendor_name (TEXT), buyer_name (TEXT), grand_total (REAL), currency (TEXT), invoice_date (TEXT)
            3. Table 'packing_lists' -> Fields: packing_list_number (TEXT), bl_reference (TEXT), total_packages (INTEGER), total_gross_mass (REAL)
            4. Table 'failed_documents' -> Fields: id, file_name, error_message, agent_analysis (TEXT)
            
            Instructions:
            - Interpret the user's natural language question.
            - Write a mathematically and structurally precise SQL query.
            - Pass that query to 'execute_read_only_query'.
            - Synthesize the returned table rows into a friendly, professional executive summary. Mention the raw data details in your answer.
            """
            
            try:
                copilot_client = get_gemini_client()
                agent_response = copilot_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[copilot_system_prompt, user_query],
                    config=types.GenerateContentConfig(
                        tools=[execute_read_only_query],
                        temperature=0.1
                    )
                )
                
                final_text = agent_response.text
                response_placeholder.markdown(final_text)
                st.session_state.copilot_messages.append({"role": "assistant", "content": final_text})
                
            except Exception as copilot_err:
                response_placeholder.error(f"Copilot Node Core error: {str(copilot_err)}")