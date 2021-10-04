
# Example `hosts.yaml`
```
ssh:
  hosts:
    - bla.com
    - 1.2.3.4:22

docker:
  containers:
    - demo9b25c0_scheduler_1

kubernetes:
  contexts:
    - fritz@polaris.us-east-1.eksctl.io
```

# Example Kubernetes Command
```python
cmd = [
  '/bin/sh',
  '-c',
  'echo This message goes to stdout; ls / -alh'
]
```