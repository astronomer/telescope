# Telescope
![astronomer logo](astro.png)
[![Build status](https://github.com/telescope/telescope/workflows/build/badge.svg?branch=main&event=push)](https://github.com/telescope/telescope/actions?query=workflow%3Abuild)
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/telescope/telescope/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/telescope/telescope/blob/main/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/telescope/telescope/releases)

A tool to observe distant (or local!) Airflow installations, and gather metadata or other required data.

# Installation
(optionally, create a virtualenv)
```shell
mkdir telescope_run_dir
cd telescope_run_dir
virtualenv venv
. venv/bin/activate 
```

Install telescope using pip from Github
```shell
pip install git+https://github.com/astronomer/telescope.git#egg=telescope
```

# Quickstart - Kubernetes Autodiscovery Assessment Mode
This will work if your Airflows are in Kubernetes and were deployed with one of the major Helm charts (and `component=scheduler` is used to identify the schedulers). It will use Helm to interrogate the installation, and connect to the Airflow schedulers to gather metadata 
```shell
telescope --kubernetes --verify --cluster-info
```
You should now have a `report.json`, `report.xlsx`, and `charts/` directory.

# Quickstart - SSH Assessment Mode
This will work if your Airflow's are on hosts accessible via SSH and SSH is configured to connect to all of these hosts (e.g. you have `~/.ssh/config` with entries for all hosts)
Create a `hosts.yaml` file, like this, enumerating every host:
```shell
ssh:
  - host: airflow.foo1.bar.com
  - host: airflow.foo2.bar.com 
  - host: ...
```

```shell
telescope -f hosts.yaml
```
You should now have a `report.json`, `report.xlsx`, and `charts/` directory.

# Usage
```shell
$ telescope --help                                                
Usage: telescope [OPTIONS]

  Telescope - A tool to observe distant (or local!) Airflow installations, and
  gather usage metadata

Options:
  --version                       Show the version and exit.
  --local                         checks versions of locally installed tools
                                  [default: False]
  --docker                        autodiscovery and airflow reporting for
                                  local docker  [default: False]
  --kubernetes                    autodiscovery and airflow reporting for
                                  kubernetes  [default: False]
  -l, --label-selector TEXT       Label selector for Kubernetes Autodiscovery
                                  [default: component=scheduler]
  --cluster-info                  get cluster size and allocation in
                                  kubernetes  [default: False]
  --verify                        adds helm installations to report  [default:
                                  False]
  --precheck                      runs Astronomer Enterprise pre-install
                                  sanity-checks in the report  [default:
                                  False]
  -f, --hosts-file PATH           Hosts file to pass in various types of hosts
                                  (ssh, kubernetes, docker) - See README.md
                                  for sample
  -o, --output-file PATH          Output file to write intermediate gathered
                                  data json, and report (with report_type as
                                  file extension), can be '-' for stdout
                                  [default: report.json]
  -p, --parallelism INTEGER       How many cores to use for multiprocessing
                                  [default: (Number CPU)]
  --gather / --no-gather          gather data about Airflow environments
                                  [default: gather]
  --report / --no-report          generate report summary of gathered data
                                  [default: report]
  --report-type [html|json|csv|xlsx]
                                  What report type to generate
  --help                          Show this message and exit.
```

# Requirements
## Locally - Python
- Python >=3.9
- `pip`

## Locally - Docker or Kubernetes or SSH Airflow Assessment modes
- **Docker**: Permissions to Exec Containers, `docker.sock` Access locally
- **Kubernetes**: Permission to List Nodes and Exec in Pods, `KUBECONFIG` set locally
- **SSH**: Credentials to connect to all hosts, SSH Access configured locally

## Remote Airflow Requirements
- Airflow Scheduler >1.10.5
- Kubernetes Scheduler has label `component=scheduler` (or `--label-selector` specified)
- Python 3
- Curl
- Postgresql/Mysql/Sqlite Metadata Database (support not guaranteed for other backing databases)

# Input
## Docker autodiscovery
Either use `--docker` or have an empty `docker` key in your hosts file to enable autodiscovery.
Autodiscovery searches for containers running locally that contain "scheduler" in the name and returns
the container_id

- `hosts.yaml`
```
docker: 
```

## Kubernetes autodiscovery
Either use `--kubernetes` or an empty `kubernets` in your hosts file to enable autodiscovery.
Autodiscovery searches for pods running in the Kubernetes cluster defined by `KUBEPROFILE` 
in any namespace, that contain the label `component=scheduler` (or another label defined by `--label-selector`), 
and returns the namespace, name, and container (`scheduler`)

- `hosts.yaml`
```
kubernetes: 
```

## Example `hosts.yaml` input 
use `-f hosts.yaml`
```
local:

docker:
  - container_id: demo9b25c0_scheduler_1

kubernetes:
  - namespace: astronomer-amateur-cosmos-2865
    name: amateur-cosmos-2865-scheduler-bfcfbd7b5-dvqqr
    container: scheduler

ssh:
  - host: 1.2.3.4
  - host: foo.com
```


# Extra Functionality
## Local
`--local` - checks installed versions of various tools, see [config.yaml](config.yaml) for more details.

## Precheck
`--precheck` - ensures the environment, useful before installing the Astronomer Enterprise chart

## Verify
`--verify` - includes the details of installed helm charts in the cluster (airflow / astronomer)
> Note: Required for some `Airflow Report` reporting functionality
> Note: This mode requires `list node` and `api client get version` permissions in `kubernetes` mode


## Cluster Info
`--cluster-info` gathers information about the provider and size of the kubernetes cluster`
> Note: Required for `Infrastructure Report` reporting functionality

## Report
`--report` generate a report of type `--report-format` from the gathered data
> Note: Required to generate `charts/` and `reports.xlsx` reporting

## Label Selection
`--label-selector` allows Kubernetes Autodiscovery to locate Airflow Deployments with alternate key/values. 
The default is `component=scheduler`, however, if your Airflows contain `role=scheduler` instead, you would 
use `--label-selector "role=scheduler"`.


# DATA SHEET
## Data Collected
The following Data is collected, which is then assembled into the `Outputs` mentioned below

### `report.json`
The name of this file can vary depending on what options were passed to the tool. There is an intermediate output called `report.json` collects all the data gathered, and is utilized to generate the report outputs.

#### Airflow Report
This information is saved under the `airflow` key, under the host_type key and the host key. E.g. `kubernetes.mynamespace|myhost-1234-xyz.airflow_report` or `ssh.my_hostname.airflow_report`

Using `curl`, `airflow_report.py` is piped and executed on the remote host (the host or container running the airflow scheduler). The performance impact of this report is negligible
- `airflow.version.version` output to determine Airflow's version
- `airflow.providers_manager.ProvidersManager`'s output, to determine what providers and versions are installed
- `socket.gethostname()` to determine the hostname
- `pkg_resources` to determine installed python packages and versions
- `airflow.configuration.conf` to determine Airflow configuration settings and what is modified from defaults. Sensitive values are redacted
- `os.environ` to determine what airflow settings, variables, and connections are set via ENV vars. Names only
- the `pools` table is retrieved to list Airflow pools and sizes from the Airflow metadata db
- the `dag` table is inspected from the Airflow metadata db
- the `connection` table is fetched from the Airflow metadata db
- the `task_instance` table is analyzed from the Airflow metadata db


#### Verify
This information is saved under the `helm` key
- `helm ls -aA -o json` and `helm get values` are run. The latter redacts sensitive information.

#### Pre-Check
This special mode runs a pod `bitnami/postgresql` and gets Kubernetes secrets (`astronomer-tls`, `astronomer-bootstrap`) to verify connectivity and information relating to Astronomer Enterprise installations.

### Local Output
See [here](https://github.com/astronomer/telescope/blob/main/telescope/config.yaml) for the most recent description of what is gathered with the local flag. Generally, versions are gathered for the following tools:
- python
- helm
- kubectl
- docker
- astro
- docker-compose
- os
- aws
- gcp
- az

Additionally, 
- `aws_id` checks `aws sts get-caller-identity`

## Pre-requisites
See [Requirements](#requirements) above.

## Usage
### Outputs
The following items are created by Telescope (using default configurations):

#### Charts
Charts are created, by default in a directory called `/charts`. The following charts are created:
- "Airflow Versions"
- "DAGs per Airflow"
- "Tasks per Airflow"
- "Monthly Task Runs per Airflow
- "Operator Set by Airflow"
- "Operator Set by DAG"

#### Spreadsheet
The spreadsheet, titled `report.xlsx` by default, contains the following:

#### Summary Report - an overall summary of the report
- num_airflows: Number of Airflows
- num_dags_active: Number of DAGs active, determined by "is_active" / "is_paused" in the metadata db from the `dag` table
- num_dags_inactive: Number of DAGs inactive, determined by "is_active" / "is_paused" in the metadata db from the `dag` table
- num_tasks: Number of Tasks, from the `task` table
- num_successful_task_runs_monthly: Number of Task Runs, within last 30 days, marked as "successful" 

#### Infrastructure Report - a summary of the infrastructure discovered during the assessment
- type: VM or K8s
- provider: if K8s, attempts to parse `eks`, `az`==`aks`, `gke`, from the Kubernetes Server Version string
- version: Kubernetes Server Version string
- num_nodes: number of nodes in the cluster
- allocatable_cpu: vcpu available to be allocated, as whole vcpus
- capacity_cpu: vcpu total, as whole vcpus
- allocatable_gb: memory available to be allocated
- capacity_gb: memory total
 
#### Airflow Report
- name: - Name of the Airflow, as reported by the Gatherer. For Kubernetes mode this is `<namespace>|<pod name>`
- version: Airflow version
- executor: Airflow executor
- num_schedulers: number of schedulers - needs to be parsed by helm / the `--verify` flag
- num_webservers: number of schedulers - needs to be parsed by helm / the `--verify` flag
- num_workers: number of celery workers, if available - needs to be parsed by helm / the `--verify` flag
- providers: providers and versions installed. Airflow 2.x only. 
- num_providers: number of providers installed. Airflow 2.x only.
- packages: python packages and versions installed 
- non_default_configurations: non-default Airflow configurations and the source of configuration
- parallelism: global parallelism from Airflow configuration
- pools: a list of pools
- default_pool_slots: total slots in the Default pool
- num_pools: number of pools
- env: Environment variables
- connections: Connection names
- num_connections: number of connections
- unique_operators: operators used in this airflow
- task_run_info: task run successes and percentage of failures for the last day, week, month, year, all time.
- task_runs_monthly_success: successful task runs in the last 30 days
- num_dags: number of DAGs
- num_tasks: number of Tasks
- num_dags_active: number of DAGs, active via `is_paused`/`is_active`
- num_dags_inactive: number of DAGs, inactive via `is_paused`/`is_active`

#### DAG Report
- airflow_name: Name of the Airflow, as reported by the Gatherer. For Kubernetes mode this is `<namespace>|<pod name>`
- dag_id: dag_id 
- root_dag_id: root dag_id if it's a subdag
- is_active: whether the scheduler has recently seen it
- is_paused: whether the DAG toggle is on/off
- is_subdag: if it's a subdag
- schedule_interval: the interval defined on the DAG 
- fileloc: the file location of the DAG
- owners: the owners, defined in the DAG
- operators: the Task operators, counted once per DAG
- num_tasks: the overall number of tasks
