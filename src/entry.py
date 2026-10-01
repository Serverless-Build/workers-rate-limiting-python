import re
from urllib.parse import urlparse, parse_qs
from pyodide.ffi import to_js
from js import Object
from workers import Response, WorkerEntrypoint

MARKER = "SERVERLESS_BUILD_RATE_LIMITING_PYTHON_V1"


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        if request.method == "GET" and url.path == "/":
            return Response.json({"pattern": "Workers Rate Limiting binding", "marker": MARKER,
                                  "endpoints": ["GET /limited?actor=...", "GET /health"],
                                  "limit": "5 requests per 10 seconds per actor, per Cloudflare location"})
        if request.method == "GET" and url.path == "/health":
            return Response.json({"ok": True, "marker": MARKER})
        if request.method != "GET" or url.path != "/limited":
            return Response.json({"error": "Not found"}, status=404)
        # DEMO identity only: use a verified user/tenant ID in your application.
        actor = parse_qs(url.query).get("actor", [""])[0]
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", actor):
            return Response.json({"error": "Provide an actor of 1–40 letters, numbers, hyphens, or underscores."}, status=400)
        outcome = await self.env.RATE_LIMITER.limit(to_js({"key": f"demo:{actor}:/limited"}, dict_converter=Object.fromEntries))
        data = {"allowed": True, "actor": actor, "marker": MARKER} if outcome.success else {"error": "Rate limit exceeded", "actor": actor, "marker": MARKER}
        return Response.json(data, status=200 if outcome.success else 429, headers={"cache-control": "no-store"})
