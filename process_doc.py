import time
import os
import sys
import json
import logging

from google import genai
from google.genai import types
from google.genai.errors import APIError
from db_utils import log_failed_document
from schema import BillOfLadingSchema
from pdf_utils import extract_text_from_pdf, convert_pdf_to_image_bytes

class PipelineSuspensionException(Exception):
    """Custom exception raised when resource exhaustion limit fields are reached to gracefully halt steps."""
    pass

logging.basicConfig(filename="app_runtime.log", level=logging.ERROR, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

def trigger_autonomous_exception_resolver(file_name: str, exception_string: str, document_type: str) -> str:
    """
    Invoked when standard structural self-correction fails. Spawns an agent 
    to determine exactly why a document failed schema enforcement.
    """
    from db_utils import get_latest_runtime_logs
    from google import genai
    
    # Capture state log snippet
    recent_logs = get_latest_runtime_logs(limit=25)
    
    client = genai.Client()
    resolver_prompt = f"""
    You are an Autonomous System Exception Reliability Engineer.
    A logistics ingestion parsing framework just failed structural schema verification.
    
    [CRITICAL PIPELINE INCIDENT REPORT]
    Target File: {file_name}
    Inferred Classification Matrix: {document_type}
    Validation Exception Stack: {exception_string}
    
    [TAIL END RUNTIME TELEMETRY LOGS]
    {recent_logs}
    
    Task: Diagnose the structural breakdown. Provide a crisp structural explanation covering:
    1. The core structural mismatch reason (e.g., unexpected data type format, missing key, multi-page data overflow).
    2. A precise strategy or schema alteration recommendation to bypass this exception type safely.
    Keep your response concise, professional, and actionable.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[resolver_prompt],
        )
        return response.text
    except Exception as e:
        return f"Autonomous Engine Analysis failed due to runtime SDK error: {str(e)}"

# Place this inside run_pipeline() or your batch upload routing exceptions block:
# Example tracking intercept layout:
"""
except Exception as e:
    logging.error(f"Failed processing pipeline step for file {pdf_file_path}: {str(e)}")
    analysis_payload = trigger_autonomous_exception_resolver(
        file_name=os.path.basename(pdf_file_path),
        exception_string=str(e),
        document_type=target_schema.__name__
    )
    from db_utils import update_failed_document_with_analysis
    update_failed_document_with_analysis(os.path.basename(pdf_file_path), str(e), analysis_payload)
"""

def process_with_self_correction(client, contents, target_schema, max_attempts=2):
    """
    Executes a recursive correction loop: If the AI output fails schema validation, 
    the error is fed back to the model for self-correction.
    Bubbles up pipeline suspension exceptions instead of enforcing catastrophic application termination.
    """
    attempt = 0
    while attempt <= max_attempts:
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=target_schema,
                    temperature=0.1
                ),
            )
        except APIError as api_err:
            err_msg = str(api_err)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                print("🛑 CRITICAL: Quota exhausted. Propagating exception to prevent systemic thread lock.")
                log_failed_document("SYSTEM", "Quota exhausted - stopping pipeline processing operations.")
                raise PipelineSuspensionException("Quota limit reached. External ingestion pipeline halted safely.")
            raise api_err
        
        try:
            # 1. Attempt standard JSON parsing
            raw_data = json.loads(response.text)
            
            # 2. Attempt strict Pydantic validation
            validated_data = target_schema.model_validate(raw_data)
            return validated_data.model_dump()
            
        except (json.JSONDecodeError, AttributeError, Exception) as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("🛑 CRITICAL: Quota exhausted during parsing phase. Propagating exception framework upwards.")
                log_failed_document("SYSTEM", "Quota exhausted - stopping pipeline parsing execution chains.")
                raise PipelineSuspensionException("Quota limit reached. System worker processing stream paused cleanly.")
            
            attempt += 1
            print(f"⚠️ Validation failed (Attempt {attempt}/{max_attempts + 1}): {e}")
            if attempt > max_attempts:
                raise RuntimeError(f"❌ Max correction attempts reached. AI failed to adhere to schema. Final error: {e}")
            
            # Feed the error back into the next prompt iteration so the AI can self-fix
            contents.append(f"CRITICAL ERROR: Your previous output failed validation: {e}. "
                            "Please correct the JSON format and structural types to strictly match the schema.")
            
    return None

def run_pipeline(pdf_file_path: str):
    if not os.path.exists(pdf_file_path):
        print(f"Error: The file path '{pdf_file_path}' does not exist.")
        return

    print(f"Reading text layer from file: {pdf_file_path}...")
    raw_document_text = extract_text_from_pdf(pdf_file_path)
    
    client = genai.Client()
    prompt = "Extract the logistics information from this document matching the requested structural schema formatting."
    contents = [prompt]

    if raw_document_text:
        print("Successfully read text layer. Dispatching native text payload to Gemini...")
        contents.append(raw_document_text)
    else:
        print("Warning: Extracted text is empty. Activating Vision Core via pdf2image page conversion...")
        image_pages = convert_pdf_to_image_bytes(pdf_file_path)
        
        if not image_pages:
            print("Critical Error: Failed to render document pages into standard image frames. Exiting.")
            return
            
        print(f"Streaming {len(image_pages)} page frames directly into Gemini Multimodal processor...")
        for page_bytes in image_pages:
            contents.append(types.Part.from_bytes(data=page_bytes, mime_type="image/jpeg"))

    print("Awaiting structural schema mapping validation from model...")
    
    doc_type_lower = pdf_file_path.lower()
    if "invoice" in doc_type_lower:
        from schema import CommercialInvoiceSchema
        target_schema = CommercialInvoiceSchema
    elif "packing" in doc_type_lower:
        from schema import PackingListSchema
        target_schema = PackingListSchema
    elif "quote" in doc_type_lower or "quotation" in doc_type_lower:
        from schema import SupplierQuotationSchema
        target_schema = SupplierQuotationSchema
    elif "origin" in doc_type_lower or "coo" in doc_type_lower:
        from schema import CertificateOfOriginSchema
        target_schema = CertificateOfOriginSchema
    elif "delivery" in doc_type_lower or "grn" in doc_type_lower:
        from schema import DeliveryNoteSchema
        target_schema = DeliveryNoteSchema
    elif "waybill" in doc_type_lower or "awb" in doc_type_lower:
        from schema import WaybillSchema
        target_schema = WaybillSchema
    elif "customs" in doc_type_lower or "declaration" in doc_type_lower or "sad" in doc_type_lower:
        from schema import CustomsDeclarationSchema
        target_schema = CustomsDeclarationSchema
    else:
        target_schema = BillOfLadingSchema

    try:
        extracted_json = process_with_self_correction(client, contents, target_schema)
        if extracted_json:
            print("\n================ EXTRACTION SUCCESSFUL ================")
            print(json.dumps(extracted_json, indent=4))
            print("=======================================================\n")
        else:
            print("⚠️ Ingestion completed with an empty result set.")
    except PipelineSuspensionException as suspension_err:
        print(f"❌ Execution Engine paused safely via custom intercept handler: {suspension_err}")
    except Exception as general_err:
        print(f"❌ Ingestion sequence mapping unhandled deviation trace: {general_err}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a path to a PDF file. Example: python process_doc.py sample.pdf")
    else:
        run_pipeline(sys.argv[1])