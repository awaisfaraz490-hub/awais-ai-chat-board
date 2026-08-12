import os
import shutil

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Response,
    Request
)

from fastapi.responses import (
    FileResponse,
    RedirectResponse
)

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, EmailStr

from pdf_processor import (
    extract_text_from_file,
    ALLOWED_EXTENSIONS
)

from database import (
    initialize_database,
    add_pdf,
    get_all_pdfs,
    get_all_pdf_text,
    get_selected_pdf_text,
    delete_pdf,
    add_chat,
    get_chat_history,
    clear_chat_history,
    create_user,
    get_user_by_email,
    create_session,
    delete_session
)

from auth import (
    hash_password,
    verify_password,
    is_valid_email,
    is_valid_password,
    get_current_user,
    get_optional_user,
    SESSION_COOKIE_NAME
)

from ai import ask_ai


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Awais Faraz AI Chatbot"
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# UPLOAD FOLDER
# ============================================================

if os.environ.get("VERCEL"):

    UPLOAD_FOLDER = "/tmp/uploads"

else:

    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "uploads"
    )


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=os.path.join(
            BASE_DIR,
            "static"
        )
    ),
    name="static"
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:

    initialize_database()

except Exception as db_init_error:

    print(
        f"[startup warning] Database not ready: {db_init_error}"
    )


# ============================================================
# REQUEST MODELS
# ============================================================

class QuestionRequest(BaseModel):

    question: str

    use_pdfs: bool = True

    pdf_uuids: list[str] = []


class SignupRequest(BaseModel):

    name: str

    email: EmailStr

    password: str


class LoginRequest(BaseModel):

    email: EmailStr

    password: str


# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def home(request: Request):

    # Check whether the user is logged in
    user = get_optional_user(request)

    # If NOT logged in,
    # ALWAYS show the login page.
    if not user:

        return RedirectResponse(
            url="/login",
            status_code=302
        )

    # If logged in,
    # show the AI chatbot dashboard.
    return FileResponse(
        os.path.join(
            BASE_DIR,
            "templates",
            "index.html"
        )
    )


# ============================================================
# LOGIN PAGE
# ============================================================

@app.get("/login")
def login_page(request: Request):

    # If already logged in,
    # don't show login page again.
    user = get_optional_user(request)

    if user:

        return RedirectResponse(
            url="/",
            status_code=302
        )

    return FileResponse(
        os.path.join(
            BASE_DIR,
            "templates",
            "login.html"
        )
    )


# ============================================================
# SIGN UP
# ============================================================

@app.post("/api/signup")
def signup(
    data: SignupRequest,
    response: Response
):

    name = data.name.strip()


    if len(name) < 2:

        raise HTTPException(
            status_code=400,
            detail="Please enter your full name."
        )


    if not is_valid_email(data.email):

        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address."
        )


    if not is_valid_password(data.password):

        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters long."
        )


    existing_user = get_user_by_email(
        data.email
    )


    if existing_user:

        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email "
                "already exists. Please log in instead."
            )
        )


    password_hash = hash_password(
        data.password
    )


    user = create_user(
        name,
        data.email,
        password_hash
    )


    if not user:

        raise HTTPException(
            status_code=409,
            detail=(
                "An account with this email "
                "already exists. Please log in instead."
            )
        )


    token, expires_at = create_session(
        user["id"]
    )


    response.set_cookie(

        key=SESSION_COOKIE_NAME,

        value=token,

        httponly=True,

        samesite="lax",

        expires=int(
            expires_at.timestamp()
        ),

        path="/"

    )


    return {

        "success": True,

        "message":
            "Account created successfully!",

        "user": {

            "name":
                user["name"],

            "email":
                user["email"]

        }

    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login")
def login(
    data: LoginRequest,
    response: Response
):

    user = get_user_by_email(
        data.email
    )


    if (

        not user

        or not verify_password(
            data.password,
            user["password_hash"]
        )

    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )


    token, expires_at = create_session(
        user["id"]
    )


    response.set_cookie(

        key=SESSION_COOKIE_NAME,

        value=token,

        httponly=True,

        samesite="lax",

        expires=int(
            expires_at.timestamp()
        ),

        path="/"

    )


    return {

        "success": True,

        "message":
            "Logged in successfully!",

        "user": {

            "name":
                user["name"],

            "email":
                user["email"]

        }

    }


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/logout")
def logout(
    request: Request,
    response: Response
):

    token = request.cookies.get(
        SESSION_COOKIE_NAME
    )


    if token:

        delete_session(token)


    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/"
    )


    return {

        "success": True,

        "message":
            "Logged out successfully!"

    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
def me(
    user=Depends(get_optional_user)
):

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )


    return {

        "success": True,

        "user": {

            "name":
                user["name"],

            "email":
                user["email"]

        }

    }


# ============================================================
# UPLOAD FILE
# ============================================================

@app.post("/upload")
async def upload_file(

    file: UploadFile = File(...),

    user=Depends(get_current_user)

):

    filename = os.path.basename(
        file.filename
    )


    ext = os.path.splitext(
        filename
    )[1].lower()


    if ext not in ALLOWED_EXTENSIONS:

        raise HTTPException(

            status_code=400,

            detail=(
                "Unsupported file type. Allowed: "
                +
                ", ".join(
                    sorted(
                        ALLOWED_EXTENSIONS
                    )
                )
            )

        )


    filepath = os.path.join(

        UPLOAD_FOLDER,

        f"{user['uuid']}_{filename}"

    )


    # Save uploaded file
    with open(
        filepath,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    # Extract text
    try:

        extracted_text = (
            extract_text_from_file(
                filepath
            )
        )

    except Exception as error:

        if os.path.exists(
            filepath
        ):

            os.remove(
                filepath
            )


        raise HTTPException(

            status_code=400,

            detail=(
                f"Could not read file: {error}"
            )

        )


    # Save database record
    pdf_uuid = add_pdf(

        user["id"],

        filename,

        filepath,

        extracted_text

    )


    return {

        "success": True,

        "message":
            "File uploaded successfully!",

        "filename":
            filename,

        "uuid":
            pdf_uuid,

        "characters":
            len(extracted_text)

    }


# ============================================================
# GET PDFs
# ============================================================

@app.get("/pdfs")
def list_pdfs(
    user=Depends(get_current_user)
):

    pdfs = get_all_pdfs(
        user["id"]
    )


    return {

        "success": True,

        "count":
            len(pdfs),

        "pdfs":
            pdfs

    }


# ============================================================
# DELETE PDF
# ============================================================

@app.delete("/pdfs/{pdf_uuid}")
def remove_pdf(

    pdf_uuid: str,

    user=Depends(get_current_user)

):

    filepath = delete_pdf(

        user["id"],

        pdf_uuid

    )


    if not filepath:

        raise HTTPException(

            status_code=404,

            detail="PDF not found."

        )


    if os.path.exists(
        filepath
    ):

        os.remove(
            filepath
        )


    return {

        "success": True,

        "message":
            "PDF deleted successfully!",

        "uuid":
            pdf_uuid

    }


# ============================================================
# ASK AI
# ============================================================

@app.post("/ask")
def ask_question(

    data: QuestionRequest,

    user=Depends(get_current_user)

):

    try:

        # ----------------------------------------------------
        # GET PDFS
        # ----------------------------------------------------

        pdfs = []


        if data.use_pdfs:

            if data.pdf_uuids:

                pdfs = get_selected_pdf_text(

                    user["id"],

                    data.pdf_uuids

                )


                if not pdfs:

                    raise HTTPException(

                        status_code=404,

                        detail=(
                            "Selected PDFs were not found."
                        )

                    )

            else:

                pdfs = get_all_pdf_text(
                    user["id"]
                )


        # ----------------------------------------------------
        # CHAT HISTORY
        # ----------------------------------------------------

        history = get_chat_history(
            user["id"]
        )


        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        answer = ask_ai(

            data.question,

            pdfs,

            history

        )


        # ----------------------------------------------------
        # SOURCES
        # ----------------------------------------------------

        sources = []


        if (

            data.use_pdfs

            and
            "SOURCE_PDFS:" in answer

        ):

            answer_parts = answer.split(

                "SOURCE_PDFS:",

                1

            )


            answer = (
                answer_parts[0].strip()
            )


            source_text = (
                answer_parts[1].strip()
            )


            for line in source_text.splitlines():

                filename = line.strip()


                if (

                    filename

                    and
                    filename not in sources

                ):

                    sources.append(
                        filename
                    )


        # ----------------------------------------------------
        # SAVE CHAT
        # ----------------------------------------------------

        add_chat(

            user["id"],

            data.question,

            answer,

            sources

        )


        return {

            "success": True,

            "question":
                data.question,

            "answer":
                answer,

            "sources":
                sources

        }


    except HTTPException:

        raise


    except Exception as error:

        raise HTTPException(

            status_code=500,

            detail=str(error)

        )


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/chat-history")
def chat_history(
    user=Depends(get_current_user)
):

    chats = get_chat_history(
        user["id"]
    )


    return {

        "success": True,

        "count":
            len(chats),

        "history":
            chats

    }


# ============================================================
# CLEAR CHAT
# ============================================================

@app.delete("/chat-history")
def clear_history(
    user=Depends(get_current_user)
):

    clear_chat_history(
        user["id"]
    )


    return {

        "success": True,

        "message":
            "Chat history cleared successfully!"

    }