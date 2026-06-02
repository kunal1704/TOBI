from io import BytesIO


def extract_uploaded_file(uploaded_file):
    name = uploaded_file.name
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    data = uploaded_file.getvalue()

    if suffix in {"txt", "md", "csv"}:
        return data.decode("utf-8", errors="ignore")

    if suffix == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install pypdf to extract text from PDF files.") from exc

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    if suffix == "docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("Install python-docx to extract text from DOCX files.") from exc

        document = Document(BytesIO(data))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(paragraphs)

    return data.decode("utf-8", errors="ignore")
