from django.http import HttpResponse


def root(request):
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>InkControl API</title></head>
<body>
  <h1>InkControl — backend</h1>
  <p>Esta é só a API Django. A interface web roda no Vite.</p>
  <ul>
    <li><a href="/api/health/">/api/health/</a> — health check</li>
    <li><a href="/admin/">/admin/</a> — painel admin</li>
    <li><a href="http://127.0.0.1:5173/">http://127.0.0.1:5173/</a> — app (com <code>npm run dev</code> em <code>frontend/</code>)</li>
  </ul>
</body>
</html>"""
    return HttpResponse(html)
