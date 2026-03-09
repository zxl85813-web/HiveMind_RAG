from app.main import app

for route in app.routes:
    print(getattr(route, "path", route.name))
