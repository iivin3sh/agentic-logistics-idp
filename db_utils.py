import pandas as pd
import os
import sqlite3
import difflib
import psycopg2
import time
def fetch_shipment_manifest_by_key(bl_number: str):
    time.sleep(2)
from urllib.parse import urlparse

DB_URL = os.getenv("DATABASE_URL")
DB_NAME = "shipments.db"

def get_connection():
    """Returns a connection object for either PostgreSQL (Cloud) or SQLite (Local)."""
    if DB_URL:
        return psycopg2.connect(DB_URL)
    else:
        return sqlite3.connect(DB_NAME)
    
def get_placeholder():
    """Returns %s for Postgres, ? for SQLite."""
    return "%s" if DB_URL else "?"

def init_db():
    """Initializes the database, supporting both SQLite and PostgreSQL syntax."""
    conn = get_connection()
    cursor = conn.cursor()
    
    is_postgres = DB_URL is not None
    # PostgreSQL uses SERIAL for auto-increment, SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT.
    id_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    try:
        # 1. Quotation Line Items Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS quotation_items (
            id {id_type},
            quote_number TEXT,
            item_number TEXT,
            product_code TEXT,
            description TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL
        )
        """)
        
        # 2. Quotation Parent Summary Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotations (
            quote_number TEXT PRIMARY KEY,
            project_name TEXT,
            date TEXT,
            currency TEXT,
            grand_total REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 3. Parent Shipment/Bill of Lading Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shipments (
                bl_number TEXT PRIMARY KEY,
                text_extraction_raw TEXT,
                shipper_name TEXT,
                consignee_name TEXT,
                vessel_name TEXT,
                voyage_number TEXT,
                port_of_loading TEXT,
                port_of_discharge TEXT,
                total_weight_kg REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 4. Nested Container Line Items Breakdown Table
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS containers (
                id {id_type},
                bl_number TEXT,
                container_number TEXT,
                seal_number TEXT,
                FOREIGN KEY (bl_number) REFERENCES shipments (bl_number)
            )
        ''')
        
        # 5. Parent Invoices Summary Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_number TEXT PRIMARY KEY,
                vendor_name TEXT,
                buyer_name TEXT,
                grand_total REAL,
                currency TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 6. Parent Packing Lists Summary Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS packing_lists (
                packing_list_number TEXT PRIMARY KEY,
                bl_reference TEXT,
                total_packages INTEGER,
                total_gross_mass REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 7. Nested Packing List Items Breakdown Table
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS packing_list_items (
                id {id_type},
                packing_list_number TEXT,
                item_description TEXT,
                package_type TEXT,
                package_count INTEGER,
                net_weight_kg REAL,
                gross_weight_kg REAL,
                FOREIGN KEY (packing_list_number) REFERENCES packing_lists (packing_list_number)
            )
        ''')

        # 8. Dead-Letter Audit Table
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS failed_documents (
                id {id_type},
                file_name TEXT,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN invoice_date TEXT")
        except (sqlite3.OperationalError, psycopg2.DatabaseError):
            pass  # column already exists

        # 9. Certificate of Origin Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS certificates_of_origin (
            id {id_type},
            coo_certificate_number TEXT,
            country_of_origin TEXT,
            exporter_details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 10. Delivery Note Master Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id {id_type},
            delivery_note_number TEXT,  
            received_date TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 11. Delivery Note Line Items Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS delivery_note_items (
            id {id_type},
            delivery_note_number TEXT,
            item_number TEXT,
            product_code TEXT,
            actual_received_quantity INTEGER,
            damaged_shortage_notes TEXT
        )
        """)

        # 12. Waybill Tracker Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS waybills (
            id {id_type},
            awb_number TEXT,  
            flight_or_vessel_number TEXT,
            flight_or_vessel_date TEXT,
            chargeable_weight REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 13. Customs Declarations Master Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS customs_declarations (
            id {id_type},
            declaration_number TEXT,  
            duty_fees_paid REAL,
            tax_fees_paid REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 14. Customs Declarations Item Lines Table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS customs_declaration_items (
            id {id_type},
            declaration_number TEXT,
            item_number TEXT,
            hs_code TEXT
        )
        """)
        
        conn.commit()
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError) as db_err:
        conn.rollback()
        print(f"Database initialization failure: {db_err}")
        raise db_err
    finally:
        conn.close()

def is_fuzzy_match(string_a, string_b, passing_score=0.70):
    if not string_a or not string_b: return False, 0.0
    clean_a, clean_b = str(string_a).strip().lower(), str(string_b).strip().lower()
    ratio = difflib.SequenceMatcher(None, clean_a, clean_b).ratio()
    return ratio >= passing_score, ratio

def run_discrepancy_audit():
    """Cross-references records to spot structural errors, weight variances, and company naming typos."""
    conn = get_connection()
    cursor = conn.cursor()
    audit_results = []
    
    try:
        query = """
        SELECT s.bl_number, s.shipper_name, i.vendor_name, s.consignee_name, i.buyer_name, s.total_weight_kg, i.grand_total, i.currency
        FROM shipments s 
        JOIN invoices i ON LOWER(TRIM(s.consignee_name)) = LOWER(TRIM(i.buyer_name))
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for row in rows:
            bl_num, s_name, v_name, c_name, b_name, bl_weight, money, curr = row
            issues = []
            
            is_vendor_matched, vendor_score = is_fuzzy_match(s_name, v_name)
            if not is_vendor_matched:
                issues.append(f"⚠️ Company Mismatch: Shipper '{s_name}' vs Vendor '{v_name}'. Score: {vendor_score*100:.1f}%")
                
            is_buyer_matched, buyer_score = is_fuzzy_match(c_name, b_name)
            if not is_buyer_matched:
                issues.append(f"⚠️ Company Mismatch: Consignee '{c_name}' vs Buyer '{b_name}'. Score: {buyer_score*100:.1f}%")
                
            cursor.execute(f"SELECT packing_list_number, total_gross_mass FROM packing_lists WHERE bl_reference = {get_placeholder()}", (bl_num,))
            pk_row = cursor.fetchone()
            
            if pk_row:
                pk_num, pl_weight = pk_row
                if abs(bl_weight - pl_weight) >= 0.01:
                    issues.append(f"⚠️ Weight Variance: B/L {bl_weight}kg vs P/L {pl_weight}kg.")
            else:
                issues.append(f"⚠️ Missing Verification Shield: No Packing List for B/L '{bl_num}'.")
                
            audit_results.append({"bl_number": bl_num, "status": "❌ Discrepancy Found" if issues else "✅ Cleared", "details": issues})
            
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, AttributeError) as err:
        print(f"Error during discrepancy audit: {err}")
        # Audit routines shouldn't break the read pipeline, but should log safely
    finally:
        conn.close()
        
    return audit_results

def save_quotation_to_db(summary, items_list):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(f"""
                INSERT INTO quotations (quote_number, project_name, date, currency, grand_total, timestamp) 
                VALUES ({p}, {p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)
                ON CONFLICT (quote_number) DO UPDATE SET 
                    project_name = EXCLUDED.project_name, date = EXCLUDED.date, 
                    currency = EXCLUDED.currency, grand_total = EXCLUDED.grand_total, timestamp = CURRENT_TIMESTAMP
            """, (summary["quote_number"], summary.get("project_name"), summary.get("date"), summary.get("currency"), summary.get("grand_total")))
        else:
            cursor.execute(f'INSERT OR REPLACE INTO quotations VALUES ({p}, {p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)', 
                        (summary["quote_number"], summary.get("project_name"), summary.get("date"), summary.get("currency"), summary.get("grand_total")))
        
        cursor.execute(f'DELETE FROM quotation_items WHERE quote_number = {p}', (summary["quote_number"],))
        for item in items_list:
            cursor.execute(f'INSERT INTO quotation_items (quote_number, item_number, product_code, description, quantity, unit_price, total_price) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})',
                        (summary["quote_number"], item.get("item_number"), item.get("product_code"), item.get("description"), item.get("quantity"), item.get("unit_price"), item.get("total_price")))
        conn.commit()
        return True, "Synced successfully!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save quotation to DB, transaction rolled back. Error: {e}")
        return False, f"Sync failed: {e}"
    finally:
        conn.close()

def save_invoice_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(f'''INSERT INTO invoices (invoice_number, vendor_name, buyer_name, grand_total, currency, invoice_date, timestamp)
                            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)
                            ON CONFLICT (invoice_number) DO UPDATE SET
                                vendor_name = EXCLUDED.vendor_name, buyer_name = EXCLUDED.buyer_name,
                                grand_total = EXCLUDED.grand_total, currency = EXCLUDED.currency,
                                invoice_date = EXCLUDED.invoice_date, timestamp = CURRENT_TIMESTAMP''',
                        (data["invoice_number"], data["vendor_name"], data["buyer_name"], data["grand_total"], data["currency"], data["invoice_date"]))
        else:
            cursor.execute(f'''INSERT OR REPLACE INTO invoices 
                            (invoice_number, vendor_name, buyer_name, grand_total, currency, invoice_date) 
                            VALUES ({p}, {p}, {p}, {p}, {p}, {p})''', 
                        (data["invoice_number"], data["vendor_name"], data["buyer_name"], data["grand_total"], data["currency"], data["invoice_date"]))
        conn.commit()
        return True, "Invoice saved!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save invoice to DB, transaction rolled back. Error: {e}")
        return False, f"Sync failed: {e}"
    finally:
        conn.close()

def save_shipment_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(f'''INSERT INTO shipments (bl_number, text_extraction_raw, shipper_name, consignee_name, vessel_name, voyage_number, port_of_loading, port_of_discharge, total_weight_kg, timestamp)
                            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)
                            ON CONFLICT (bl_number) DO UPDATE SET
                                shipper_name = EXCLUDED.shipper_name, consignee_name = EXCLUDED.consignee_name,
                                vessel_name = EXCLUDED.vessel_name, voyage_number = EXCLUDED.voyage_number,
                                port_of_loading = EXCLUDED.port_of_loading, port_of_discharge = EXCLUDED.port_of_discharge,
                                total_weight_kg = EXCLUDED.total_weight_kg, timestamp = CURRENT_TIMESTAMP''',
                        (data["bl_number"], "", data["shipper_name"], data["consignee_name"], data["vessel_name"], data["voyage_number"], data["port_of_loading"], data["port_of_discharge"], data["total_weight_kg"]))
        else:
            cursor.execute(f'INSERT OR REPLACE INTO shipments VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)',
                        (data["bl_number"], "", data["shipper_name"], data["consignee_name"], data["vessel_name"], data["voyage_number"], data["port_of_loading"], data["port_of_discharge"], data["total_weight_kg"]))
        
        cursor.execute(f'DELETE FROM containers WHERE bl_number = {p}', (data["bl_number"],))
        for cont in data.get("containers", []):
            cursor.execute(f'INSERT INTO containers (bl_number, container_number, seal_number) VALUES ({p}, {p}, {p})',
                        (data["bl_number"], cont["container_number"], cont["seal_number"]))
        conn.commit()
        return True, "Shipment saved!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save shipment to DB, transaction rolled back. Error: {e}")
        return False, f"Sync failed: {e}"
    finally:
        conn.close()

def save_packing_list_to_db(summary, items_list):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(f'''INSERT INTO packing_lists (packing_list_number, bl_reference, total_packages, total_gross_mass, timestamp)
                            VALUES ({p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)
                            ON CONFLICT (packing_list_number) DO UPDATE SET
                                bl_reference = EXCLUDED.bl_reference, total_packages = EXCLUDED.total_packages,
                                total_gross_mass = EXCLUDED.total_gross_mass, timestamp = CURRENT_TIMESTAMP''',
                        (summary["packing_list_number"], summary["bl_reference"], summary["total_packages"], summary["total_gross_mass"]))
        else:
            cursor.execute(f'INSERT OR REPLACE INTO packing_lists VALUES ({p}, {p}, {p}, {p}, CURRENT_TIMESTAMP)',
                        (summary["packing_list_number"], summary["bl_reference"], summary["total_packages"], summary["total_gross_mass"]))
            
        cursor.execute(f'DELETE FROM packing_list_items WHERE packing_list_number = {p}', (summary["packing_list_number"],))
        for item in items_list:
            cursor.execute(f'INSERT INTO packing_list_items (packing_list_number, item_description, package_type, package_count, net_weight_kg, gross_weight_kg) VALUES ({p}, {p}, {p}, {p}, {p}, {p})',
                        (summary["packing_list_number"], item.get("item_description"), item.get("package_type"), item.get("package_count"), item.get("net_weight_kg"), item.get("gross_weight_kg")))
        conn.commit()
        return True, "Packing list synced!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save packing list to DB, transaction rolled back. Error: {e}")
        return False, f"Sync failed: {e}"
    finally:
        conn.close()

def log_failed_document(file_name, error_message):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        cursor.execute(f"INSERT INTO failed_documents (file_name, error_message) VALUES ({p}, {p})", (file_name, str(error_message)))
        conn.commit()
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError) as e:
        conn.rollback()
        print(f"Critical failure logging document tracking drops: {e}")
    finally:
        conn.close()

def get_all_tables_as_dataframes():
    """Fetches all operational tables to compile the master ledger tabs."""
    conn = get_connection()
    try:
        df_bl = pd.read_sql_query("SELECT * FROM shipments ORDER BY timestamp DESC", conn)
        df_inv = pd.read_sql_query("SELECT * FROM invoices ORDER BY timestamp DESC", conn)
        df_pl = pd.read_sql_query("SELECT * FROM packing_lists ORDER BY timestamp DESC", conn)
        df_quotes = pd.read_sql_query("SELECT * FROM quotation_items ORDER BY id DESC", conn)
        df_pl_items = pd.read_sql_query("SELECT * FROM packing_list_items", conn)
        
        df_coo = pd.read_sql_query("SELECT * FROM certificates_of_origin ORDER BY timestamp DESC", conn)
        df_dn = pd.read_sql_query("SELECT * FROM delivery_notes ORDER BY timestamp DESC", conn)
        df_dn_items = pd.read_sql_query("SELECT * FROM delivery_note_items", conn)
        df_wb = pd.read_sql_query("SELECT * FROM waybills ORDER BY timestamp DESC", conn)
        df_cd = pd.read_sql_query("SELECT * FROM customs_declarations ORDER BY timestamp DESC", conn)
        df_cd_items = pd.read_sql_query("SELECT * FROM customs_declaration_items", conn)
        
        return {
            "Bill of Lading Master": df_bl,
            "Commercial Invoices": df_inv,
            "Packing Lists Summary": df_pl,
            "Packing List Items": df_pl_items,
            "Quotation Line Items": df_quotes,
            "Certificates of Origin": df_coo,
            "Warehouse Delivery Notes": df_dn,
            "Delivery Note Line Items": df_dn_items,
            "Waybill Tracking Logs": df_wb,
            "Customs Declarations": df_cd,
            "Customs Declaration Items": df_cd_items
        }
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, ValueError, AttributeError) as e:
        print(f"Error gathering dataframes for unified ledger: {e}")
        return {}
    finally:
        conn.close()

def save_certificate_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        cursor.execute(
            f"INSERT INTO certificates_of_origin (coo_certificate_number, country_of_origin, exporter_details) VALUES ({p}, {p}, {p})",
            (data["coo_certificate_number"], data["country_of_origin"], data["exporter_details"])
        )
        conn.commit()
        return "Certificate of Origin saved successfully!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save certificate, transaction rolled back. Error: {e}")
        return f"Error: {e}"
    finally:
        conn.close()

def save_delivery_note_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(
                f"""INSERT INTO delivery_notes (delivery_note_number, received_date) VALUES ({p}, {p})
                    ON CONFLICT (delivery_note_number) DO UPDATE SET received_date = EXCLUDED.received_date""",
                (data["delivery_note_number"], data["received_date"])
            )
        else:
            cursor.execute(
                f"INSERT OR REPLACE INTO delivery_notes (delivery_note_number, received_date) VALUES ({p}, {p})",
                (data["delivery_note_number"], data["received_date"])
            )
        
        cursor.execute(f"DELETE FROM delivery_note_items WHERE delivery_note_number = {p}", (data["delivery_note_number"],))
        for item in data.get("items", []):
            cursor.execute(
                f"INSERT INTO delivery_note_items (delivery_note_number, item_number, product_code, actual_received_quantity, damaged_shortage_notes) VALUES ({p}, {p}, {p}, {p}, {p})",
                (data["delivery_note_number"], item["item_number"], item["product_code"], item["actual_received_quantity"], item["damaged_shortage_notes"])
            )
        conn.commit()
        return "Delivery Note tracking data updated!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save delivery note, transaction rolled back. Error: {e}")
        return f"Error: {e}"
    finally:
        conn.close()

def save_waybill_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(
                f"""INSERT INTO waybills (awb_number, flight_or_vessel_number, flight_or_vessel_date, chargeable_weight) VALUES ({p}, {p}, {p}, {p})
                    ON CONFLICT (awb_number) DO UPDATE SET flight_or_vessel_number = EXCLUDED.flight_or_vessel_number, 
                    flight_or_vessel_date = EXCLUDED.flight_or_vessel_date, chargeable_weight = EXCLUDED.chargeable_weight""",
                (data["awb_number"], data["flight_or_vessel_number"], data["flight_or_vessel_date"], data["chargeable_weight"])
            )
        else:
            cursor.execute(
                f"INSERT OR REPLACE INTO waybills (awb_number, flight_or_vessel_number, flight_or_vessel_date, chargeable_weight) VALUES ({p}, {p}, {p}, {p})",
                (data["awb_number"], data["flight_or_vessel_number"], data["flight_or_vessel_date"], data["chargeable_weight"])
            )
        conn.commit()
        return "Transport Waybill metrics locked!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save waybill, transaction rolled back. Error: {e}")
        return f"Error: {e}"
    finally:
        conn.close()

def save_customs_declaration_to_db(data):
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        if DB_URL:
            cursor.execute(
                f"""INSERT INTO customs_declarations (declaration_number, duty_fees_paid, tax_fees_paid) VALUES ({p}, {p}, {p})
                    ON CONFLICT (declaration_number) DO UPDATE SET duty_fees_paid = EXCLUDED.duty_fees_paid, tax_fees_paid = EXCLUDED.tax_fees_paid""",
                (data["declaration_number"], data["duty_fees_paid"], data["tax_fees_paid"])
            )
        else:
            cursor.execute(
                f"INSERT OR REPLACE INTO customs_declarations (declaration_number, duty_fees_paid, tax_fees_paid) VALUES ({p}, {p}, {p})",
                (data["declaration_number"], data["duty_fees_paid"], data["tax_fees_paid"])
            )
        
        cursor.execute(f"DELETE FROM customs_declaration_items WHERE declaration_number = {p}", (data["declaration_number"],))
        for item in data.get("items", []):
            cursor.execute(
                f"INSERT INTO customs_declaration_items (declaration_number, item_number, hs_code) VALUES ({p}, {p})",
                (data["declaration_number"], item["item_number"], item["hs_code"])
            )
        conn.commit()
        return "Government Customs Declaration records written!"
    except (sqlite3.OperationalError, sqlite3.IntegrityError, psycopg2.DatabaseError, KeyError, TypeError) as e:
        conn.rollback()
        print(f"Failed to save customs declaration, transaction rolled back. Error: {e}")
        return f"Error: {e}"
    finally:
        conn.close()

# =====================================================================
# AGENTIC IDP UPGRADES: DATABASE REFLECTION, TOOLS, AND SCHEMA ADAPTATION
# =====================================================================

def execute_read_only_query(sql_query: str) -> str:
    """
    Executes an LLM-generated SQL query securely against the active storage engine.
    Strictly filters out mutation statements to preserve ledger integrity.
    """
    forbidden_keywords = ["insert", "update", "delete", "drop", "truncate", "alter", "create", "grant"]
    query_lower = sql_query.lower()
    
    if any(keyword in query_lower for keyword in forbidden_keywords):
        return "Security Error: Unauthorized Data Manipulation Instruction Blocked."
        
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql_query, conn)
        if df.empty:
            return "No records matching that query execution frame were found."
        
        # Convert to records dictionary format which is fully JSON-serializable by the GenAI SDK
        return df.to_json(orient="records")
    except Exception as e:
        return f"Database Query Error: {str(e)}"
    finally:
        conn.close()

def get_latest_runtime_logs(limit: int = 50) -> str:
    """
    Reads the tail end of the application runtime log to feed diagnostic loops.
    """
    log_file = "app_runtime.log"
    if not os.path.exists(log_file):
        return "Runtime logging stream active. No exception entries recorded yet."
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            return "".join(lines[-limit:])
    except Exception as e:
        return f"Failed to pull diagnostic telemetry frames: {str(e)}"

# --- ATOMIC DATA TOOLS FOR THE DISCREPANCY AUDITOR AGENT ---

def fetch_all_cross_referenced_keys():
    """Returns all overlapping keys between shipments and invoices for deep compliance checking."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Pull candidate keys where fuzzy alignment is highly likely to be checked by the agent
        cursor.execute("SELECT bl_number FROM shipments")
        shipments = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT invoice_number FROM invoices")
        invoices = [r[0] for r in cursor.fetchall()]
        return {"tracked_bill_of_ladings": shipments, "tracked_invoices": invoices}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def fetch_shipment_manifest_by_key(bl_number: str):
    """Fetches details of a shipment manifest including its sub-containers."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM shipments WHERE bl_number = ?", (bl_number,))
        row = cursor.fetchone()
        if not row:
            return f"Shipment manifest '{bl_number}' not found."
        
        # Pull associated container frameworks
        cursor.execute("SELECT container_number, seal_number FROM containers WHERE bl_number = ?", (bl_number,))
        containers = [{"container_number": r[0], "seal_number": r[1]} for r in cursor.fetchall()]
        
        return {
            "bl_number": row[0],
            "shipper_name": row[2],
            "consignee_name": row[3],
            "vessel_name": row[4],
            "voyage_number": row[5],
            "port_of_loading": row[6],
            "port_of_discharge": row[7],
            "total_weight_kg": row[8],
            "linked_containers": containers
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def fetch_invoice_data_by_key(invoice_number: str):
    """Fetches full tracking values for an individual commercial invoice summary."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
        row = cursor.fetchone()
        if not row:
            return f"Invoice record '{invoice_number}' not found."
        return {
            "invoice_number": row[0],
            "vendor_name": row[1],
            "buyer_name": row[2],
            "grand_total": row[3],
            "currency": row[4],
            "invoice_date": row[6] if len(row) > 6 else "N/A"
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

# --- UPGRADED DIAGNOSTIC STORAGE ROUTINE ---

def update_failed_document_with_analysis(file_name: str, error_message: str, agent_analysis: str):
    """Logs parsing drops along with autonomous debugging diagnostics."""
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    try:
        # Gracefully patch the schema dynamically if the column is absent
        try:
            cursor.execute("ALTER TABLE failed_documents ADD COLUMN agent_analysis TEXT")
            conn.commit()
        except Exception:
            pass # Column already structurally present
            
        cursor.execute(
            f"INSERT INTO failed_documents (file_name, error_message, agent_analysis) VALUES ({p}, {p}, {p})",
            (file_name, error_message, agent_analysis)
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to log autonomous agent telemetry trace: {e}")
    finally:
        conn.close()