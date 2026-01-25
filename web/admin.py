from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")

        # Use your existing login logic here
        # result = login(email, password, db)
        # if result["success"] and result["data"]["user"]["is_admin"]:
        #     request.session.update({"token": "..."})
        #     return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        # Check if the session has a valid token
        return "token" in request.session

# Apply authentication to admin
authentication_backend = AdminAuth(secret_key="your-secret-key")
admin = Admin(app, engine, authentication=authentication_backend)