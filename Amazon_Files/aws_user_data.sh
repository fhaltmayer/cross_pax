#!/bin/bash
# ref: https://github.com/awslabs/ec2-spot-labs/blob/master/ec2-spot-deep-learning-training/user_data_script.sh
# Made a few changes to avoid causing problems with instances not being deleted due to a hang on shutdown. Also added
# the closing of open ports because I would rather not have open ports on an expensive instance.

# Uncomment if not using custom image

sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt install unzip -y
sudo unzip awscliv2.zip
sudo ./aws/install

INSTANCE_ID=$(curl --local-port 4000-4200 -s http://169.254.169.254/latest/meta-data/instance-id)
INSTANCE_AZ=$(curl --local-port 4000-4200 -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
AWS_REGION=us-west-2

VOLUME_ID=$(aws ec2 describe-volumes --region $AWS_REGION --filter "Name=tag:Name,Values=DeepL" --query "Volumes[].VolumeId" --output text)
VOLUME_AZ=$(aws ec2 describe-volumes --region $AWS_REGION --filter "Name=tag:Name,Values=DeepL" --query "Volumes[].AvailabilityZone" --output text)


# Uncomment if not using custome image

sudo apt-get update
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common \
    --assume-yes

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable"

sudo apt-get update --assume-yes

sudo apt-get install docker-ce docker-ce-cli containerd.io --assume-yes


sudo git clone https://github.com/fhaltmayer/cross_pax

# Close up open ports 
sudo aws ec2  modify-instance-attribute --instance-id $INSTANCE_ID --groups sg-059277e4f44253675

cd cross_pax

sudo docker build . -t paxos

sudo docker run -p 5000:5000 -e VIEW=10.0.0.5:5000 -e IPPORT=10.0.0.4:5000 paxos

