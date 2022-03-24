set -euo pipefail

rm -rf dev
virtualenv dev
source  dev/bin/activate
set -x
python -m pip install telescope --find-links https://github.com/astronomer/telescope/releases/

TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes --docker --local

TELESCOPE_KUBERNETES_METHOD=kubectl TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes

set +x
deactivate
rm -rf dev
