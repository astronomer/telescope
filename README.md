# Telescope
<!--suppress HtmlDeprecatedAttribute -->
<p align="center">
  <img src="https://raw.githubusercontent.com/astronomer/telescope/main/telescope.svg" alt="Astronomer Telescope Logo" />
</p>

<!-- TOC -->
* [Telescope](#telescope)
* [What is it?](#what-is-it)
* [Installation Method 1) via Binary](#installation-method-1-via-binary)
* [Installation Method 2) via PIP](#installation-method-2-via-pip)
* [Quickstart - Kubernetes Autodiscovery Assessment Mode](#quickstart---kubernetes-autodiscovery-assessment-mode)
* [Quickstart - SSH Assessment Mode](#quickstart---ssh-assessment-mode)
* [Presigned URL Upload](#presigned-url-upload)
* [Data Collected](#data-collected)
  * [`cluster_info`](#cluster_info)
  * [`verify`](#verify)
  * [`Airflow Report`](#airflow-report)
* [Usage](#usage)
* [Requirements](#requirements)
  * [Locally - via PIP](#locally---via-pip)
  * [Locally - Docker or Kubernetes or SSH Airflow Assessment modes](#locally---docker-or-kubernetes-or-ssh-airflow-assessment-modes)
  * [Remote Airflow Requirements](#remote-airflow-requirements)
* [Input](#input)
  * [Local autodiscovery](#local-autodiscovery)
  * [Docker autodiscovery](#docker-autodiscovery)
  * [Kubernetes autodiscovery](#kubernetes-autodiscovery)
  * [Example `hosts.yaml` input](#example-hostsyaml-input)
* [Output](#output)
  * [`*.data.json`](#datajson)
    * [Output file includes the following sections:](#output-file-includes-the-following-sections)
    * [Column Description and Examples](#column-description-and-examples)
* [Extra Functionality](#extra-functionality)
  * [Label Selection](#label-selection)
  * [Airflow Report Command](#airflow-report-command)
  * [DAG Obfuscation](#dag-obfuscation)
    * [Custom Obfuscation Function](#custom-obfuscation-function)
  * [Optional Environmental Variables](#optional-environmental-variables)
* [Alternative Methods](#alternative-methods-)
* [Install from Source](#install-from-source)
  * [As a zip](#as-a-zip)
  * [With git](#with-git)
* [Compatibility Matrix](#compatibility-matrix)
* [Security Notice](#security-notice)
<!-- TOC -->

# What is it?

Telescope is a tool to observe distant (or local!) Airflow installations, and gather metadata or other required data.

It is a CLI that runs on your workstation and accesses remote Airflows to collect a common set of data.

Optionally, it can be installed and run as an Airflow plugin.

Telescope has been purpose-built to help administrators understand their Airflow installations and provide metadata to assist with migrations.

**Main features**
- Analyze your Airflow deployment and execution environment to provide a snapshot of all configurations.
- Summarizes Airflow-specific settings (variables, connections, pools, etc.)
- Generates a report of runtime configurations (airflow.cfg)
- Generates a DAGs report including code quality metrics, execution statistics and more.
- Can be run on most deployment environments (Docker, Kubernetes, SSH Remote) and Airflow versions.
- Security and anonymity are built-in.
  - Kubernetes and airflow.cfg sensitive values are redacted.
  - Individual user information and secrets are never accessed.
  - Reports can be parameterized to obfuscate DAG IDs and filenames.

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
*Note: PIP installation requires Python >= 3.7*

*optionally*, create a virtualenv called `venv` (or anything else ) in the current directory for easy cleanup
```shell
python -m venv venv
source venv/bin/activate
```

Install Telescope using Pip from Github

```shell
python -m pip install astronomer-telescope
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

# Presigned URL Upload
For both the Telescope CLI and Aeroscope Airflow Plugin, you have the option to upload the data payload via a presigned upload url. Please contact an Astronomer Representative to acquire a presigned url.

You can utilize this in the Telescope CLI as follows
```shell
telescope --kubernetes --organization-name <My Organization> --presigned-url https://storage.googleapis.com/astronomer-telescope............c32f043eae2974d847541bbaa1618825a80ed80f58f0ba3
```
Make sure to change `--kubernetes` to the correct method of operation to access your Airflow, and the contents of `--presigned-url` to the actual URL supplied to you.

*Note:* Presigned URLs generally only last for up to a day, make sure to use yours soon after receiving it or request another when you are able.

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
  -u, --presigned-url TEXT      URL to write data directly to - given by an
                                Astronomer Representative
  --help                        Show this message and exit.
```

# Requirements
## Locally - via PIP
- Python >=3.7
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

# Output
## `*.data.json`
The name of this file can vary depending on what options were passed to the tool.
There is an intermediate output ending in `*.data.json` which contains all data gathered, and is utilized to generate the report outputs.

### Output file includes the following sections:

| Report                        | Description                                                                                            |
|-------------------------------|--------------------------------------------------------------------------------------------------------|
| airflow version report        | Airflow Deployment version                                                                             |
| configuration report          | Airflow runtime configuration (airflow.cfg)                                                            |
| connections report            | List of all Airflow connections (IDs only)                                                             |
| dags report                   | Lisst of DAGs, including code quality metrics                                                          |
| env vars report               | List of airflow-related environment variables                                                          |
| hostname report               | Airflow Hostname configuration                                                                         |
| installed packages report     | List of all installed packages                                                                         |
| pools report                  | List of Airflow pools and associated configuration                                                     |
| providers report              | List of all installed providers                                                                        |
| usage stats report            | Execution statistics (success & failure task counts) over the last 1, 7, 30, 365 days and all time.    |
| usage stats dag rollup report | Execution statistics (success & failure dag run counts) over the last 1, 7, 30, 365 days and all time. |
| user report                   | Number of active users over the last 1, 7, 30 and 365 days                                             |
| variables report              | List of all Airflow variables (keys only)                                                              |

### Column Description and Examples
[Click on this link](./docs/output.md) for detailed column-by-column report outputs. Column descriptions and examples are provided.

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
- `TELESCOPE_REPORT_PACKAGE_URL` - sets the URL that both the local CLI AND `TELESCOPE_AIRFLOW_REMOTE_CMD` will use (unless `TELESCOPE_AIRFLOW_REMOTE_CMD` is set directly)

# Alternative Methods
Telescope can also be installed as an Airflow plugin and has an `AeroscopeOperator`
This is helpful in instances where shell access is unable to be acquired - such as with Google Cloud Composer (GCC) or AWS' Managed Apache Airflow (MWAA).

To install Telescope this way, please review instructions [here](./aeroscope/README.md).


# Install from Source
If neither the [pip installation method](#installation-method-2-via-pip)
nor [binary installation](#installation-method-1-via-binary) methods work - you can download the source
and execute directly as a python module

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

# Compatibility Matrix
Telescope is being tested against the following Airflow versions:
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

# Security Notice
This project, by default, executes a python script downloaded from the internet on each Airflow it connects to.
This is by design. Please fully understand this and take any steps required to protect your environment
before running Telescope.

---

**Artwork**
Orbiter logo [by b farias](https://thenounproject.com/bfarias/) used with permission
from [The Noun Project](https://thenounproject.com/icon/telescope-1187570/)
under [Creative Commons](https://creativecommons.org/licenses/by/3.0/us/legalcode).
