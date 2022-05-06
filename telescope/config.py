"""Set some variables for re-use across the project"""
import os
import telescope

VERSION = os.getenv("TELESCOPE_REPORT_RELEASE_VERSION", telescope.version)
AIRGAPPED = os.getenv("KUBERNETES_AIRGAPPED", "").lower() == "true"
REPORT_PACKAGE = "airflow_report.pyz"
REPORT_PACKAGE_URL = f"https://github.com/astronomer/telescope/releases/download/v{VERSION}/{REPORT_PACKAGE}"
