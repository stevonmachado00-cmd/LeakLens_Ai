from app.main import app

print('Total routes:', len(app.routes))
for r in app.routes:
    try:
        methods = ','.join(r.methods)
    except Exception:
        methods = ''
    print(r.path, methods)
