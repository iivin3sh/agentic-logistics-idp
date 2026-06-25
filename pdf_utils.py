import pdfplumber
from pdf2image import convert_from_path, convert_from_bytes
import io

def extract_text_from_pdf(pdf_path: str) -> str:
    """Opens a PDF file path and extracts all raw text across all pages."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                full_text += f"\n--- PAGE {page_num} ---\n" + page_text
    return full_text.strip()

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Opens in-memory PDF bytes and extracts raw text layer across all pages."""
    full_text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                full_text += f"\n--- PAGE {page_num} ---\n" + page_text
    return full_text.strip()

def convert_pdf_to_image_bytes(pdf_path: str) -> list:
    """Converts a local scanned PDF into a list of standalone JPEG raw byte packets."""
    try:
        images = convert_from_path(pdf_path)
        image_bytes_list = []
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            image_bytes_list.append(img_byte_arr.getvalue())
        return image_bytes_list
    except Exception:
        return []

def convert_pdf_bytes_to_image_bytes(pdf_bytes: bytes) -> list:
    """Converts in-memory PDF byte contents into a list of standalone JPEG raw byte packets."""
    try:
        images = convert_from_bytes(pdf_bytes)
        image_bytes_list = []
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            image_bytes_list.append(img_byte_arr.getvalue())
        return image_bytes_list
    except Exception:
        return []

if __name__ == "__main__":
    print("PDF utility script initialized with Multimodal Vision layer components.")