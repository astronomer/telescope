# Astronomer Migration Provider

Apache Airflow Provider containing Operators from Astronomer. The purpose of these operators is to better assist customers migrating to Astronomer hosted Airflow environments from MWAA, GCC, OSS. These providers also provide a convient method to Run Telescoper, as Astronomer developed Airflow scoping tool. This provider is meant for MWAA 2.0.2 and Composer 1 since the plugin and CLI methods are unavailable.

## Installation
Install and update using [pip](https://pip.pypa.io/en/stable/getting-started/):
```text
pip install https://astro-migration-provider.s3.us-west-2.amazonaws.com/astronomer-migration-provider-0.1.1.tar.gz
```

## Usage
1. Add the following line to your `requirements.txt` in your source environment:
   ```text
    https://astro-migration-provider.s3.us-west-2.amazonaws.com/astronomer-migration-provider-0.1.1.tar.gz
    ```
   1. Add the following DAG to your source environment:
       ```python
          from datetime import datetime
          from operators.aeroscope import AeroscopeOperator
          from airflow.decorators import dag
  
  
          @dag(
               schedule_interval=None,
               start_date=datetime(2021, 1, 1),
               catchup=False,
               default_args={"retries": 0},
               tags=["telescope"],
                   )
          def aeroscope():
               execute = AeroscopeOperator(
                    task_id="execute",
                    presigned_url='{{ dag_run.conf["presigned_url"] }}',
                    email='{{ dag_run.conf["email"] }}',
                           )
    
    
          aeroscope = aeroscope()
      ```
   2. Ask your Astronomer Representive for a presigned url
   3. Trigger the `aeroscope` DAG w/ the following config:
   ```json
   {"presigned_url":"<astoronomer-provided-url>",
   "email": "<your_company_email>"}
   ``` 
   

     
