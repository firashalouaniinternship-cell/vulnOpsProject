import os
from pypdf import PdfReader
import json
import traceback

def extract_pdf_text_robust(pdf_path, output_json):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    print(f"--- Extracting text from {pdf_path} ---")
    try:
        reader = PdfReader(pdf_path)
        pages_text = []
        
        total_pages = len(reader.pages)
        print(f"Total pages: {total_pages}")
        
        for i in range(total_pages):
            try:
                print(f"Processing page {i+1}/{total_pages}...")
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    pages_text.append({
                        "page": i + 1,
                        "content": text
                    })
            except Exception as pe:
                print(f"Warning: Failed to extract page {i+1}: {pe}")
        
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(pages_text, f, ensure_ascii=False, indent=2)
        
        print(f"--- Successfully extracted {len(pages_text)} pages to {output_json} ---")
    except Exception as e:
        print(f"Critical error during PDF extraction: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = r"c:\Users\firas halouani\Desktop\newProject\RagSystem\OWASP-Top-10-for-LLMs-v2025.pdf"
    output_json = r"c:\Users\firas halouani\Desktop\newProject\RagSystem\owasp_text.json"
    extract_pdf_text_robust(pdf_path, output_json)
