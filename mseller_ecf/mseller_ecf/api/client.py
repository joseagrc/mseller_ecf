from __future__ import annotations

import json
from typing import Any

import frappe
import requests
from frappe import _

from mseller_ecf.mseller_ecf.api.exceptions import (
    MSellerECFAuthenticationError,
    MSellerECFConfigurationError,
    MSellerECFRequestError,
)

BASE_URL = "https://ecf.api.mseller.app"
VALID_ENVIRONMENTS = {"TesteCF", "CerteCF", "eCF"}


class MSellerECFClient:
    def __init__(self, settings=None):
        self.settings = settings or frappe.get_single("MSeller ECF Settings")
        self._validate_settings()
        self.base_url = f"{BASE_URL}/{self.settings.environment}"

    def _validate_settings(self):
        if not self.settings.enabled:
            raise MSellerECFConfigurationError(_("MSeller ECF integration is disabled."))

        if self.settings.environment not in VALID_ENVIRONMENTS:
            raise MSellerECFConfigurationError(_("Invalid MSeller ECF environment."))

        missing = []
        for fieldname in ("email", "password", "api_key"):
            value = self.settings.get_password(fieldname) if fieldname in {"password", "api_key"} else self.settings.get(fieldname)
            if not value:
                missing.append(fieldname)

        if missing:
            raise MSellerECFConfigurationError(
                _("Missing MSeller ECF setting values: {0}").format(", ".join(missing))
            )

    def authenticate(self) -> str:
        response = self._request(
            "POST",
            "/customer/authentication",
            authenticated=False,
            json_body={
                "email": self.settings.email,
                "password": self.settings.get_password("password"),
            },
        )

        id_token = response.get("idToken")
        if not id_token:
            raise MSellerECFAuthenticationError(_("MSeller authentication response did not include idToken."))

        self.settings.db_set("id_token", id_token, update_modified=False)
        if response.get("accessToken"):
            self.settings.db_set("access_token", response.get("accessToken"), update_modified=False)
        if response.get("refreshToken"):
            self.settings.db_set("refresh_token", response.get("refreshToken"), update_modified=False)

        frappe.db.commit()
        return id_token

    def send_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/documentos-ecf", json_body=payload, retry_auth=True)

    def get_document(self, ecf: str) -> dict[str, Any]:
        return self._request("GET", "/documentos-ecf", params={"ecf": ecf}, retry_auth=True)

    def get_documents_batch(self, ecfs: list[str]) -> dict[str, Any]:
        if len(ecfs) > 100:
            raise MSellerECFRequestError(_("MSeller batch status lookup accepts at most 100 e-CF numbers."))

        return self._request(
            "POST",
            "/documentos-ecf/status/batch",
            json_body={"ecfs": ecfs},
            retry_auth=True,
        )

    def _headers(self) -> dict[str, str]:
        id_token = self.settings.get_password("id_token")
        if not id_token:
            id_token = self.authenticate()

        return {
            "Authorization": f"Bearer {id_token}",
            "X-API-KEY": self.settings.get_password("api_key"),
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        retry_auth: bool = False,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._headers() if authenticated else {"Content-Type": "application/json"}

        response = requests.request(
            method,
            url,
            headers=headers,
            json=json_body,
            params=params,
            timeout=(10, 60),
        )

        if response.status_code == 401 and authenticated and retry_auth:
            self.authenticate()
            headers = self._headers()
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=(10, 60),
            )

        if response.status_code in {401, 403}:
            raise MSellerECFAuthenticationError(self._response_message(response))

        if response.status_code >= 400:
            raise MSellerECFRequestError(
                self._response_message(response),
                status_code=response.status_code,
                response_text=response.text,
            )

        try:
            return response.json()
        except json.JSONDecodeError:
            raise MSellerECFRequestError(
                _("MSeller returned a non-JSON response."),
                status_code=response.status_code,
                response_text=response.text,
            )

    @staticmethod
    def _response_message(response) -> str:
        try:
            data = response.json()
        except json.JSONDecodeError:
            return response.text or _("MSeller API request failed.")

        if isinstance(data, dict):
            return data.get("message") or data.get("error") or json.dumps(data, ensure_ascii=False)

        return str(data)
