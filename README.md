# Telescope
![astronomer logo](astro.png)

A tool to observe distant (or local!) Airflow installations, and gather metadata or other required data.

# Installation
```shell
pip install git+https://github.com/astronomer/telescope.git#egg=telescope
```

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
  - 1.2.3.4
  - foo.com
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
`--cluster-info` gathers information about the provider and size of the kubernetes cluster