set -euo pipefail

rm -rf withoutcharts
virtualenv withoutcharts
source withoutcharts/bin/activate
set -x
python -m pip install telescope --find-links https://github.com/astronomer/telescope/releases/
TELESCOPE_REPORT_RELEASE_VERSION=$(poetry version --short) telescope --kubernetes --cluster-info --docker --verify --local --report --charts --versions
set +x
deactivate
rm -rf withoutcharts
