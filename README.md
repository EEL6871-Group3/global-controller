# global-controller
## Components
* CPU sampler
    - sample the current CPU of each running nodes
    - compute the average CPU usage as the cluster CPU, store it
* controller
    - if the recent `number_cpu_data_used` cluster CPU are all greater than the cpu_bar, scale up
    - check the lastest created node, if it's not running any job and it has been at least `node_start_delay` seconds, delete it(scaling down)
* job renderer
    - read from the job list
    - try to assign the job to the running nodes in the order of the created time of the nodes. That is, assign the job to the earliest node possible, which will make the last node empty if possible to support scaling down
    - if no node is available, waite for the next iteration to render the job

## Settings
Settings are at the start of the `global_controller.py` file

```Python
# APIs
get_nodes_api = "http://localhost:5001/nodes"
start_node_api = "http://localhost:5001/start-node"
delete_node_api = "http://localhost:5001/delete-node"
cpu_api = "http://localhost:5001/cpu"

# settings
sample_time = 5  # every X seconds, save the CPU usage of each node
loop_sleep_time = (
    3  # every X seconds, based on the CPU usage, make a scaling up/down decision
)
master_node = "k8s-master"
worker_nodes = [
    "k8s-worker1",
    "k8s-worker2",
]  # list of the two workers, in the order of jobs assignemnt priority, e.g., job will be assigned to master node, if unable, to the worker1, then worker2
node_job_api = {
    "k8s-master": "http://localhost:5001/job",
    "k8s-worker1": "http://localhost:5001/job",
    "k8s-worker2": "http://localhost:5001/job",
}
node_pod_api = {
    "k8s-master": "http://localhost:5001/pod-num",
    "k8s-worker1": "http://localhost:5001/pod-num",
    "k8s-worker2": "http://localhost:5001/pod-num",
}
cpu_bar = 0.8
number_cpu_data_used = (
    6  # use the previous X number of cpu to see if we need to scale up
)
node_start_delay = (
    30  # no scaling down decision in X seconds after a scaling up decision
)
job_assign_time = 15  # every X seconds, schedule a job
job_file_name = "job_list.txt"
```

## run
`Python3 global_controller.py`.
Notice that the `job_list.txt` file must exists in the working directory where the controller is run.