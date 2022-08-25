  [![Build status](https://github.com/astronomer/telescope/workflows/build/badge.svg?branch=main&event=push)](https://github.com/astronomer/telescope/actions?query=workflow%3Alint-test-build-release)
  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
  [![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/astronomer/telescope/blob/main/.pre-commit-config.yaml)
  [![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/astronomer/telescope/releases)

# Telescope
<p align="center">
  <img src="astro.png" alt="Astronomer Telescope Logo" />
</p>


A tool to observe distant (or local!) Airflow installations, and gather metadata or other required data.

# Installation Method 1) via Binary

Find and download the executable in [the Telescope Release for the correct version](https://github.com/astronomer/telescope/releases/latest)

- **for Linux (x86_64)**
```shell
wget https://github.com/astronomer/telescope/releases/latest/download/telescope-linux-x86_64
chmod +x telescope-linux-x86_64
```

- **for Mac (x86_64, not M1 or ARM)**
```shell
wget https://github.com/astronomer/telescope/releases/latest/download/telescope-darwin-x86_64
chmod +x telescope-darwin-x86_64
```
Note: For Mac, you will get a Security error when you first run Telescope via the CLI binary - you can bypass this in `System Preferences -> Security & Privacy -> General` and hitting `Allow` 

- **for Windows (x86_64)**
```shell
wget https://github.com/astronomer/telescope/releases/latest/download/telescope-mingw64_nt-10.0-20348-x86_64.exe
chmod +x telescope-mingw64_nt-10.0-20348-x86_64.exe
```

# Installation Method 2) via PIP
*Note: PIP installation requires Python >= 3.6*

*optionally*, create a virtualenv called `venv` (or anything else ) in the current directory for easy cleanup
```shell
python -m venv venv
source venv/bin/activate
```

Install Telescope using Pip from Github

```shell
python -m pip install telescope --find-links https://github.com/astronomer/telescope/releases/latest
```

# Quickstart - Kubernetes Autodiscovery Assessment Mode

This will work if your Airflows are in Kubernetes and were deployed with one of the major Helm charts (
and `component=scheduler` is used to identify the schedulers). It will use Helm to interrogate the installation, and
connect to the Airflow schedulers to gather metadata

```shell
telescope --kubernetes --organization-name <My Organization>
```
You should now have a file ending in `*.data.json` - which is an intermediate data payload

# Quickstart - SSH Assessment Mode
This will work if your Airflows are on hosts accessible via SSH and SSH is configured to connect to all of these hosts.
You can pass any configuration option that a [Fabric Connection object](https://docs.fabfile.org/en/stable/api/connection.html#module-fabric.connection) can take
Create a `hosts.yaml` file, like this, enumerating every host:
```shell
ssh:
  - host: airflow.foo1.bar.com
  - host: root@airflow.foo2.bar.com
  - host: airflow.foo3.bar.com
    user: root
    connect_kwargs: {"key_filename":"/full/path/to/id_rsa"}
```

```shell
telescope -f hosts.yaml --organization-name <My Organization>
```
You should now have a file ending in `*.data.json` - which is an intermediate data payload

# Usage
```shell
$ telescope --help
Usage: telescope [OPTIONS]

  Telescope - A tool to observe distant (or local!) Airflow installations, and
  gather usage metadata

Options:
  --version                     Show the version and exit.
  --local                       Airflow Reporting for local Airflow  [default:
                                False]
  --docker                      Autodiscovery and Airflow reporting for local
                                Docker  [default: False]
  --kubernetes                  Autodiscovery and Airflow reporting for
                                Kubernetes  [default: False]
  -l, --label-selector TEXT     Label selector for Kubernetes Autodiscovery
                                [default: component=scheduler]
  --dag-obfuscation             Obfuscate DAG IDs and filenames, keeping first
                                and last 3 chars; my-dag-name => my-*****ame
                                [default: False]
  --dag-obfuscation-fn TEXT     Obfuscate DAG IDs, defining a custom function
                                that takes a string and returns a string;
                                'lambda x: x[-5:]' would return only the last
                                five letters of the DAG ID and fileloc
  -f, --hosts-file PATH         Hosts file to pass in various types of hosts
                                (ssh, kubernetes, docker) - See README.md for
                                sample
  -p, --parallelism INTEGER     How many cores to use for multiprocessing
                                [default: (Number CPU)]
  -n, --organization-name TEXT  Denote who this report belongs to, e.g. a
                                company name
  -o, --data-file PATH          Data file to write intermediate gathered data,
                                can be '-' for stdout
  --help                        Show this message and exit.
```

# Requirements
## Locally - via PIP
- Python >=3.6
- `pip`

## Locally - Docker or Kubernetes or SSH Airflow Assessment modes
- **Docker**: Permissions to Exec Containers, `docker.sock` Access locally
- **Kubernetes**: Permission to List Nodes and Exec in Pods, `KUBECONFIG` set locally
- **SSH**: Credentials to connect to all hosts, SSH Access configured locally
- **Local**: Permission to execute Python locally

## Remote Airflow Requirements
- Airflow Scheduler >1.10.5
- Python 3.x
- Postgresql/Mysql/Sqlite Metadata Database (support not guaranteed for other backing databases)
- **Kubernetes**: Kubernetes Scheduler has label `component=scheduler` (or `--label-selector` specified)
- `github.com` access

# Input
## Local autodiscovery
Either use `--local` or have an empty `local` key in your hosts file to enable autodiscovery.
Autodiscovery simply runs the Airflow Report as a process, assuming that an Airflow Scheduler is being run
on the current node.

## Docker autodiscovery
Either use `--docker` or have an empty `docker` key in your hosts file to enable autodiscovery.
Autodiscovery searches for containers running locally that contain "scheduler" in the name and returns
the container_id

- `hosts.yaml`
```
docker:
```

## Kubernetes autodiscovery
Either use `--kubernetes` or an empty `kubernetes` in your hosts file to enable autodiscovery.
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
  - host: airflow.foo1.bar.com
  - host: root@airflow.foo2.bar.com
  - host: airflow.foo3.bar.com
    user: root
    connect_kwargs: {"key_filename":"/full/path/to/id_rsa"}
```

# Extra Functionality
## Label Selection
`--label-selector` allows Kubernetes Autodiscovery to locate Airflow Deployments with alternate key/values.
The default is `component=scheduler`, however, if your Airflows contain `role=scheduler` instead, you would
use `--label-selector "role=scheduler"`.

## Airflow Report Command
`TELESCOPE_AIRFLOW_REPORT_CMD` can be set, normally the default is
```shell
python -W ignore -c "import runpy,os;from urllib.request import urlretrieve as u;a='airflow_report.pyz';u('https://github.com/astronomer/telescope/releases/latest/download/'+a,a);runpy.run_path(a);os.remove(a)"
```

This can be used, for instance, if there is no access to Github on the remote box, or a custom directory is needed to run,
or environment activation is required ahead of time.

If your `python` is called something other than `python` (e.g. `python3`):
```shell
TELESCOPE_AIRFLOW_REPORT_CMD=$(cat <<'EOF'
python3 -W ignore -c "import runpy,os;from urllib.request import urlretrieve as u;a='airflow_report.pyz';u('https://github.com/astronomer/telescope/releases/latest/download/airflow_report.pyz',a);runpy.run_path(a);os.remove(a)"
EOF
) telescope -f hosts.yaml 
```

or if you need to activate a `python` (such as with RedHat Linux) prior to running, and want to copy the telescope Manifest up to the host independently:
```shell
scp airflow_report.pyz remote_user@remote_host:airflow_report.pyz
TELESCOPE_AIRFLOW_REPORT_CMD="scl enable rh-python36 python -W ignore -c 'import runpy;a=\'airflow_report.pyz\';runpy.run_path(a);os.remove(a)'" telescope -f hosts.yaml
```

## DAG Obfuscation
`DAG ID` and `fileloc` can be obfuscated with the `--dag-obfuscation` command.
The default obfuscation keeps the first 3 and last 3 characters and adds a fixed width of `******`. e.g.
```text
my-dag-name => my-*****ame
```

### Custom Obfuscation Function
If a different obfuscation function is desired, a `--dag-obfuscation-function` can be passed,
which needs to be a python function that evaluates to `(str) -> str`. E.g.
```shell
--dag-obfuscation-fn="lambda x: x[-5:]"
```
would return only the last five letters of `dag_id` and `fileloc`. E.g.
```
dag_id="hello_world" -> "world"
fileloc="/a/b/c/d/filepath.py" -> "th.py"
```

## Optional Environmental Variables
- `TELESCOPE_KUBERNETES_METHOD=kubectl` - to run with kubectl instead of the python SDK (often for compatibility reasons)
- `TELESCOPE_REPORT_RELEASE_VERSION=x.y.z` - can be a separate telescope semver release number, to control which report gets run
- `TELESCOPE_KUBERNETES_AIRGAPPED=true` - executes the airflow report in airgapped mode (i.e copies report binary from local to pod)
- `LOG_LEVEL=DEBUG` - can be any support Python logging level `[CRITICAL, FATAL, ERROR, WARN, WARNING, INFO, DEBUG, NOTSET]`
- `TELESCOPE_SHOULD_VERIFY=false` - turn off helm chart collection - required to gather some data about Airflow in Kubernetes

# Install as an Airflow Plugin
Telescope can also be installed as an Airflow plugin. 
This is helpful in instances where shell access is unable to be acquired - such as with Google Cloud Composer (GCC) or AWS' Managed Apache Airflow (MWAA).

To install Telescope this way upload the [Aeroscope plugin](plugins/aeroscope.py) based on your normal method of installing plugins. 
- Google Cloud Composer - https://cloud.google.com/composer/docs/concepts/plugins
- AWS Managed Apache Airflow - https://docs.aws.amazon.com/mwaa/latest/userguide/configuring-dag-import-plugins.html



# Install from Source
If neither the [pip installation method](#installation-method-2-via-pip)
or [binary installation](#installation-method-1-via-binary)
methods work - you can download the source and execute directly as a python module

## As a zip
```shell
wget https://github.com/astronomer/telescope/archive/refs/heads/main.zip && unzip main.zip
cd telescope-main
python -m telescope ...
```

## With git
```shell
git clone https://github.com/astronomer/telescope.git
cd telescope
python -m telescope ...
```

# Data Collected
The following Data is collected:

## `cluster_info`
When run using `kubernetes`, cluster info is attained from the Nodes - including allocated and max CPU and Memory, number of nodes, and kubelet version

## `verify`
When run using `kubernetes`, Helm chart information for charts named like `astronomer` or `airflow` is fetched, sensitive values are redacted.

## `Airflow Report`
This information is saved under the `airflow_report` key, under the `host_type` key and the host key. E.g. `kubernetes.mynamespace|myhost-1234-xyz.airflow_report` or `ssh.my_hostname.airflow_report`

Using python `airflow_report.pyz` is downloaded and executed on the remote host (the host or container running the airflow scheduler). The performance impact of this report is negligible
- `airflow.version.version` output to determine Airflow's version
- `airflow.providers_manager.ProvidersManager`'s output, to determine what providers and versions are installed
- `socket.gethostname()` to determine the hostname
- `pkg_resources` to determine installed python packages and versions
- `airflow.configuration.conf` to determine Airflow configuration settings and what is modified from defaults. Sensitive values are redacted
- `os.environ` to determine what airflow settings, variables, and connections are set via ENV vars. Names only
- the `pools` table is retrieved to list Airflow pools and sizes from the Airflow metadata db
- the `dag` table is inspected from the Airflow metadata db
  - `dags` are read off disk to attain variable and connection names, utilizing the filepath from the `dags` table
- the `connection` table is fetched from the Airflow metadata db
- the `variable` table is fetched from the Airflow metadata db
- the `ab_user` table is fetched from the Airflow metadata db
- the `task_instance` table is analyzed from the Airflow metadata db

# Output
## `*.data.json`
The name of this file can vary depending on what options were passed to the tool.
There is an intermediate output ending in `*.data.json` which contains all data gathered, and is utilized to generate the report outputs.

# Compatibility Matrix
Telescope is been tested against the following Airflow versions:
```shell
"apache/airflow:2.3.4"
"apache/airflow:2.2.4"
"apache/airflow:2.1.3"
"apache/airflow:1.10.15"
"apache/airflow:1.10.10"
"bitnami/airflow:1.10.2"
```

Telescope is tested with the following Metadata Database Backends:
- (automated) PostgreSQL, SQLite
- (manually) MySQL, SQLServer

Telescope is tested on the following versions of Python:
```
"3.5", "3.9", "3.10"
```

Telescope is tested on the following Operating Systems:
- Ubuntu
- Mac (arm64, amd64)
- Windows
