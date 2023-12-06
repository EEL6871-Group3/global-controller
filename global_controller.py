import time
import threading
import requests
import logging

# APIs
get_nodes_api = "localhost:5001/nodes"
start_node_api = "localhost:5001/start-node"
delete_node_api = "localhost:5001/delete-node"
cpu_api = "localhost:5001/cpu"

# settings
sample_time = 5  # every X seconds, save the CPU usage of each node
loop_sleep_time = (
    30  # every X seconds, based on the CPU usage, make a scaling up/down decision
)
master_node = "k8s-master"
worker_nodes = [
    "k8s-worker1",
    "k8s-worker2",
]  # list of the two workers, in the order of jobs assignemnt priority, e.g., job will be assigned to master node, if unable, to the worker1, then worker2

# global variables
# CPU_usage = {
#     master_node: [],
#     worker_nodes[0]: [],
#     worker_nodes[1]: [],
# }
cluster_cpu = []  # recent cluster CPU usage
started_nodes = [master_node]  # the nodes that have been started by the controller.


def get_nodes():
    """get the current running nodes"""
    try:
        response = requests.get(get_nodes_api)
        if response.status_code == 200:
            res = response.json()
            if res["success"]:
                return res["nodes"], None
            else:
                return None, f"Error: {res['msg']}"
        else:
            return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, e


def get_cpu():
    """get the current CPU usage"""
    try:
        response = requests.get(cpu_api)
        if response.status_code == 200:
            cpu_data = response.json()
            return cpu_data, None
        else:
            return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, e


def sample_cpu():
    """sample the cluster CPU"""
    global sample_time
    while True:
        nodes, err = get_nodes()
        if err != None:
            logging.critical(f"error getting nodes, msg: {err}")
        cpu, err = get_cpu()
        if err != None:
            logging.critical(f"error getting nodes cpu, msg: {err}")

        time.sleep(sample_cpu)
