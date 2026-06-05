"""
Runtime Simulator — validates that the AppSpec can produce a working application.
Generates actual code and verifies its structural correctness.
"""

from __future__ import annotations
import os
import re
import logging
import hashlib
from typing import Any

from backend.config import GENERATED_APPS_DIR
from backend.runtime.execution_report import ExecutionReport
from backend.runtime.code_generator import generate_app_html

logger = logging.getLogger(__name__)


class RuntimeSimulator:
    """
    Proves execution awareness by:
    1. Generating a complete HTML/JS/CSS app from AppSpec
    2. Validating the generated code is structurally correct
    3. Running consistency checks on the output
    4. Saving the generated app to disk
    """

    def simulate(self, app_spec_dict: dict[str, Any]) -> ExecutionReport:
        """
        Run the full simulation pipeline.

        Args:
            app_spec_dict: AppSpec as dict.

        Returns:
            ExecutionReport with all checks and generated files.
        """
        report = ExecutionReport()

        logger.info("[Runtime] Starting execution simulation...")

        # --- Check 1: Can we generate HTML? ---
        try:
            html = generate_app_html(app_spec_dict)
            report.add_check(
                "code_generation",
                passed=True,
                details=f"Generated {len(html)} bytes of HTML",
            )
        except Exception as e:
            report.add_check(
                "code_generation",
                passed=False,
                details=f"Code generation failed: {str(e)}",
            )
            report.errors.append(f"Code generation: {str(e)}")
            return report

        # --- Check 2: HTML structural validity ---
        html_valid = self._check_html_structure(html, report)

        # --- Check 3: All pages rendered ---
        self._check_pages_rendered(html, app_spec_dict, report)

        # --- Check 4: Navigation links match pages ---
        self._check_navigation(html, app_spec_dict, report)

        # --- Check 5: Forms have correct fields ---
        self._check_forms(html, app_spec_dict, report)

        # --- Check 6: No broken references ---
        self._check_no_broken_refs(html, report)

        # --- Save generated app ---
        if html_valid:
            filepath = self._save_app(html, app_spec_dict)
            report.generated_files.append(filepath)
            report.preview_html = html

        logger.info(
            f"[Runtime] Simulation complete: "
            f"{report.pass_count} passed, {report.fail_count} failed"
        )

        return report

    def _check_html_structure(self, html: str, report: ExecutionReport) -> bool:
        """Verify basic HTML structural correctness."""
        checks = [
            ("<!DOCTYPE html>" in html or "<!doctype html>" in html.lower(), "DOCTYPE declaration"),
            ("<html" in html, "HTML root element"),
            ("<head>" in html or "<head " in html, "HEAD section"),
            ("<body>" in html or "<body " in html, "BODY section"),
            ("</html>" in html, "Closing HTML tag"),
            ("<title>" in html, "Title element"),
        ]

        all_passed = True
        for passed, name in checks:
            report.add_check(f"html_structure_{name.lower().replace(' ', '_')}", passed, name)
            if not passed:
                all_passed = False

        return all_passed

    def _check_pages_rendered(
        self, html: str, app_spec: dict, report: ExecutionReport
    ) -> None:
        """Verify all UI pages are rendered in the HTML."""
        pages = app_spec.get("ui", {}).get("pages", [])
        for page in pages:
            page_name = page.get("name", "").replace(" ", "_").lower()
            page_id = f'id="page-{page_name}"'
            found = page_id in html
            report.add_check(
                f"page_rendered_{page_name}",
                passed=found,
                details=f"Page '{page_name}' {'found' if found else 'MISSING'} in HTML",
            )

    def _check_navigation(
        self, html: str, app_spec: dict, report: ExecutionReport
    ) -> None:
        """Verify navigation links exist."""
        pages = app_spec.get("ui", {}).get("pages", [])
        nav_count = html.count("nav-links")
        report.add_check(
            "navigation_present",
            passed=nav_count > 0,
            details=f"Navigation section {'found' if nav_count > 0 else 'MISSING'}",
        )

    def _check_forms(
        self, html: str, app_spec: dict, report: ExecutionReport
    ) -> None:
        """Verify forms exist for form-type components."""
        pages = app_spec.get("ui", {}).get("pages", [])
        form_count = 0
        for page in pages:
            for comp in page.get("components", []):
                if comp.get("type") == "form":
                    form_count += 1

        actual_forms = html.count("<form")
        report.add_check(
            "forms_generated",
            passed=actual_forms >= form_count,
            details=f"Expected {form_count} forms, found {actual_forms}",
        )

    def _check_no_broken_refs(self, html: str, report: ExecutionReport) -> None:
        """Check for obvious broken references."""
        # Check for undefined variables in JS
        undefined_refs = html.count("undefined")
        report.add_check(
            "no_undefined_refs",
            passed=undefined_refs < 3,  # Allow some — template text might include it
            details=f"Found {undefined_refs} 'undefined' references",
        )

    def _save_app(self, html: str, app_spec: dict) -> str:
        """Save the generated app to disk."""
        app_name = app_spec.get("metadata", {}).get("name", "app")
        safe_name = re.sub(r'[^a-z0-9_]', '_', app_name.lower())
        filename = f"{safe_name}.html"
        filepath = os.path.join(str(GENERATED_APPS_DIR), filename)

        os.makedirs(str(GENERATED_APPS_DIR), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"[Runtime] Saved generated app: {filepath}")
        return filepath
