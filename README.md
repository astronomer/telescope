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

# What is it?
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

[Read more at the official documentation!](https://astronomer.github.io/telescope)

---

**Artwork**
Orbiter logo [by b farias](https://thenounproject.com/bfarias/) used with permission
from [The Noun Project](https://thenounproject.com/icon/telescope-1187570/)
under [Creative Commons](https://creativecommons.org/licenses/by/3.0/us/legalcode).
