import asyncio
import boto3

from botocore.exceptions import ClientError
from botocore.stub import Stubber
from temporalio import activity
from temporalio.exceptions import ApplicationError
from moto import mock_aws
from ipaddress import IPv4Address

from shared import  (
    VPCInfoInput, VPCInfoOutput, 
    SubnetInfoInput, SubnetInfoOutput, 
    InternetGatewayInfoInput, InternetGatewayInfoOutput,
    EC2InfoInput, EC2InfoOutput
    )

class AWSInfrastructureActivities:
    def __init__(self, session: boto3.session):
        self.session = session

#This activity will create a VPC in the specified region with the given CIDR 
# block in the region identified. The VPC is required before we can create 
# subnets or EC2 instances. The activity will return the VPC ID, the region 
# of the VPC, and the CIDR block of the VPC.
    @activity.defn
    async def create_vpc(
        self, input: VPCInfoInput
    ) -> VPCInfoOutput:

        activity.logger.info(f"Build VPC invoked with input: {input}")

        try:
            with mock_aws():
                ec2 = self.session.client("ec2", region_name=str(input.region))
                activity.logger.info(
                    f"Creating VPC with CIDR: {input.cidr_block}"
                )

                response = ec2.create_vpc(CidrBlock=str(input.cidr_block))
                vpc_id = response["Vpc"]["VpcId"]
                #wait for the vpc to exist
                waiter = ec2.get_waiter('vpc_available')     
                waiter.wait(VpcIds = [vpc_id], 
                                WaiterConfig={'Delay': 5, 'MaxAttempts': 20})

                activity.logger.info(
                    f"VPC {vpc_id} successfully created and is now available")
                return VPCInfoOutput(
                    vpc_id=response["Vpc"]["VpcId"], 
                    cidr_block=response["Vpc"]["CidrBlock"])

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            
            #These are errors that we cannot solve via simple retries and 
            # should be surfaced to the caller
            if error_code in ["InvalidVpc.Duplicate", "VpcLimitExceeded", 
                              "InvalidParameterValue"]:
                raise ApplicationError(
                    f"Permanent AWS failure: {error_code}", 
                    non_retryable=True
                )
       
            #TODO: Raise better Temporal error
            raise

#Create Subnet Activity
# This activity will create a subnet for a given VPC, given the VPC ID, 
# region, availability zone, and CIDR block.
    @activity.defn
    async def create_subnet(
        self, input: SubnetInfoInput
    ) -> SubnetInfoOutput:
        activity.logger.info(f"Build Subnets invoked with input: {input}")
        try:
            with mock_aws():
                ec2 = self.session.client("ec2", region_name=str(input.region))
                response = ec2.create_subnet(
                    VpcId=input.vpc_id,
                    CidrBlock=str(input.cidr_block),
                    AvailabilityZone=input.availability_zone
                )
                subnet_id = response["Subnet"]["SubnetId"]

                # Wait for subnet to exist
                waiter = ec2.get_waiter("subnet_available")
                waiter.wait(
                    SubnetIds=[subnet_id],
                    WaiterConfig={'Delay': 2, 'MaxAttempts': 5}
                )
                
                activity.logger.info(
                    f"Subnet {subnet_id} successfully created in VPC {input.vpc_id} with CIDR {input.cidr_block}")
                
                return SubnetInfoOutput(
                    vpc_id=response["Subnet"]["VpcId"],
                    subnet_id=response["Subnet"]["SubnetId"],
                    availability_zone=response["Subnet"]["AvailabilityZone"]
                    )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # Non-retryable: CIDR overlap or AZ issues
            if error_code in ["InvalidSubnet.Conflict", "InvalidParameterValue"]:
                raise ApplicationError(
                    f"Subnet creation failed: {error_code}", 
                    non_retryable=True)

            #TODO: Raise better Temporal error
            raise

#Create EC2 Instance Activity
# This activity will create an EC2 instance in the specified region, with the
# given instance type, operating system, and in the specified subnet. The activity 
# will return the instance ID and the public IP address of the instance.
    @activity.defn
    async def create_ec2_instance(
        self, input: EC2InfoInput
    ) -> EC2InfoOutput:
        activity.logger.info(f"Build EC2 Instance invoked with input: {input}")
        try:
            with mock_aws():
                ec2 = self.session.client("ec2", region_name=str(input.region))    
                # Map operating system to an Amazon Machine Image (AMI) ID
                # Hardcodded for the demo purposes
                if input.operating_system == "amazonlinux2":
                    # Amazon Linux 2 AMI ID for us-east-2
                    ami_id = "ami-0c02fb55956c7d316"  
                elif input.operating_system == "windows":
                    # Windows Server 2019 Base AMI ID for us-east-2
                    ami_id = "ami-0b69ea66ff7391e80"  
                else:
                    raise ApplicationError(
                        f"Unsupported operating system: {input.operating_system}",
                        non_retryable=True)

                response = ec2.run_instances(
                    ImageId=ami_id,
                    InstanceType=input.instance_type,
                    SubnetId=input.subnet_id,
                    MinCount=1,
                    MaxCount=1
                    )
                instance_id = response["Instances"][0]["InstanceId"]

                # Wait for instance to be running
                waiter = ec2.get_waiter("instance_running")
                waiter.wait(
                    InstanceIds=[instance_id],
                    WaiterConfig={'Delay': 5, 'MaxAttempts': 20}
                )

                # Retrieve instance information
                instance_description = ec2.describe_instances(InstanceIds=[instance_id])
                if "PublicIpAddress" not in instance_description["Reservations"][0]["Instances"][0]:
                    public_ip = ""
                else:
                    public_ip = instance_description["Reservations"][0]["Instances"][0].get("PublicIpAddress")
                response: EC2InfoOutput = EC2InfoOutput(
                    instance_id=response["Instances"][0]["InstanceId"],
                    public_ip=public_ip,
                    vpc_id=instance_description["Reservations"][0]["Instances"][0]["VpcId"],
                    subnet_id=instance_description["Reservations"][0]["Instances"][0]["SubnetId"]
                )
                activity.logger.info(
                    f"EC2 instance {instance_id} successfully created with public IP {public_ip}"
                )   
                return response
    

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # Non-retryable: Invalid subnet or instance type issues
            if error_code in ["InvalidSubnetID.NotFound", "InvalidInstanceType"]:
                raise ApplicationError(
                    f"EC2 instance creation failed: {error_code}",
                    non_retryable=True)

            #TODO: Raise better Temporal error
            raise
