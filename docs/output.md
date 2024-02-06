# Data Collected & Output
## Data Collected
The following Data is collected:

When run using `kubernetes`

- cluster info is attained from the Nodes - including allocated and max CPU and Memory, number of nodes, and kubelet version
- Helm chart information for charts named like `astronomer` or `airflow` is fetched, sensitive values are redacted.

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


There is an intermediate output ending in `*.data.json` which contains all data gathered, and is utilized to generate the report outputs.
The name of this file can vary depending on what options were passed to the tool.

**Output file includes the following sections:**

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

### Airflow Version Report

Airflow Deployment version

Example: `2.5.0+astro.1`

### Configuration Report

Airflow runtime configuration (airflow.cfg)

[See documentation here](https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html)
[See here for default airflow.cfg](https://github.com/apache/airflow/blob/main/airflow/config_templates/default_airflow.cfg)

| Config Section | Config Setting            | Example Value                                                    |
|----------------|---------------------------|------------------------------------------------------------------|
| core           | dags_folder               | `/usr/local/airflow/dags`                                        |
| logging        | base_log_folder           | `/usr/local/airflow/logs`                                        |
| metrics        | statsd_on                 | `True`                                                           |
| secrets        | backend                   | `***`                                                            |
| cli            | endpoint_url              | `http://localhost:8080`                                          |
| debug          | fail_fast                 | `False`                                                          |
| api            | auth_backend              | `astronomer.flask_appbuilder.current_user_backend`               |
| lineage        | backend                   | ` `                                                              |
| operators      | default_owner             | `airflow`                                                        |
| webserver      | base_url                  | `https://deployments.astro.subdomain.domain.com/cluster/airflow` |
| email          | email_backend             | `airflow.utils.email.send_email_smtp`                            |
| smtp           | smtp_mail_from            | `noreply@domain.com`                                             |
| celery         | celery_app_name           | `airflow.executors.celery_executor`                              |
| scheduler      | min_file_process_interval | `90`                                                             |
| ...            | ...                       | ...                                                              |

Note: Only one entry per config section is shown to reduce the length of the above table.

### Connections Report

List of all Airflow connections (IDs only)

Example:

| Connection ID      |
|--------------------|
| `airflow_db`       |
| `aws_default`      |
| `postgres_default` |
| ...                |

### DAGs Report

List of DAGs, including code quality metrics

| Field Name                 | Description                                                                                         | Example Value                            |
|----------------------------|-----------------------------------------------------------------------------------------------------|------------------------------------------|
| dag_id                     | The id of the DAG                                                                                   | `my_dag_id`                              |
| schedule_interval          | The schedule dictating when the DAG runs are scheduled                                              | `0 1 * * *`                              |
| root_dag_id                | The Parent DAG ID if dag is a SubDAG                                                                | `null`                                   |
| is_paused                  | If the DAG was paused (Boolean)                                                                     | `false`                                  |
| is_active                  | If the DAG file is present in the DAGS_FOLDER                                                       | `true`                                   |
| is_subdag                  | If the DAG is defined within another DAG                                                            | `false`                                  |
| fileloc                    | Local Path to the DAG file                                                                          | `/usr/local/airflow/dags/my_dag_file.py` |
| owners                     | Name of the DAG owner                                                                               | `airflow`                                |
| operators                  | Comma-separated list of Operators used in DAG                                                       | `ÈmptyOperator,PythonOperator`           |
| num_tasks                  | Number of tasks in the DAG                                                                          | `4`                                      |
| variables                  | Comma-separated list of variables referenced in the DAG                                             | `AIRFLOW_VAR_FOO_BAR`                    |
| connections                | Comma-separated list of connections referenced in the DAG                                           | `AIRFLOW_CONN_AIRFLOW_DB`                |
| cc_rank                    | Cyclomatic Complexity rating                                                                        | `"A"`                                    |
| mi_rank                    | Maintainability Index score                                                                         | `"A"`                                    |
| analysis                   | Subsection for Code Metrics Results from [Radon](https://radon.readthedocs.io/en/latest/intro.html) |                                          |
| analysis > loc             | Total number of lines of code                                                                       | `55`                                     |
| analysis > lloc            | Number of logical lines of code                                                                     | `15`                                     |
| analysis > sloc            | Number of source lines of code                                                                      | `35`                                     |
| analysis > comments        | Number of Python comment lines                                                                      | `3`                                      |
| analysis > multi           | Number of lines representing multi-line strings                                                     | `12`                                     |
| analysis > blank           | Number of blank lines                                                                               | `15`                                     |
| analysis > single_comments | Number of blank lines (or whitespace-only ones)                                                     | `3`                                      |

### Environment Variables Report

List of airflow-related environment variables

Example values:
Note: Only the keys are fetched by Telescope for obvious security reasons.

Example:

| section        | Config                          |
|----------------|---------------------------------|
| config_options | AIRFLOW__CORE__SQL_ALCHEMY_CONN |
| connections    | AIRFLOW_CONN_AIRFLOW_DB         |
| variables      | AIRFLOW_VAR_FOO_BAR             |

### Hostname Report

Airflow Hostname configuration

Example: `astral-satellite-1234-scheduler-01abc23de-fghij`

### Installed Packages Report

List of all installed packages

Example:

| Package                                  | Version       |
|------------------------------------------|---------------|
| ...                                      | ...           |
| apache-airflow                           | 2.5.0+astro.1 |
| apache-airflow-providers-amazon          | 6.2.0         |
| apache-airflow-providers-apache-hive     | 5.0.0         |
| apache-airflow-providers-apache-livy     | 3.2.0         |
| apache-airflow-providers-celery          | 3.1.0         |
| apache-airflow-providers-cncf-kubernetes | 5.0.0         |
| apache-airflow-providers-common-sql      | 1.3.1         |
| apache-airflow-providers-databricks      | 4.0.0         |
| apache-airflow-providers-dbt-cloud       | 2.3.0         |
| apache-airflow-providers-elasticsearch   | 4.3.1         |
| apache-airflow-providers-ftp             | 3.2.0         |
| apache-airflow-providers-google          | 8.6.0         |
| apache-airflow-providers-http            | 4.1.0         |
| apache-airflow-providers-imap            | 3.1.0         |
| apache-airflow-providers-microsoft-azure | 5.0.1         |
| apache-airflow-providers-postgres        | 5.3.1         |
| apache-airflow-providers-redis           | 3.1.0         |
| apache-airflow-providers-sftp            | 4.2.0         |
| apache-airflow-providers-snowflake       | 4.0.2         |
| apache-airflow-providers-sqlite          | 3.3.1         |
| apache-airflow-providers-ssh             | 3.3.0         |
| ...                                      | ...           |

### Pools Report

List of Airflow pools and associated configuration

Example:

| Pool         | Config  | Value |
|--------------|---------|-------|
| default_pool | total   | 100   |
| default_pool | running | 0     |
| default_pool | queued  | 0     |
| default_pool | open    | 100   |

### Providers Report

List of all installed providers

Example:

| Package                                    | Version  |
|:-------------------------------------------|----------|
| `apache-airflow-providers-amazon`          | `7.1.0`  |
| `apache-airflow-providers-google`          | `8.8.0`  |
| `apache-airflow-providers-microsoft-azure` | `5.0.2`  |
| `apache-airflow-providers-postgres`        | `5.4.0`  |
| `apache-airflow-providers-slack`           | `7.2.0`  |

### Usage Statistics Report

Execution statistics (success & failure task counts) over the last 1, 7, 30, 365 days, and all time.

| Field Name       | Description                                          | Example Value     |
|------------------|------------------------------------------------------|-------------------|
| dag_id           | The id of the DAG                                    | example_dag_basic |
| 1_days_success   | Number of successful task runs in the last day.      | 4                 |
| 1_days_failed    | Number of failed task runs in the last  day.         | 0                 |
| 7_days_success   | Number of successful task runs in the last 7 days.   | 27                |
| 7_days_failed    | Number of failed task runs in the last 7 days.       | 1                 |
| 30_days_success  | Number of successful task runs in the last 30 days.  | 108               |
| 30_days_failed   | Number of failed task runs in the last 30 days.      | 12                |
| 365_days_success | Number of successful task runs in the last 365 days. | 1430              |
| 365_days_failed  | Number of failed task runs in the last 365 days.     | 30                |
| all_days_success | Number of all time successful task runs.             | 1672              |
| all_days_failed  | Number of all time failed task runs.                 | 48                |

### Usage Statistics DAG Rollup Report

Execution statistics (success & failure dag run counts) over the last 1, 7, 30, 365 days, and all time.

| Field Name       | Description                                         | Example Value     |
|------------------|-----------------------------------------------------|-------------------|
| dag_id           | The id of the dag                                   | example_dag_basic |
| 1_days_success   | Number of successful dag runs in the last day.      | 2                 |
| 1_days_failed    | Number of failed dag runs in the last  day.         | 0                 |
| 7_days_success   | Number of successful dag runs in the last 7 days.   | 13                |
| 7_days_failed    | Number of failed dag runs in the last 7 days.       | 1                 |
| 30_days_success  | Number of successful dag runs in the last 30 days.  | 33                |
| 30_days_failed   | Number of failed dag runs in the last 30 days.      | 6                 |
| 365_days_success | Number of successful dag runs in the last 365 days. | 250               |
| 365_days_failed  | Number of failed dag runs in the last 365 days.     | 20                |
| all_days_success | Number of all time successful dag runs.             | 300               |
| all_days_failed  | Number of all time failed dag runs.                 | 24                |

### Users Report

Number of active users over the last 1, 7, 30, and 365 days

| Column                | Description                                 | Example Value |
|-----------------------|---------------------------------------------|---------------|
| 1_days_active_users   | Number of active users in the last day      | 2             |
| 7_days_active_users   | Number of active users in the last 7 days   | 4             |
| 30_days_active_users  | Number of active users in the last 30 days  | 8             |
| 365_days_active_users | Number of active users in the last 365 days | 9             |
| total_users           | Total number of users                       | 12            |

### Variables Report

List of all Airflow variables (keys only)

Example:

| Variable       |
|----------------|
| s3_bucket      |
| my_first_var   |
| my_second_var  |
| ...            |
