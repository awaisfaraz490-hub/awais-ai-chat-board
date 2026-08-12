import os
import base64
import mimetypes

from openai import OpenAI


# NOTE (Aug 2026): Groq deprecated "llama-3.3-70b-versatile" and
# "llama-3.1-8b-instant". Using a decommissioned model name causes
# every /ask request to fail. These are the current recommended
# replacements from https://console.groq.com/docs/deprecations
MODEL_NAME = "openai/gpt-oss-120b"

# Vision-capable model, used to "read" uploaded images/screenshots
# (handwriting, UI screenshots, photos of documents, etc.) so they
# can be treated just like a PDF's extracted text.
VISION_MODEL_NAME = "qwen/qwen3.6-27b"

_client = None


def get_client():
    """
    Lazily create the Groq client (using OpenAI's SDK, since Groq's
    API is OpenAI-compatible) so a missing API key only breaks the
    /ask route (with a clear error) instead of crashing the entire
    app at import time (which would break every route, including
    the homepage).
    """
    global _client

    if _client is None:

        api_key = os.environ.get("GROQ_API_KEY")

        if not api_key:
            raise Exception(
                "GROQ_API_KEY is not set. Add it in your "
                "environment variables (locally in a .env file, "
                "or in Vercel Project Settings -> Environment Variables). "
                "Get a free key at https://console.groq.com/keys"
            )

        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

    return _client


# ==============================
# READ AN IMAGE / SCREENSHOT
# ==============================

def describe_image(filepath):
    """
    Sends an image (screenshot, photo, scanned page, etc.) to a
    vision-capable model and returns a detailed text transcription +
    description. This text is then stored exactly like PDF text, so
    the rest of the app (search, Q&A, sources) doesn't need to know
    the difference between a PDF and an image.
    """

    mime_type, _ = mimetypes.guess_type(filepath)

    if not mime_type:
        mime_type = "image/png"

    with open(filepath, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    data_url = f"data:{mime_type};base64,{encoded}"

    prompt = (
        "Carefully read this image (it may be a screenshot, a photo "
        "of a document, a scanned page, a diagram, or a UI). "
        "1) Transcribe ALL visible text exactly as written (any "
        "language). 2) Then briefly describe any charts, tables, "
        "layout, or visual elements that are not plain text. "
        "Be thorough and accurate -- this transcription will be used "
        "to answer questions later, so do not skip any text."
    )

    response = get_client().chat.completions.create(
        model=VISION_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ]
    )

    return response.choices[0].message.content


# ==============================
# ASK AI
# ==============================

def ask_ai(
    question,
    pdfs=None,
    chat_history=None
):

    # Make sure values are available
    if pdfs is None:

        pdfs = []

    if chat_history is None:

        chat_history = []


    # ==============================
    # CONVERSATION CONTEXT
    # ==============================

    conversation = ""

    if chat_history:

        for chat in chat_history[-10:]:

            conversation += f"""
Previous User Question:
{chat['question']}

Previous AI Answer:
{chat['answer']}

---
"""


    # ==============================
    # GENERAL AI MODE
    # ==============================

    if not pdfs:

        prompt = f"""
You are a helpful AI assistant.

You are having a conversation with the user.

Use the previous conversation to understand
follow-up questions.

IMPORTANT LANGUAGE RULE:
Always answer in the SAME language the user's
current question is written in. If the question
is in Urdu, answer fully in Urdu. If it is in
English, answer in English. If it is in Roman
Urdu (Urdu written in English letters), answer
in Roman Urdu. Match whatever language or script
the user used, even if it mixes languages.

Previous conversation:
{conversation}

Current question:
{question}

Answer the current question clearly and simply,
in the same language as the question above.

If the question refers to something from the
previous conversation, use that context.

Answer:
"""


    # ==============================
    # PDF MODE
    # ==============================

    else:

        context = ""

        for pdf in pdfs:

            context += f"""
PDF NAME:
{pdf['filename']}

PDF CONTENT:
{pdf['extracted_text']}

---
"""


        prompt = f"""
You are a PDF AI assistant.

You are having a conversation with the user.

Use the uploaded PDF information and previous
conversation to answer the current question.

IMPORTANT RULES:

1. Use the PDF information when answering PDF questions.

2. Use previous conversation to understand
   follow-up questions.

3. If the answer cannot be found in the PDFs,
   say (translated into the question's language
   if needed):

"I could not find this information in the uploaded PDFs."

4. Do not invent information.

5. After answering, identify the PDF files that
   contain information used for the answer.

6. LANGUAGE RULE: Always answer in the SAME
   language the user's current question is
   written in. If the question is in Urdu, answer
   fully in Urdu. If it is in English, answer in
   English. If it is in Roman Urdu (Urdu written
   in English letters), answer in Roman Urdu.
   The PDF content may be in a different language
   than the question - still answer in the
   question's language, translating the relevant
   information as needed.

Use this exact format:

SOURCE_PDFS:
filename1
filename2

Previous conversation:
{conversation}

PDF INFORMATION:
{context}

Current question:
{question}

ANSWER (in the same language as the question above):
"""


    # ==============================
    # CALL OPENAI
    # ==============================

    try:

        response = get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        answer = response.choices[0].message.content

        return answer

    except Exception as error:

        raise Exception(
            f"OpenAI error: {error}"
        )