import json
import requests
import urllib
import os

##################################################################
# 
# File: 
# application-provision.py
#
# Desc: 
# -------------------
# Example for application provisioning via the Morpheus API
#
# Requirements:
# -------------------
# python3 -m venv morpheus-tools
# source morpheus-tools/bin/activate
# pip install requests
#
# Steps:
# -------------------
# 1. Set up terraform blueprint for network
# 2. Set up app blueprint for app (Morpheus DSL)
# 3. Call API, auth, get bearer token
# 4. Call API, create tf app
# 5. Take return payload and store in object
# 6. Manipulate app payload with details from tf return
# 7. Call API, create app
# 8. Capture return
#
##################################################################

# Define vars
apiEndpoint = os.environ['MORPHEUS_URL']
apiUsername = os.environ['MORPHEUS_USERNAME']
apiPassword = os.environ['MORPHEUS_PASSWORD']
awsAccessKey = os.environ['AWS_ACCESS_KEY']
awsSecretKey = os.environ['AWS_SECRET_KEY']

# Disable ssl warnings (for my example)
requests.packages.urllib3.disable_warnings()

# Out()
def out(aString):
	out = "\n--------------------------------------\n"
	out += "| "+ aString+"\n"
	out += "--------------------------------------"
	print(out)

def printConfig():
	out = "\n===============================\n"
	out += "= Config:\n"
	out += "= apiEndpoint="+apiEndpoint+"\n" 
	out += "= apiUsername="+apiUsername+"\n"
	out += "= apiPassword="+apiPassword+"\n"
	out += "= awsAccessKey="+awsAccessKey+"\n"
	out += "= awsSecretKey="+awsSecretKey+"\n"
	out += "===============================\n"
	print(out)

# Auth()
def auth():
	url = apiEndpoint+"/oauth/token?grant_type=password&scope=write&client_id=morph-customer"
	credsJSON = {'username':apiUsername, 'password': apiPassword};
	response = requests.post(url, verify=False, headers='', data=credsJSON)
	authInfo = json.loads(response.content)
	print(authInfo.get('access_token'))
	return authInfo.get('access_token');

def getNetworkBP():
	return {
  		"id": 2,
  		"image": "https://10.30.20.180/storage/logos/uploads/AppTemplate/2/templateImage/network_original.png",
  		"name": "AWSNetwork",
  		"description": "AWSNetwork",
  		"terraform": {
    		"tf": "#################################\n##\t\t\tVariables\t\t   ##\n#################################\nvariable \"access_key\" {}\nvariable \"secret_key\" {} \n\n#################################\n##\t\t\tProvider\t\t   ##\n#################################\nprovider \"aws\" {\n\tregion = \"us-west-1\"\n\taccess_key = \"${var.access_key}\"\n    secret_key = \"${var.secret_key}\"\n}\n\ndata \"aws_availability_zones\" \"all\" {}\n\t\n#################################\n##\t\t\t  VPC\t\t\t   ##\n#################################\nresource \"aws_vpc\" \"main\" {\n\tcidr_block = \"10.0.0.0/16\"\n\ttags {\n\tinstance_tenancy     = \"default\"\n\tenable_dns_support   = \"true\"\n\tenable_dns_hostnames = \"true\"\n\t}\n\t\n\ttags {\n\t\tName        = \"from-morpheus\"\n\t\tDescription = \"This is a test VPC TF create from Morpheus\"\n\t}\n\t\n\tlifecycle {\n\t\tcreate_before_destroy = true\n\t}\n}\n\n#################################\n##\t\tPublic Subnets\t\t   ##\n#################################\n### Create Public Subnet 1 in AZ1\nresource \"aws_subnet\" \"public_subnet_az1\" {\n  vpc_id            = \"${aws_vpc.main.id}\"\n  cidr_block        = \"${cidrsubnet(\"10.0.0.0/16\", 10, 3)}\"\n  availability_zone = \"${data.aws_availability_zones.all.names[0]}\"\n\n  tags {\n    Name = \"${aws_vpc.main.id}-public-subnet-az1\"\n  }\n}\n\n### Associate Public Subnet 1 to Public Route Table\nresource \"aws_route_table_association\" \"public_1\" {\n  subnet_id      = \"${aws_subnet.public_subnet_az1.id}\"\n  route_table_id = \"${aws_route_table.public_route_table.id}\"\n}\n\t\n#################################\n##\t\tPrivate Subnets\t\t   ##\n#################################\n### Create Private Subnet for NAT Gateway 1 in AZ1\nresource \"aws_subnet\" \"nat_subnet_az1\" {\n  vpc_id            = \"${aws_vpc.main.id}\"\n  cidr_block        = \"${cidrsubnet(\"10.0.0.0/16\", 12, 4076)}\"\n  availability_zone = \"${data.aws_availability_zones.all.names[0]}\"\n\n  tags {\n    Name = \"${aws_vpc.main.id}-NatGatewayPublicSubnet1\"\n  }\n}\n\nresource \"aws_route_table_association\" \"nat_gw_1\" {\n  subnet_id      = \"${aws_subnet.nat_subnet_az1.id}\"\n  route_table_id = \"${aws_route_table.public_route_table.id}\"\n}\n\n#################################\n##\t\t  Internet Gateway     ##\n#################################\nresource \"aws_internet_gateway\" \"internet\" {\n\tvpc_id = \"${aws_vpc.main.id}\"\n\ttags {\n\tName = \"${aws_vpc.main.id}-internet_gateway\"\n\t}\n\tlifecycle {\n\t\tcreate_before_destroy = true\n\t}\n}\n\n#################################\n##\t  Public Routing Table     ##\n#################################\n### Create Public Route Table for VPC\nresource \"aws_route_table\" \"public_route_table\" {\n\tvpc_id = \"${aws_vpc.main.id}\"\n\n\troute {\n\t\tcidr_block = \"0.0.0.0/0\"\n\t\tgateway_id = \"${aws_internet_gateway.internet.id}\"\n\t}\n\n\ttags {\n\t\tName = \"${aws_vpc.main.id}-PublicRouteTable\"\n\t}\n}\n\n#################################\n##\t  Private Routing Table    ##\n#################################\n### Create Private Route Table for VPC for AZ1\nresource \"aws_route_table\" \"private_route_table_az1\" {\n\tvpc_id = \"${aws_vpc.main.id}\"\n\n\ttags {\n\t\tName = \"${aws_vpc.main.id}-PrivateRouteTable-AZ1\"\n\t}\n}\n\n### Create Private Route Table for VPC for AZ2\nresource \"aws_route_table\" \"private_route_table_az2\" {\n\tvpc_id = \"${aws_vpc.main.id}\"\n\n\ttags {\n\t\tName = \"${aws_vpc.main.id}-PrivateRouteTable-AZ2\"\n\t}\t\n}\n\n### Create Private Route Table for VPC for AZ3\nresource \"aws_route_table\" \"private_route_table_az3\" {\n\tvpc_id = \"${aws_vpc.main.id}\"\n\n\ttags {\n\t\tName = \"${aws_vpc.main.id}-PrivateRouteTable-AZ3\"\n  }\n}\n\n#################################\n##\t\t   Security Group  \t   ##\n#################################\nresource \"aws_security_group\" \"main\" {\n\tname = \"${aws_vpc.main.id}-SecurityGroup\"\n\tvpc_id = \"${aws_vpc.main.id}\"\n\tingress {\n\t\tfrom_port = 8080\n\t\tto_port = 8080\n\t\tprotocol = \"tcp\"\n\t\tcidr_blocks = [\"0.0.0.0/0\"]\n\t}\t\n\tlifecycle {\n\t\tcreate_before_destroy = true\n\t}\n}",
    		"tfvarSecret": "tfvars/AWS_TRAINING",
    		"git": {},
    		"configType": "tf"
  		},
  		"type": "terraform",
  		"category": "network",
  		"templateName": "AWSNetwork",
  		"defaultCluster": "null",
  		"defaultPool": "null",
  		"needsReset": "true",
  		"group": {
    		"id": 1,
    		"name": "jb-public-group"
  		},
  		"environment": "Dev",
  		"envCode": "dev"
	}

def runAppCreate(bp):
	url = apiEndpoint+"/api/apps"
	response = requests.post(url, verify=False, headers=headers, json=bp)
	return json.loads(response.content);

def getAppInformation(appId):
	url = apiEndpoint+"/api/apps/"+str(appId)
	response = requests.get(url, verify=False, headers=headers)
	return json.loads(response.content);

def getZone(zoneCode):
	cloud = ""
	url = apiEndpoint+"/api/zones"
	response = requests.get(url, verify=False, headers=headers)
	zList = json.loads(response.content);
	for zone in zList.get('zones'):
		if zone.get("code") == zoneCode:
			cloud = zone;
			break
	return cloud

def getResourcePools(zoneId):
	url = apiEndpoint+"/api/zones/"+str(zoneId)+"/resource-pools"
	response = requests.get(url, verify=False, headers=headers)
	return json.loads(response.content);


printConfig()

# 1. Auth and get bearer token
out("Doing the auth thang...")
apiBearerToken = auth()
headers = {'Content-Type': 'application/json','Authorization': 'Bearer {0}'.format(apiBearerToken)}

# 2. Run Terraform create
out("Running the network create in TF...");
networkAppInfo = runAppCreate(getNetworkBP())
print(networkAppInfo)

# 3. Get resource pools for the desired cloud
out("Getting resource pools...");
zone = getZone("mtaws");
resourcePools = getResourcePools(zone.get('id'))
print(resourcePools)

