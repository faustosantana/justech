"""Reautenticación Administración Justech — secretos solo por hash/env, nunca plaintext en Git."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

SCOPE_ADMIN_CENTER = "admin_center"
ENV_HASH = "JUSTECH_ADMIN_CENTER_PASSWORD_HASH"
MAX_ATTEMPTS_DEFAULT = 5
SESSION_MINUTES_DEFAULT = 15


class JustechAdminCenterAuthService(models.AbstractModel):
    _name = "justech.admin.center.auth.service"
    _description = "Autenticación reforzada Consola Justech"

    @api.model
    def scope(self):
        return SCOPE_ADMIN_CENTER

    @api.model
    def user_is_authorized(self, user=None):
        user = user or self.env.user
        return user.has_group("base.group_system") or user.has_group(
            "justech_admin_center.group_justech_admin_center_manager"
        )

    @api.model
    def require_authorized_user(self, user=None):
        if not self.user_is_authorized(user=user):
            raise AccessError(
                _("No está autorizado para Administración Justech.")
            )

    @api.model
    def is_session_valid(self):
        self.require_authorized_user()
        Access = self.env["justech.admin.access.service"]
        token = self.env.context.get(Access._session_token_param(self.scope()))
        if not token:
            token = self.env["ir.config_parameter"].sudo().get_param(
                Access._session_storage_key(self.scope())
            )
        if not token:
            return False
        token_hash = Access._hash_session_token(token)
        session = self.env["justech.admin.session"].find_valid(
            self.env.user, self.scope(), token_hash
        )
        return bool(session)

    @api.model
    def require_session(self):
        self.require_authorized_user()
        if self.is_session_valid():
            return True
        raise AccessError(
            _(
                "Debe reautenticarse con la clave maestra de Administración Justech. "
                "La sesión dura %(mins)s minutos."
            )
            % {"mins": SESSION_MINUTES_DEFAULT}
        )

    @api.model
    def _env_hash(self):
        value = (os.environ.get(ENV_HASH) or "").strip()
        if value:
            return value
        # Server secret file (never in Git): one-line PBKDF2 hash
        secret_path = "/opt/odoo-dev/secrets/justech_admin_center_password.hash"
        try:
            if os.path.isfile(secret_path):
                with open(secret_path, "r", encoding="utf-8") as fh:
                    return (fh.read() or "").strip()
        except OSError:
            pass
        return ""

    @api.model
    def _verify_pbkdf2(self, password: str, encoded: str) -> bool:
        """Format: pbkdf2_sha256$iterations$salt_b64$hash_b64"""
        try:
            algo, iterations_s, salt_b64, hash_b64 = encoded.split("$", 3)
        except ValueError:
            return False
        if algo != "pbkdf2_sha256":
            return False
        try:
            iterations = int(iterations_s)
            salt = base64.b64decode(salt_b64.encode())
            expected = base64.b64decode(hash_b64.encode())
        except Exception:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
        )
        return hmac.compare_digest(digest, expected)

    @api.model
    def make_pbkdf2_hash(self, password: str, iterations: int = 200_000) -> str:
        """Utility for ops — never call with secrets from source code."""
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return "pbkdf2_sha256$%s$%s$%s" % (
            iterations,
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        )

    @api.model
    def _audit_attempt(self, success, reason=""):
        # Never log the password
        self.env["justech.admin.audit.log"].sudo().log_simple(
            summary=_("Reautenticación consola: %s") % ("OK" if success else "FALLIDA"),
            operation="admin_center_reauth",
            result="ok" if success else "error",
            error=reason if not success else False,
            reason=_("Intento de acceso a Administración Justech"),
        )

    @api.model
    def _max_attempts(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("justech_admin_center.max_auth_attempts", str(MAX_ATTEMPTS_DEFAULT))
        )

    @api.model
    def _lock_minutes(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("justech_admin_center.auth_lock_minutes", "15")
        )

    @api.model
    def _attempt_key(self):
        return "justech_admin_center.auth_fail.%s" % self.env.uid

    @api.model
    def _check_rate_limit(self):
        ICP = self.env["ir.config_parameter"].sudo()
        raw = ICP.get_param(self._attempt_key()) or ""
        if not raw:
            return
        try:
            count_s, until_s = raw.split("|", 1)
            count = int(count_s)
            until = fields.Datetime.from_string(until_s) if until_s else None
        except Exception:
            return
        now = fields.Datetime.now()
        if until and until > now and count >= self._max_attempts():
            raise UserError(
                _("Acceso bloqueado temporalmente por intentos fallidos. Intente más tarde.")
            )

    @api.model
    def _register_failure(self):
        from datetime import timedelta

        ICP = self.env["ir.config_parameter"].sudo()
        raw = ICP.get_param(self._attempt_key()) or "0|"
        try:
            count = int(raw.split("|", 1)[0] or 0)
        except Exception:
            count = 0
        count += 1
        until = fields.Datetime.now() + timedelta(minutes=self._lock_minutes())
        ICP.set_param(self._attempt_key(), "%s|%s" % (count, fields.Datetime.to_string(until)))

    @api.model
    def _clear_failures(self):
        self.env["ir.config_parameter"].sudo().set_param(self._attempt_key(), False)

    @api.model
    def verify_and_open_session(self, password):
        """Verify master secret and open scoped session. Password never stored."""
        self.require_authorized_user()
        self._check_rate_limit()
        if not password or not str(password).strip():
            self._audit_attempt(False, "empty")
            self._register_failure()
            raise UserError(_("Introduzca la clave maestra."))

        password = str(password).strip()
        env_hash = self._env_hash()
        verified = False
        reason = ""

        if env_hash:
            verified = self._verify_pbkdf2(password, env_hash)
            reason = "env_hash_mismatch" if not verified else "env_hash"
        elif "justech.admin.access.service" in self.env:
            Access = self.env["justech.admin.access.service"]
            try:
                Access.verify_key_only(password, action="admin_center")
                verified = True
                reason = "justech_admin_key"
            except UserError as exc:
                verified = False
                reason = str(exc)[:120]
                self._register_failure()
                self._audit_attempt(False, reason)
                raise
        else:
            self._audit_attempt(False, "no_secret_configured")
            raise UserError(
                _(
                    "No hay secreto configurado. Defina %(env)s en el servidor "
                    "o configure la Clave Administrativa Justech."
                )
                % {"env": ENV_HASH}
            )

        if not verified:
            self._register_failure()
            self._audit_attempt(False, reason)
            raise UserError(_("Clave maestra incorrecta."))

        # Open session via existing infra
        Access = self.env["justech.admin.access.service"]
        if reason == "env_hash":
            # Open session without re-checking user key store: mint token directly
            token = secrets.token_urlsafe(32)
            token_hash = Access._hash_session_token(token)
            self.env["justech.admin.session"].create_session(
                self.env.user, self.scope(), token_hash, Access._get_request_ip()
            )
            self.env["ir.config_parameter"].sudo().set_param(
                Access._session_storage_key(self.scope()), token
            )
        else:
            Access.open_session(password, scope=self.scope())

        self._clear_failures()
        self._audit_attempt(True, reason)
        return True

    @api.model
    def ensure_session_or_wizard(self):
        """Return True if session OK, else action to open auth wizard."""
        self.require_authorized_user()
        if self.is_session_valid():
            return True
        return self.env["justech.admin.auth.wizard"].action_open()
