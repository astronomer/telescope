# Astronomer Aeroscope Provider

The Astronomer Aeroscope Provider contains a Plugin and Operator from Astronomer. 
These provide a method to run Telescope in environments where other methods are unavailable 

## Installation
Add the following line to your `requirements.txt` in your source environment:
```text
astronomer-aeroscope
```

## Usage Option 1) Plugin Usage
- Navigate to the top navigation bar in your Source Airflow environment.
- Click the `Astronomer` menu, then `Run Report`

## Usage Option 2) Operator Usage
- Add the following DAG to your source Airflow environment
```python
from datetime import datetime

from airflow.models import DAG
from astronomer.aeroscope.operators import AeroscopeOperator

with DAG(
  dag_id="astronomer_aeroscope",
  schedule_interval=None,
  start_date=datetime(2021, 1, 1),
) as dag:
  AeroscopeOperator(
      task_id="run_report",
      presigned_url='{{ dag_run.conf["presigned_url"] }}',
      organization='{{ dag_run.conf["organization"] }}',
  )
```
- Trigger the `astronomer_aeroscope` DAG with the configuration given by your Astronomer Representative
   

     
