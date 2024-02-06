<!--suppress HtmlDeprecatedAttribute -->
<p align="center">
  <img
    width="200px" height="200px"
    src="https://raw.githubusercontent.com/astronomer/telescope/main/telescope.svg"
    alt="Astronomer Telescope Logo"
  />
</p>
<p align="center">
  <b>Astronomer Telescope</b> is a tool to observe distant (or local!) Airflow installations,
  and help you better understand your deployments.
</p>

## What is it?
It is a CLI that runs on your workstation and accesses remote Airflows to collect a common set of data.

Optionally, it can be installed and run as an Airflow plugin via [Starship](https://github.com/astronomer/starship).

Telescope has been purpose-built to help administrators understand their Airflow installations
and provide metadata to assist with migrations.

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


## Quickstart
### Install
Install from [pip](install/#recommended-installation-method-1-via-binary)
```shell
python -m pip install astronomer-telescope
```
or download a [binary](install/#recommended-installation-method-1-via-binary).

### Usage
For more information, see [requirements](install/#requirements) or [usage](CLI)

#### Kubernetes Autodiscovery Assessment Mode

This will work if the Airflow instances are in Kubernetes and were deployed with one of the major Helm charts (
`component=scheduler` is used to identify the schedulers).

It will use Helm to analyze the installation, and connect to the Airflow schedulers to gather metadata.

```shell
telescope --kubernetes --organization-name <My Organization>
```
This will produce a file ending in `*.data.json` - which is an data payload that can be sent to Astronomer for
further processing and detailed analysis.

#### SSH Assessment Mode
This will work if the Airflow instances are on hosts accessible via SSH
and SSH is configured to connect to all of these hosts.


You can pass any configuration option that a
[Fabric Connection object](https://docs.fabfile.org/en/stable/api/connection.html#module-fabric.connection) can take.


Create a file enumerating every host, such as:
```shell title="hosts.yaml"
ssh:
  - host: airflow.foo1.bar.com
  - host: root@airflow.foo2.bar.com
  - host: airflow.foo3.bar.com
    user: root
    connect_kwargs: {"key_filename":"/full/path/to/id_rsa"}
```
and run with:
```shell
telescope -f hosts.yaml --organization-name <My Organization>
```
This will produce a file ending in `*.data.json` - which is an data payload that can be sent to Astronomer for
further processing and detailed analysis.

## Security Notice
This project, by default, executes a python script downloaded from the internet on each Airflow it connects to.
This is by design. Please fully understand this and take any steps required to protect your environment
before running Telescope.
Telescope `eval`'s any custom DAG obfuscation function passed to it.

---

**Artwork**
Orbiter logo [by b farias](https://thenounproject.com/bfarias/) used with permission
from [The Noun Project](https://thenounproject.com/icon/telescope-1187570/)
under [Creative Commons](https://creativecommons.org/licenses/by/3.0/us/legalcode).
