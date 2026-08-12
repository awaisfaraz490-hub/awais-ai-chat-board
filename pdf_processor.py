import os

import fitz

from ai import describe_image


# File types the /upload route accepts.
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"
}

TEXT_EXTENSIONS = {
    ".txt", ".md"
}


def extract_text_from_pdf(filepath):
    document = fitz.open(filepath)

    full_text = ""

    for page_number, page in enumerate(document):

        text = page.get_text()

        if text.strip():

            full_text += (
                f"\n\n--- Page {page_number + 1} ---\n"
            )

            full_text += text

    document.close()

    return full_text


def extract_text_from_plain_text(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as text_file:
        return text_file.read()


def extract_text_from_file(filepath):
    """
    Single entry point used by app.py. Figures out the file type from
    its extension and routes it to the right extractor:
      - .pdf            -> PyMuPDF text extraction
      - .txt / .md      -> read as plain text
      - image formats   -> vision AI transcription (ai.describe_image)
    Whatever comes back is stored as "extracted_text" and treated the
    same way everywhere else in the app (chat context, sources, etc.)
    """

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(filepath)

    if ext in TEXT_EXTENSIONS:
        return extract_text_from_plain_text(filepath)

    if ext in IMAGE_EXTENSIONS:
        return describe_image(filepath)

    raise ValueError(f"Unsupported file type: {ext}")
