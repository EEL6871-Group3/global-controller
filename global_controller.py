import time
import threading
import requests
import logging
from datetime import datetime

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
master_node = "node0.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us"
worker_nodes = [
    "node1.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us",
    "node2.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us",
]  # list of the two workers, in the order of jobs assignemnt priority, e.g., job will be assigned to master node, if unable, to the worker1, then worker2
node_job_api = {
    "node0.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.71:5004/job",
    "node1.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.114:5004/job",
    "node2.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.87:5004/job",
}
node_pod_api = {
    "node0.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.71:5004/lpod-num",
    "node1.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.114:5004/lpod-num",
    "node2.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.87:5004/lpod-num",
}

node_url = {
    "node0.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.71:5004/",
    "node1.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.114:5004/",
    "node2.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us": "http://128.110.217.87:5004/",
}
cpu_bar = 0.8
number_cpu_data_used = (
    2  # use the previous X number of cpu to see if we need to scale up
)
node_start_delay = (
    30  # no scaling down decision in X seconds after a scaling up decision
)
job_assign_time = 15  # every X seconds, schedule a job
job_file_name = "job_list.txt"

# global variables
# CPU_usage = {
#     master_node: [],
#     worker_nodes[0]: [],
#     worker_nodes[1]: [],
# }
cluster_cpu = []  # recent cluster CPU usage
started_nodes = [
    master_node,
    # "node1.group-3-project.ufl-eel6871-fa23-pg0.utah.cloudlab.us",
]  # the nodes that have been started by the controller.
last_started_time = datetime.now()
job_list = []


def get_node_pod_num(node):
    try:
        response = requests.get(node_pod_api[node])
        if response.status_code == 200:
            res = response.json()
            if res["success"]:
                return res["pod-num"], None
            else:
                return None, f"Error: {res['msg']}"
        else:
            return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, e


def read_file_to_list(file_path):
    """read a file, return a list of strings(each line)"""
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
        # Strip newline characters from each line
        lines = [line.strip() for line in lines]
        return lines, None
    except FileNotFoundError:
        return [], "The file was not found."
    except Exception as e:
        return [], e


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


def delete_node(node_name):
    try:
        payload = {"node": node_name}
        response = requests.post(delete_node_api, json=payload)
        if response.status_code == 200:
            res = response.json()
            return res["success"], res["msg"]
        else:
            return False, f"Error: {response.status_code}"
    except Exception as e:
        return False, e


def start_controller(node_name):
    try:
        response = requests.get(node_url[node_name] + "/start")
        if response.status_code == 200:
            res = response.json()
            return res["success"], res["msg"]
        else:
            return False, f"Error: {response.status_code}"
    except Exception as e:
        return False, e


def stop_controller(node_name):
    try:
        response = requests.get(node_url[node_name] + "/stop")
        if response.status_code == 200:
            res = response.json()
            return res["success"], res["msg"]
        else:
            return False, f"Error: {response.status_code}"
    except Exception as e:
        return False, e


def start_new_node(node_name):
    try:
        payload = {"node": node_name}
        response = requests.post(start_node_api, json=payload)
        if response.status_code == 200:
            res = response.json()
            return res["success"], res["msg"]
        else:
            return False, f"Error: {response.status_code}"
    except Exception as e:
        return False, e


def remove_worker(node_name):
    global worker_nodes, started_nodes
    index = 0
    for node in worker_nodes:
        if node == node_name:
            break
        index += 1
    worker_nodes.pop(index)

    index = 0
    for node in started_nodes:
        if node == node_name:
            break
        index += 1
    started_nodes.pop(index)


def sample_cpu():
    """sample the cluster CPU"""
    global sample_time, started_nodes, cluster_cpu
    while True:
        running_nodes, err = get_nodes()
        logging.debug(f"running nodes: {running_nodes}")
        if err != None:
            logging.critical(f"error getting nodes, msg: {err}")
            time.sleep(sample_time)
            continue
        nodes_cpu, err = get_cpu()
        logging.debug(f"nodes_cpu: {nodes_cpu}")
        if err != None:
            logging.critical(f"error getting nodes cpu, msg: {err}")
            time.sleep(sample_time)
            continue
        total_cpu = 0
        num = 0
        for node in started_nodes:
            if node not in running_nodes:
                logging.error(f"node started but not currently running: {node}")
                logging.info(
                    f"removing node {node} from worker nodes because it stops accidentally"
                )
                remove_worker(node)
                continue
            if node not in nodes_cpu:
                logging.error(f"can't get node CPU, node: {node}")
                continue
            total_cpu += nodes_cpu[node] / 100
            num += 1
        if num != 0:
            cur_cluster_cpu = total_cpu / num
            cluster_cpu.append(cur_cluster_cpu)
            logging.info(f"current cluster cpu: {cur_cluster_cpu}")
        time.sleep(sample_time)


def controller():
    """make scaling up of scaling down decision"""
    global started_nodes, cluster_cpu, number_cpu_data_used, cpu_bar, last_started_time
    while True:
        # scaling up decision
        # compute cluster cpu
        ave_cluster_cpu = None
        if len(cluster_cpu) < number_cpu_data_used:
            logging.info("not enough CPU data, skip scaling up")
            time.sleep(loop_sleep_time)
            continue
        else:
            cpu_data = cluster_cpu[-number_cpu_data_used:]
            ave_cluster_cpu = sum(cpu_data) / number_cpu_data_used
        if ave_cluster_cpu > cpu_bar:
            # scale up
            if len(started_nodes) == len(worker_nodes) + 1:
                logging.info("all nodes started, won't scale up")
            else:
                logging.info(
                    f"current cluster average {ave_cluster_cpu}, greater than {cpu_bar}, scaling up"
                )
                new_node = worker_nodes[
                    len(started_nodes) - 1
                ]  # master node is always started
                ok, err = start_new_node(new_node)
                if ok:
                    ok, msg = start_controller(new_node)
                    if ok:
                        started_nodes.append(new_node)
                        last_started_time = datetime.now()
                    else:
                        logging.error(
                            f"error trying to start the controller for node {new_node}, msg: {msg}"
                        )
                else:
                    logging.error(f"error trying to start node {new_node}, msg: {err}")
        else:
            logging.info(
                f"current cluster average {ave_cluster_cpu}, less than {cpu_bar}, not scaling up"
            )
        # scaling down decision
        if (
            datetime.now() - last_started_time
        ).total_seconds() > node_start_delay and len(started_nodes) > 1:
            # check last node jobs, if it's zero, delete it
            target_node = started_nodes[-1]

            # check node pod num
            pod_num, err = get_node_pod_num(target_node)
            if pod_num is None:
                logging.error(f"error getting pod num for node {target_node}")
            else:
                if pod_num == 0:
                    ok, e = delete_node(target_node)
                    if not ok:
                        logging.error(
                            f"error when deleting node {target_node}, error: {e}"
                        )
                    else:
                        ok, msg = stop_controller(target_node)
                        started_nodes.pop()
                        logging.info(f"scaling down: deleted node {target_node}")
                        if not ok:
                            logging.error(
                                f"error when stopping controller of the deleted node {target_node}, error: {msg}"
                            )
                else:
                    logging.error(
                        f"node {target_node} pod num {pod_num}, won't be deleted"
                    )
        time.sleep(loop_sleep_time)


def assign_job(job, node_name):
    """try to assign a job to a node

    Args:
        job (_type_): _description_
        node (_type_): _description_
    """
    try:
        payload = {"node": node_name, "job": job}
        response = requests.post(node_job_api[node_name], json=payload)
        if response.status_code == 200:
            res = response.json()
            return res["success"], res["msg"]
        else:
            return False, f"Error: {response.status_code}"
    except Exception as e:
        return False, e


def job_scheduling():
    while True:
        job = job_list[0]
        job_assigned = False
        for node in started_nodes:
            ok, err = assign_job(job, node)
            if not ok:
                logging.info(f"can't assign job {job} to node {node}, because {err}")
            else:
                logging.info(f"assgiend job {job} to node {node}")
                job_assigned = True
                break
        if not job_assigned:
            logging.info(
                f"job {job} can't be assigned, will try to assign the job in the next iteration"
            )
        else:
            job_list = job_list[1:]
        time.sleep(job_assign_time)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # read job list
    job_list, error = read_file_to_list(job_file_name)
    logging.info(f"getting job list from {job_file_name}")
    if error != None:
        logging.critical(f"error getting the job list: {error}")
        logging.critical("shutting down")
        exit(0)

    # sample_cpu()

    # start CPU sampling
    logging.info("start sampling")
    sample_cpu_thread = threading.Thread(target=sample_cpu)
    sample_cpu_thread.daemon = True
    sample_cpu_thread.start()

    controller()

    # start controller
    logging.info("start controller")
    controller_thread = threading.Thread(target=controller)
    controller_thread.daemon = True
    controller_thread.start()

    # start job rendering
    logging.info("start controller")
    job_thread = threading.Thread(target=job_scheduling)
    job_thread.daemon = True
    job_thread.start()
