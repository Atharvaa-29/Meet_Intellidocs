from pathlib import Path

def parse_txt(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")

def parse_pdf(file_path: str) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except ImportError:
        raise ImportError("pypdf not installed. Run: pip install pypdf")

def parse_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        raise ImportError("python-docx not installed. Run: pip install python-docx")

def parse_file(file_path: str) -> str:
    """Auto-detect file type and parse to plain text."""
    ext = Path(file_path).suffix.lower()
    if ext == ".txt":
        return parse_txt(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
