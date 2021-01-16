import os
import requests
import json
import time
import threading
import subprocess
import sys
import random
launch_json =   {
                    "DryRun":False,
                    "ImageId": "ami-05d0c107fba01ca39",
                    "InstanceType": "t2.micro",
                    "KeyName": "Ubuntu-Desk",

                    "Placement": {
                        "AvailabilityZone": "us-west-2a",
                        "GroupName": "",
                        "Tenancy": "default"
                    },
                    "SecurityGroupIds": ["sg-0b18a61cc53d131b4"],
                    "SubnetId": "subnet-04af643d9e0f97df3",
                    "UserData": "",
                    "IamInstanceProfile": {
                        "Arn": "arn:aws:iam::970535627334:instance-profile/EC2_Port_Close",
                    },
                    "PrivateIpAddress": "10.0.0.4",
                }

# user_script =   "\n".join(("#!/bin/bash", 
#                 "INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)",
#                 "sudo git clone https://github.com/fhaltmayer/cross_pax",
#                 "aws ec2  modify-instance-attribute --instance-id $INSTANCE_ID --groups sg-059277e4f44253675",
#                 "cd cross_pax",
#                 "sudo docker build . -t paxos",
#                 ""))

user_script = "\n".join((
"#!/bin/bash",
"INSTANCE_ID=$(curl --local-port 4000-4200 -s http://169.254.169.254/latest/meta-data/instance-id)",
"INSTANCE_AZ=$(curl --local-port 4000-4200 -s http://169.254.169.254/latest/meta-data/placement/availability-zone)",
"AWS_REGION=us-west-2",

"VOLUME_ID=$(aws ec2 describe-volumes --region $AWS_REGION --filter \"Name=tag:Name,Values=DeepL\" --query \"Volumes[].VolumeId\" --output text)",
"VOLUME_AZ=$(aws ec2 describe-volumes --region $AWS_REGION --filter \"Name=tag:Name,Values=DeepL\" --query \"Volumes[].AvailabilityZone\" --output text)",

"sudo git clone https://github.com/fhaltmayer/cross_pax",


"sudo aws ec2  modify-instance-attribute --instance-id $INSTANCE_ID --groups sg-059277e4f44253675",

"cd cross_pax",

"sudo docker build . -t paxos"))

# sudo docker run -p 5000:5000 -e VIEW=10.0.0.5:5000 -e IPPORT=10.0.0.4:5000 paxos





class Node:
    def __init__(self, port, private_ip, node_id):
        self.port = port
        self.private_ip = private_ip
        self.full_private_address = private_ip + ":" + str(port)
        self.id = node_id
        self.json = launch_json.copy()
        self.json["PrivateIpAddress"] = private_ip
        self.view = None
        self.instance_id = None

  

def build_nodes(count, private_ip = "10.0.0.", port=5000):
    nodes = []
    for x in range(4, count+4):
        node_private_ip = private_ip + str(x)
        nodes.append(Node(port, node_private_ip, x-4))

    for x in nodes:
        view = [y.private_ip + ":" + str(y.port) for y in nodes]
        view.remove(x.private_ip + ":" + str(x.port))
        x.view = view
        add_line = "sudo docker run -p 5000:5000 -e IPPORT=" + str(x.full_private_address) + " -e VIEW=" + ",".join(view) + " paxos"
        x.json["UserData"] = user_script +  "\n" + add_line
        print(x.json["PrivateIpAddress"])
    return nodes

def run_nodes(nodes):
    print("Starting nodes.")
    checker = []
    for x in nodes:
        checker.append(x)

    while len(checker) > 0:
        for x in checker:
            
            with open("start.json", 'w') as f:
                json.dump(x.json, f)
            path = os.path.abspath(os.getcwd())
            path += "/start.json"

            try:
                output = subprocess.check_output("aws ec2 run-instances --cli-input-json file://" + str(path) + " --output json", shell = True)
                output = json.loads(output)
                x.instance_id = output["Instances"][0]["InstanceId"]
                print(str("Node " + str(x.id) + " launched."))
                checker.remove(x)
            except:
                # print("Node " + str(x.id) + " failed to launch.")
                pass
        time.sleep(2)


def get_public_ip(nodes):
    print("Getting public ips.")
    checker = []
    for x in nodes:
        checker.append(x)
    while len(checker) > 0:
        for x in checker:
            try:
                output = subprocess.check_output("aws ec2 describe-instances --instance-ids " + x.instance_id + " --output json", shell = True)
                output = json.loads(output)
                x.public_ip = output["Reservations"][0]["Instances"][0]["PublicIpAddress"]
                x.full_public_address = "http://" + x.public_ip + ":" + str(x.port)
                print(x.full_public_address + " found for node: " + str(x.id) + ".")
                checker.remove(x)
            except:
                # print("Node " + str(x.id) + " failed to find address.")
                pass
        time.sleep(2)

def wait_for_load(nodes):
    print("Testing node reachability.")
    count = 0
    checker = []
    for x in nodes:
        checker.append(x)

    while len(checker) > 0:
        count += 1
        print("Loop: " + str(count))
        for x in checker:
            try :
                response = requests.get(x.full_public_address + "/", timeout=3)
                print(x.full_public_address + " reachable for node: " + str(x.id) + ".")
                checker.remove(x)
            except:
                pass
        time.sleep(5)
    print("All Ready")

def test_broadcast(nodes):
   
    def concurrent(address, num):
        print("sending to ip: " + address)
        msg = {"val": str(random.randint(0,1000))}
        response = requests.post(address, json = msg)
        print(address, "done")
    threads = []
    count = 100
    while(count > 0):
        for i, x in enumerate(nodes):
            address = x.full_public_address + "/kv-store/test_POST"
            thread = threading.Thread(target=concurrent, args=(address, i))
            thread.start()
            threads.append(thread)
        count -= 1

    for x in threads:
        x.join()

    results = []

    for x in nodes:
        address = x.full_public_address + "/"
        response = requests.get(address)
        response = response.json()
        results.append((x.full_public_address, response["log"]))
    equal = results[0][1]
    same = True
    for x in results:
        if x[1] != equal:
            same = False
            break
    if same:
        print("All nodes are consistent.")
    else:
        print("Inconsisitency found.")


    return 1

def shutdown(nodes):
    for x in nodes:
        os.system("aws ec2 terminate-instances --instance-ids " + x.instance_id)
    return 1




if __name__ == "__main__":

    port = 5000
    private_ip = "10.0.0."
    node_count = 10
    nodes = build_nodes(node_count, private_ip, port)
    run_nodes(nodes)
    get_public_ip(nodes)
    wait_for_load(nodes)
    test_broadcast(nodes)
    input("Press enter to shutdown instances...")
    shutdown(nodes)

