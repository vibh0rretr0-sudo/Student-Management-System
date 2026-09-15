"""HTTP route modules.

Importing this package registers every route on the shared router in
backend.routes.helpers. The server then handles each request through
helpers.dispatch().
"""
from backend.routes import (  # noqa: F401
    analytics_routes,
    announcement_routes,
    assessment_routes,
    attendance_routes,
    auth_routes,
    course_routes,
    dashboard_routes,
    pref_routes,
    static_routes,
    student_routes,
)
