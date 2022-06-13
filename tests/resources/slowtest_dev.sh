set -euo pipefail

rm -rf dev
virtualenv dev
source  dev/bin/activate
set -x
python -m pip install telescope poetry --find-links https://github.com/astronomer/telescope/releases/tag/v$(poetry version --short)

TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes --docker --local -n Astronomer

TELESCOPE_KUBERNETES_METHOD=kubectl TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes -n Astronomer

TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes --dag-obfuscation -n Astronomer

echo "%%%%% Running "
TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) TELESCOPE_KUBERNETES_AIRGAPPED=true telescope --kubernetes -n Astronomer

set +x
deactivate
rm -rf dev
