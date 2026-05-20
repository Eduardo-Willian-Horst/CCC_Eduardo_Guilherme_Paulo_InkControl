"""RNF01: header X-Response-Time-Ms em todas as respostas HTTP."""

import time


class ResponseTimeMiddleware:
    """RNF01: expoe tempo de resposta no header para monitoramento simples."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response["X-Response-Time-Ms"] = str(elapsed_ms)
        return response
