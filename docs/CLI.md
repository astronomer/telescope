::: mkdocs-click
    :module: astronomer_telescope.__main__
    :command: telescope


## Presigned URL Upload
You have the option to upload the data payload via a presigned upload url.
Please contact an Astronomer Representative to acquire a presigned url.

You can utilize this in the Telescope CLI as follows
```shell
telescope --kubernetes --organization-name <My Organization> --presigned-url https://storage.googleapis.com/astronomer-telescope............c32f043eae2974d847541bbaa1618825a80ed80f58f0ba3
```
Make sure to change `--kubernetes` to the correct method of operation to access your Airflow,
and the contents of `--presigned-url` to the actual URL supplied to you.

*Note:* Presigned URLs generally only last for up to a day,
make sure to use yours soon after receiving it or request another when you are able.

## Configuration
### Local autodiscovery
Either use `--local` or have an empty `local` key in your hosts file to enable autodiscovery.
Autodiscovery simply runs the Airflow Report as a process, assuming that an Airflow Scheduler is being run
on the current node.

### Docker autodiscovery
Either use `--docker` or have an empty `docker` key in your hosts file to enable autodiscovery.
Autodiscovery searches for containers running locally that contain "scheduler" in the name and returns
the container_id

- `hosts.yaml`
```
docker:
```

### Kubernetes autodiscovery
Either use `--kubernetes` or an empty `kubernetes` in your hosts file to enable autodiscovery.
Autodiscovery searches for pods running in the Kubernetes cluster defined by `KUBEPROFILE`
in any namespace, that contain the label `component=scheduler` (or another label defined by `--label-selector`),
and returns the namespace, name, and container (`scheduler`)

- `hosts.yaml`
```
kubernetes:
```

### Example `hosts.yaml` input
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

## Compatibility Matrix
Telescope is tested with

**Airflow versions**
```text
--8<- "tests/airflow_report/airflow_report_test.py:airflow-images"
```

**Metadata Database Backends**

- PostgreSQL
- SQLite
- MySQL (manual, infrequent testing)
- SQLServer (manual, infrequent testing)

**Python Versions**
```text
--8<- ".github/workflows/checks.yml:python-versions"
```

**Operating Systems**
```text
--8<- ".github/workflows/deploy.yml:oses"
```
