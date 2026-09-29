from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from qna import ask_gemini

from database import (
    create_tables,
    create_user,
    authenticate_user,
    create_conversation,
    save_message,
    get_messages,
    get_conversations,
    update_conversation_title,
    conversation_belongs_to_user,
    delete_conversation
)

app = FastAPI(title="EduGenie")

templates = Jinja2Templates(directory="templates")


# =========================================================
# MODELS
# =========================================================

class Message(BaseModel):
    role: str
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: list[Message] = []
    conversation_id: int | None = None


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
def startup():
    create_tables()


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home(request: Request):

    user_id = request.cookies.get("user_id")

    if not user_id:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return RedirectResponse(
        url="/chat",
        status_code=303
    )


# =========================================================
# REGISTER PAGE
# =========================================================

@app.get("/register")
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "request": request,
            "error": None
        }
    )


# =========================================================
# REGISTER USER
# =========================================================

@app.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    username = username.strip()

    if not username or not password:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "Username and password are required."
            }
        )

    if len(password) < 6:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "Password must contain at least 6 characters."
            }
        )

    user_id = create_user(
        username,
        password
    )

    if user_id is None:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "Username already exists."
            }
        )

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# =========================================================
# LOGIN PAGE
# =========================================================

@app.get("/login")
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "error": None
        }
    )


# =========================================================
# LOGIN USER
# =========================================================

@app.post("/login")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    username = username.strip()

    user = authenticate_user(
        username,
        password
    )

    if user is None:

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Invalid username or password."
            }
        )

    response = RedirectResponse(
        url="/chat",
        status_code=303
    )

    response.set_cookie(
        key="user_id",
        value=str(user["id"]),
        httponly=True,
        samesite="lax"
    )

    return response


# =========================================================
# LOGOUT
# =========================================================

@app.get("/logout")
def logout():

    response = RedirectResponse(
        url="/login",
        status_code=303
    )

    response.delete_cookie("user_id")

    return response


# =========================================================
# CHAT PAGE
# =========================================================

@app.get("/chat")
def chat_page(request: Request):

    user_id = request.cookies.get("user_id")

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "conversation_id": ""
        }
    )


# =========================================================
# ASK EDU GENIE
# =========================================================

@app.post("/qa")
def question_answer(
    request: QuestionRequest,
    http_request: Request
):

    user_id = http_request.cookies.get("user_id")

    if not user_id:

        return {
            "error": "Not authenticated"
        }

    try:
        user_id = int(user_id)
    except ValueError:

        return {
            "error": "Invalid user session"
        }

    conversation_id = request.conversation_id

    # -----------------------------------------------------
    # Create a conversation if necessary
    # -----------------------------------------------------

    if conversation_id is None or conversation_id == 0:

        conversation_id = create_conversation(
            user_id
        )

    # -----------------------------------------------------
    # Security check
    # -----------------------------------------------------

    if not conversation_belongs_to_user(
        conversation_id,
        user_id
    ):

        return {
            "error": "Conversation does not belong to this user."
        }

    # -----------------------------------------------------
    # Get saved conversation history
    # -----------------------------------------------------

    saved_messages = get_messages(
        conversation_id
    )

    history = []

    for message in saved_messages:

        history.append(
            Message(
                role=message["role"],
                content=message["content"]
            )
        )

    # -----------------------------------------------------
    # If no saved history exists,
    # use history sent by browser
    # -----------------------------------------------------

    if not history:

        history = request.history

    # -----------------------------------------------------
    # Ask Gemini
    # -----------------------------------------------------

    try:

        answer = ask_gemini(
            request.question,
            history
        )

    except Exception as e:

        print("Gemini error:", e)

        return {
            "error": "Unable to get an answer from EduGenie right now."
        }

    # -----------------------------------------------------
    # Give conversation a title
    # -----------------------------------------------------

    if not saved_messages:

        title = request.question.strip()

        if len(title) > 40:

            title = title[:40] + "..."

        update_conversation_title(
            conversation_id,
            title
        )

    # -----------------------------------------------------
    # Save user's question
    # -----------------------------------------------------

    save_message(
        conversation_id,
        "user",
        request.question
    )

    # -----------------------------------------------------
    # Save Gemini's answer
    # -----------------------------------------------------

    save_message(
        conversation_id,
        "assistant",
        answer
    )

    # -----------------------------------------------------
    # Return answer
    # -----------------------------------------------------

    return {
        "question": request.question,
        "answer": answer,
        "conversation_id": conversation_id
    }


# =========================================================
# GET ALL CONVERSATIONS
# =========================================================

@app.get("/conversations")
def conversations(request: Request):

    user_id = request.cookies.get("user_id")

    if not user_id:

        return []

    try:
        user_id = int(user_id)
    except ValueError:

        return []

    saved_conversations = get_conversations(
        user_id
    )

    return [
        {
            "id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"]
        }
        for conversation in saved_conversations
    ]


# =========================================================
# GET SINGLE CONVERSATION
# =========================================================

@app.get("/conversations/{conversation_id}")
def conversation(
    conversation_id: int,
    request: Request
):

    user_id = request.cookies.get("user_id")

    if not user_id:

        return []

    try:
        user_id = int(user_id)
    except ValueError:

        return []

    # -----------------------------------------------------
    # Security check
    # -----------------------------------------------------

    if not conversation_belongs_to_user(
        conversation_id,
        user_id
    ):

        return []

    messages = get_messages(
        conversation_id
    )

    return [
        {
            "role": message["role"],
            "content": message["content"]
        }
        for message in messages
    ]


# =========================================================
# DELETE CONVERSATION
# =========================================================

@app.delete("/conversations/{conversation_id}")
def delete_chat(
    conversation_id: int,
    request: Request
):

    user_id = request.cookies.get("user_id")

    if not user_id:
        return {
            "success": False,
            "error": "Not authenticated"
        }

    try:
        user_id = int(user_id)
    except ValueError:
        return {
            "success": False,
            "error": "Invalid user"
        }

    deleted = delete_conversation(
        conversation_id,
        user_id
    )

    if not deleted:
        return {
            "success": False,
            "error": "Conversation not found."
        }

    return {
        "success": True
    }