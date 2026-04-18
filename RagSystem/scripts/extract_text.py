import os
from pypdf import PdfReader
import json

def extract_pdf_text(pdf_path, output_json):
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    print(f"Extracting text from {pdf_path}...")
    reader = PdfReader(pdf_path)
    pages_text = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages_text.append({
                "page": i + 1,
                "content": text
            })
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(pages_text, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully extracted {len(pages_text)} pages to {output_json}")

if __name__ == "__main__":
    pdf_path = r"c:\Users\firas halouani\Desktop\newProject\RagSystem\OWASP-Top-10-for-LLMs-v2025.pdf"
    output_json = r"c:\Users\firas halouani\Desktop\newProject\RagSystem\owasp_text.json"
    extract_pdf_text(pdf_path, output_json)
