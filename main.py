from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from auth_routes import auth

app = FastAPI()

# ✅ Include auth routes with or without prefix — choose only one
app.include_router(auth)  # or app.include_router(auth, prefix="/auth", tags=["auth"])

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

@app.get("/profile", response_class=HTMLResponse, name="profile")
def profile(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.get("/", response_class=HTMLResponse, name="login")
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

  # adjust the filename

