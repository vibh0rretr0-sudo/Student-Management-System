"""SMS backend: plain-Python HTTP server, models, and routes.

Reading order for the curious — each layer only knows the one below it:

    server.py        socket -> Request -> dispatch() -> Response -> socket
    routes/          URL patterns -> handler functions (the "controllers")
    models/          every SQL query lives here; parameterized, nothing else
    auth.py          password hashing + the in-memory session store
    cpp_engine.py    subprocess bridge to the C++ compute engine
    config.py        host/port/DB credentials (git-ignored; see config.example.py)

There is no web framework anywhere: http.server provides the socket, a
hand-rolled route table provides the "router", and plain strings provide
the templates. That restraint is the point of the project — see
docs/OVERVIEW.md for the full rationale.
"""
