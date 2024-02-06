"""Set some variables for re-use across the project"""
import os

import astronomer_telescope

VERSION = os.getenv("TELESCOPE_REPORT_RELEASE_VERSION", astronomer_telescope.version)
AIRGAPPED = os.getenv("TELESCOPE_KUBERNETES_AIRGAPPED", "false").lower() == "true"
REPORT_PACKAGE = "airflow_report.pyz"
REPORT_PACKAGE_URL = os.getenv(
    "TELESCOPE_REPORT_PACKAGE_URL",
    f"https://github.com/astronomer/telescope/releases/download/v{VERSION}/{REPORT_PACKAGE}",
)
