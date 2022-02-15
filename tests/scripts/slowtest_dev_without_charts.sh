set -euxo pipefail

rm -rf withoutcharts
virtualenv withoutcharts
source withoutcharts/bin/activate
#python -m pip install "telescope @ git+https://github.com/astronomer/telescope.git@dev#egg=telescope"
python -m pip install telescope --find-links https://github.com/astronomer/telescope/releases/
TELESCOPE_AIRFLOW_REPORT_BRANCH=dev telescope --kubernetes --cluster-info --docker --verify --report --charts --versions
deactivate
rm -rf withoutcharts
