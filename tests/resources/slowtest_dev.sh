set -euo pipefail

rm -rf dev
virtualenv dev
source  dev/bin/activate
set -x
python -m pip install telescope poetry --find-links https://github.com/astronomer/telescope/releases/tag/v$(poetry version --short)

LOG_LEVEL=DEBUG TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes --docker --local -n Astronomer

LOG_LEVEL=DEBUG TELESCOPE_KUBERNETES_METHOD=kubectl TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes -n Astronomer

LOG_LEVEL=DEBUG TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes --dag-obfuscation -n Astronomer

set +x
deactivate
rm -rf dev
