import json

from app.main import app

routes = []
for route in app.routes:
    routes.append(getattr(route, "path", route.name))

with open("routes.json", "w", encoding="utf-8") as f:
    json.dump(routes, f)
