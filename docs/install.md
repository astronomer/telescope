
# Installation & Requirements
## Recommended Installation Method 1) via Binary

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

## Recommended Installation Method 2) via PIP
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

## Requirements
### Local - pip installation
- Python >=3.7
- `pip`

### Local - binary installation
- No requirements

### Local - Assessment Mode Requirements
#### Docker Permissions to Exec Containers, `docker.sock` Access locally

#### Kubernetes:
- Permission to List Nodes and Exec in Pods
- `KUBECONFIG` set locally

#### SSH
- Credentials to connect to all hosts
- SSH Access configured locally

#### Local
- Permission to execute Python locally

### Remote Airflow Requirements
- Airflow Scheduler >1.10.5
- Python 3.x
- `Postgresql`/`Mysql`/`Sqlite` Metadata Database (support not guaranteed for other backing databases)
- `github.com` access (unless using )
- `Kubernetes`: Kubernetes Scheduler has label `component=scheduler` (or `--label-selector` specified)


## Alternate Installation Methods
Telescope can also be installed as an Airflow plugin via [Starship](https://github.com/astronomer/starship)

### Install from Source
If neither the [pip installation method](#installation-method-2-via-pip)
nor [binary installation](#installation-method-1-via-binary) methods work - you can download the source
and execute directly as a python module

### As a zip
```shell
wget https://github.com/astronomer/telescope/archive/refs/heads/main.zip && unzip main.zip
cd telescope-main
python -m telescope ...
```

### With git
```shell
git clone https://github.com/astronomer/telescope.git
cd telescope
python -m telescope ...
```
