"""JECRC Student & Faculty Portal application factory."""
from __future__ import annotations

import logging
import secrets
from pathlib import Path

from flask import Flask, g, redirect, render_template, request

from config import BASE_DIR, Config

from .db import close_db
from .security import check_csrf, is_mobile_user_agent
from .utils import json_err


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "static"),
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    app.config.setdefault("SEND_FILE_MAX_AGE_DEFAULT", 3600)

    from .blueprints.auth import bp as auth_bp
    from .blueprints.common import bp as common_bp
    from .blueprints.main import bp as pages_bp
    from .blueprints.professor import bp as professor_bp
    from .blueprints.student import bp as student_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(common_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(professor_bp)

    app.teardown_appcontext(close_db)

    # ------------------------------------------------------------------
    # Request pipeline: nonce, CSRF, device gating
    # ------------------------------------------------------------------
    @app.before_request
    def prepare_request():
        g.csp_nonce = secrets.token_urlsafe(16)
        if request.path.startswith("/api/"):
            csrf_response = check_csrf()
            if csrf_response is not None:
                return csrf_response
            return None
        if request.path.startswith("/static/"):
            return None
        if request.path == "/blocked":
            return None
        if is_mobile_user_agent():
            return render_template("blocked.html"), 200
        return None

    @app.after_request
    def security_headers(response):
        nonce = getattr(g, "csp_nonce", "")
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        if request.path.startswith("/static/"):
            if app.config.get("ENV_NAME") == "production":
                response.headers.setdefault("Cache-Control",
                                            "public, max-age=86400")
            else:
                # Development: always revalidate so edits show up immediately.
                response.headers["Cache-Control"] = "no-store"
        return response

    @app.context_processor
    def inject_globals():
        return {
            "csp_nonce": getattr(g, "csp_nonce", ""),
            "app_name": "JECRC Student & Faculty Portal",
        }

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------
    def wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(404)
    def not_found(_error):
        if wants_json():
            return json_err("We couldn't find that resource.", 404, "not_found")
        return render_template("error.html", status=404,
                               title="Page not found",
                               message="The page you're looking for has moved or "
                                       "never existed."), 404

    @app.errorhandler(413)
    def too_large(_error):
        message = "That file is larger than the 10 MB upload limit."
        if wants_json():
            return json_err(message, 413, "file_too_large")
        return render_template("error.html", status=413,
                               title="Upload too large", message=message), 413

    @app.errorhandler(403)
    def forbidden(_error):
        if wants_json():
            return json_err("You don't have access to that.", 403, "forbidden")
        return render_template("error.html", status=403, title="Access denied",
                               message="Your account doesn't have access to this "
                                       "resource."), 403

    @app.errorhandler(500)
    def server_error(error):
        app.logger.error("Unhandled error: %s", error, exc_info=True)
        if wants_json():
            return json_err("Something went wrong on our side. Please try again.",
                            500, "server_error")
        return render_template("error.html", status=500,
                               title="Something went wrong",
                               message="We hit an unexpected error. Try again or "
                                       "head back to the dashboard."), 500

    # ------------------------------------------------------------------
    # CLI helpers
    # ------------------------------------------------------------------
    @app.cli.command("init-db")
    def init_db_command():
        """Create (or recreate with --drop) the database schema."""
        import click

        from .db import init_db

        init_db(app, drop="--drop" in __import__("sys").argv)
        click.echo("Schema created.")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Load the demo dataset (idempotent)."""
        from .db import db_from_config
        from .seed import seed

        db = db_from_config(app.config)
        try:
            if (db.scalar("SELECT COUNT(*) AS c FROM users", default=0) or 0) > 0:
                print("Database already has users; skipping seed.")
            else:
                seed(db, app.config["UPLOAD_DIR"])
                print("Demo data loaded. Password for all accounts: Jecrc@2026")
        finally:
            db.close()

    logging.getLogger("werkzeug").setLevel(logging.INFO)
    return app
