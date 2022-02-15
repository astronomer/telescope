set -euxo pipefail

rm -rf withcharts
virtualenv withcharts
source withcharts/bin/activate
python -m pip install "telescope[charts] @ git+https://github.com/astronomer/telescope.git@dev#egg=telescope"
#python -m pip install "telescope[charts] @ https://github.com/astronomer/telescope/blob/dev/telescope-$(poetry version --short)-py3-none-any.whl?raw=true"
TELESCOPE_AIRFLOW_REPORT_BRANCH=dev telescope --kubernetes --cluster-info --docker --verify --report --charts --versions
deactivate
rm -rf withcharts
