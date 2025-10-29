import fitz  # PyMuPDF
import sys

PDF_PATH = "Reference Technical Design Document - Generative Newsletter V2.pdf"
TXT_PATH = "Reference Technical Design Document - Generative Newsletter V2.txt"

def pdf_to_txt(pdf_path, txt_path):
    doc = fitz.open(pdf_path)
    with open(txt_path, "w", encoding="utf-8") as out:
        for page in doc:
            text = page.get_text()
            out.write(text)
            out.write("\n\n")
    print(f"Text extracted to {txt_path}")

if __name__ == "__main__":
    pdf_to_txt(PDF_PATH, TXT_PATH)
