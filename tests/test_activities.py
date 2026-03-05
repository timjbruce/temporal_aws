import boto3
from moto import mock_aws

import pytest
from activities import AWSInfrastructureActivities
from ipaddress import IPv4Network
from temporalio.testing import ActivityEnvironment
from temporalio.exceptions import ApplicationError

from shared import (
    VPCInfoInput, VPCInfoOutput, 
    SubnetInfoInput, SubnetInfoOutput, 
    EC2InfoInput, EC2InfoOutput
)

def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"

@pytest.fixture
def vpc_creator():
    """Returns a function that creates a VPC and returns the full Boto3 response."""
    with mock_aws():
        def _create(cidr="10.0.0.0/16"):
            ec2 = boto3.client("ec2", region_name="us-east-1")
            return ec2.create_vpc(CidrBlock=cidr)
        return _create

@pytest.fixture
def subnet_creator():
    """Returns a function that creates a Subnet for a given VPC ID."""
    with mock_aws():
        def _create(vpc_id, cidr="10.0.1.0/24"):
            ec2 = boto3.client("ec2", region_name="us-east-1")
            return ec2.create_subnet(VpcId=vpc_id, CidrBlock=cidr)
        return _create
    
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "vpc_input, vpc_output",
    [
        (
            VPCInfoInput(region="us-east-1", cidr_block="10.0.0.0/16"),
            VPCInfoOutput(vpc_id="vpc-12345", 
                          cidr_block="10.0.0.0/16")
        )
    ])
    
@pytest.mark.asyncio
async def test_create_vpc(vpc_input, vpc_output):
    with mock_aws():
        session = boto3.Session()
        activity_environment = ActivityEnvironment()
        activities = AWSInfrastructureActivities(session)
        result = await activity_environment.run(activities.create_vpc, vpc_input)
        assert IPv4Network(result.cidr_block) == IPv4Network(str(vpc_input.cidr_block))

@pytest.mark.parametrize(
    "subnet_input, subnet_output",
    [
        (
            SubnetInfoInput(
                vpc_id="", 
                region="us-east-1", 
                cidr_block="10.0.1.0/24",
                availability_zone="us-east-1a"),
            SubnetInfoOutput(
                vpc_id="", 
                subnet_id="subnet-12345", 
                availability_zone="us-east-1a")
        )
    ]
)

@pytest.mark.asyncio
async def test_create_subnet(vpc_creator, subnet_input, subnet_output):
    with mock_aws():
        session = boto3.Session()
        activity_environment = ActivityEnvironment()
        activities = AWSInfrastructureActivities(session)
        vpc_resp = vpc_creator()
        subnet_input.vpc_id = vpc_resp["Vpc"]["VpcId"]
        result = await activity_environment.run(activities.create_subnet, subnet_input)
        assert subnet_input.vpc_id == result.vpc_id


@pytest.mark.parametrize(
    "ec2_input, ec2_output",
    [
        (
            EC2InfoInput(
                region="us-east-1", 
                instance_type="t2.micro",
                operating_system="linux",
                subnet_id=""
            ),
            EC2InfoOutput(
                vpc_id="",
                subnet_id="",
                instance_id="i-12345", 
                public_ip="54.123.45.67"
            )
        )
    ]
)

@pytest.mark.asyncio
async def test_create_ec2_instance(vpc_creator, subnet_creator, ec2_input, ec2_output):
    with mock_aws():
        session = boto3.Session()
        activity_environment = ActivityEnvironment()
        activities = AWSInfrastructureActivities(session)
        vpc_resp = vpc_creator() 
        vpc_id = vpc_resp["Vpc"]["VpcId"]
        subnet_resp = subnet_creator(vpc_id)
        subnet_id = subnet_resp["Subnet"]["SubnetId"]
        ec2_input.subnet_id = subnet_id
        result = await activity_environment.run(activities.create_ec2_instance, ec2_input)
        assert result.vpc_id == vpc_id
        assert result.subnet_id == subnet_id
        print(result)