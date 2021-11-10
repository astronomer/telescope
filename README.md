# Telescope

<div align="center">

[![Build status](https://github.com/telescope/telescope/workflows/build/badge.svg?branch=master&event=push)](https://github.com/telescope/telescope/actions?query=workflow%3Abuild)
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/telescope/telescope/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/telescope/telescope/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/telescope/telescope/releases)

A tool to observe distant (or local!) Airflow installations, and gather metadata or other required data.

</div>

# Telescope
![astronomer logo](astro.png)

A tool to observe distant (or local!) Airflow installations, and gather metadata or other required data.

# Installation
```shell
pip install git+https://github.com/astronomer/telescope.git#egg=telescope
```

# Usage
```shell
$ telescope --help                                                
Usage: telescope [OPTIONS]

  Telescope - A tool to observe distant (or local!) Airflow installations, and
  gather metadata or other required data,

Options:
  --local                    checks versions of locally installed tools
                             [default: False]
  --docker                   autodiscovery and airflow reporting for local
                             docker  [default: False]
  --kubernetes               autodiscovery and airflow reporting for
                             kubernetes  [default: False]
  --cluster-info             get cluster size and allocation in kubernetes
                             [default: False]
  --verify                   adds helm installations to report  [default:
                             False]
  -f, --hosts-file PATH      Hosts file to pass in various types of hosts
                             (ssh, kubernetes, docker) - See README.md for
                             sample
  -o, --output-file PATH     Output file to write report json, can be '-' for
                             stdout  [default: report.json]
  -p, --parallelism INTEGER  How many cores to use for multiprocessing
                             [default: (Number CPU)]
  --help                     Show this message and exit.
```

# Requirements
## Locally - Python
- Python 3.x
- PIP
- KUBECONFIG _or_ SSH Access _or_ `docker.sock` Access

## Locally - Docker
- Docker (permissions to run pods)
- KUBECONFIG _or_ SSH Access _or_ `docker.sock` Access

## Remote:
- Airflow 2.x Scheduler
- label `component=scheduler` (docker / kubernetes)
- Python 3.x
- Curl

# Input
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

## Docker autodiscovery
Either use `--docker` or an empty `docker` in your hosts file to enable autodiscovery.
Autodiscovery searches for containers running locally that contain "scheduler" in the name and returns
the container_id

- `hosts.yaml`
```
docker: 
```

## Kubernetes autodiscovery
Either use `--kubernetes` or an empty `kubernets` in your hosts file to enable autodiscovery.
Autodiscovery searches for pods running in the Kubernetes cluster defined by `KUBEPROFILE` 
in any namespace, that contain the label `component=scheduler`, and returns the namespace, name, and container (`scheduler`)

- `hosts.yaml`
```
kubernetes: 
```

# Extra Functionality
## Local
`--local` - checks installed versions of various tools, see [config.yaml](config.yaml) for more details.

## Precheck
`--precheck` - ensures the environment, useful before installing the Astronomer Enterprise chart

## Verify
`--verify` - includes the details of installed helm charts in the cluster (airflow / astronomer)

## Cluster Info
`--cluster-info` gathers information about the provider and size of the kubernetes cluster`