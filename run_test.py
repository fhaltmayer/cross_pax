import os
import requests
import json
import time
import threading
import random
import subprocess

class Node:
    def __init__(self, external_port, ip, node_id):
        self.external_port = external_port
        self.ip = ip
        self.id = node_id
    def __str__(self):
        return "\n External Port: " + str(self.external_port) + "\n IP: " + self.ip + "\n ID: " + str(self.id)

def build_file(name): 
    os.system("sudo docker build . -t " + name)

def build_view(count, ip = "10.0.0.", internal_port = 5000, external_port = 8080):
    nodes = []
    for x in range(2, count+2):
        node_ip = ip + str(x)
        node_external_port = external_port + x
        nodes.append(Node(node_external_port, node_ip, x-2))
    return nodes

def launch_instances(nodes, internal_port, net, name):
    for x in nodes:
        if len(nodes) == 1:
            launch_string = "sudo docker run"
        else:
            launch_string = "sudo docker run -d"
        view = [y.ip + ":" + str(internal_port) for y in nodes]
        launch_string += " -p " + str(x.external_port) + ":" + str(internal_port)
        launch_string += " --ip=" + x.ip 
        launch_string += " --net=" + net
        launch_string += " -e VIEW="
        launch_string += ",".join(view)
        launch_string += " -e IPPORT=" + x.ip + ":" + str(internal_port)
        launch_string += " " + name
        # print(launch_string)
        node_id = subprocess.check_output(launch_string, shell=True).decode("utf-8").rstrip('\n')
        x.docker_id = node_id
        print(x.docker_id)
    time.sleep(2)
    os.system("sudo docker ps")

def kill_all():
    os.system("sudo docker kill $(docker ps -q)")



def disconnect_node(node, network):
    dis_string = "sudo docker network disconnect " + network + " " + node.docker_id
    os.system(dis_string)
    time.sleep(0.5)


def connect_node(node, network):
    con_string = "sudo docker network connect " + network + " --ip=" + node.ip + ' ' + node.id
    os.system(con_string)
    time.sleep(0.5)


def test_broadcast(nodes, local, percentage, paxos, rounds):
   
    def concurrent(address, num):
        
        print("sending to ip: " + address)
        msg = {"val": str(random.randint(0,1000))}
        response = requests.post(address, json = msg)
        response = response.json()
        if "result" in response:
            print(address, "success")
        else:
            print(address, "failure")

    threads = []

    while rounds > 0:
        if percentage < 0:
            random_start = 0
            end = 1
        
        else:
            rand_percentage = int(len(nodes) * (percentage/100))
            random_start = random.random()*(len(nodes)-rand_percentage)
            random_start = int(random_start)

            end = random_start+rand_percentage
            end = int(end)

        for i, x in enumerate(nodes[random_start: end]):
            address = local + ":" + str(x.external_port) + "/kv-store/" + paxos
            thread = threading.Thread(target=concurrent, args=(address, i))
            thread.start()
            threads.append(thread)
            # if i %2  == 0:
            #     time.sleep(.1)
            # else:
            #     pass

        rounds -= 1
        

    for x in threads:
        x.join()

    results = []

    for x in nodes:
        address = local + ":" + str(x.external_port) + "/"
        response = requests.get(address)
        response = response.json()
        sub_res = []
        for y in response:
            if int(y) > -1:
                sub_res.append(response[y])
        sub_res.sort()
        results.append((x.external_port, sub_res))
    
    equal = results[0][1]
    for x in results:
        if x[1] != equal:
            return 0

    print(results)
    return 1

# def test_diconnected_nodes(nodes, local, paxos):
#     disconnect_nodes = nodes[:len(nodes)]


if __name__ == "__main__":

    local = "http://127.0.0.1"
    name = "paxos"
    internal_port = 5000
    external_port = 8080
    ip = "10.0.0."
    net = "mynet"
    node_count = 12
    percent = 20
    rounds = 5
    paxos = "multipaxos"
    # paxos = "paxos"

    
    kill_all()

    build_file(name)

    nodes = build_view(node_count, ip, internal_port, external_port)
    
    launch_instances(nodes, internal_port, net, name)

    time.sleep(1)

    test_broadcast(nodes, local, percent, paxos, rounds)

# sudo docker run -p 8083:5000 --ip=10.0.0.20 --net=mynet  -e VIEW=10.0.0.20:5000,10.0.0.21:5000,10.0.0.22:5000,10.0.0.23:5000 -e IPPORT=10.0.0.20:8080 paxos

# sudo docker run -p 8082:5000 --ip=10.0.0.2 --net=mynet  -e VIEW=10.0.0.2:5000,10.0.0.3:5000 -e IPPORT=10.0.0.2:5000 paxos
# sudo docker run -p 8083:5000 --ip=10.0.0.3 --net=mynet  -e VIEW=10.0.0.2:5000,10.0.0.3:5000 -e IPPORT=10.0.0.3:5000 paxos