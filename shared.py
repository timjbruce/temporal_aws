from dataclasses import dataclass
from enum import StrEnum

TASK_QUEUE_NAME = "aws-infrastructure-tasks"

@dataclass
class AWSInfrastructureWorkflowInput:
    region: str
    cidr_block: str
    instance_type: str
    operating_system: str

@dataclass
class AWSInfrastructureWorkflowOutput:
    region: str
    vpc_id: str
    subnet_ids: list[str]
    instance_id: str
    instance_ip: str

@dataclass
class VPCInfoInput:
    region: str
    cidr_block: str

@dataclass
class VPCInfoOutput:
    vpc_id: str
    cidr_block: str

@dataclass
class SubnetInfoInput:
    vpc_id: str
    region: str
    cidr_block: str
    availability_zone: str

@dataclass
class SubnetInfoOutput:
    vpc_id: str
    subnet_id: str
    availability_zone: str

@dataclass
class InternetGatewayInfoInput:
    region: str
    vpc_id: str

@dataclass
class InternetGatewayInfoOutput:
    vpc_id: str
    internet_gateway_id: str

@dataclass
class EC2InfoInput:
    region: str
    instance_type: str
    operating_system: str
    subnet_id: str

@dataclass
class EC2InfoOutput:
    instance_id: str
    public_ip: str
    vpc_id: str
    subnet_id: str
