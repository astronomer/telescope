set -euo pipefail

rm -rf dev
virtualenv dev
source  dev/bin/activate
set -x
python -m pip install astronomer_telescope==$(poetry version --short)

LOG_LEVEL=DEBUG TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) astronomer_telescope --kubernetes --docker --local -n Astronomer

LOG_LEVEL=DEBUG TELESCOPE_KUBERNETES_METHOD=kubectl TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) astronomer_telescope --kubernetes -n Astronomer

LOG_LEVEL=DEBUG TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) astronomer_telescope --kubernetes --dag-obfuscation -n Astronomer

set +x
deactivate
rm -rf dev
