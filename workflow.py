import asyncio

from datetime import timedelta
from ipaddress import IPv4Network

from temporalio import workflow

# Import activity, passing it through the sandbox without reloading the module
with workflow.unsafe.imports_passed_through():
    from activities import AWSInfrastructureActivities
    from shared import (
        AWSInfrastructureWorkflowInput, AWSInfrastructureWorkflowOutput,
        VPCInfoInput, VPCInfoOutput, 
        SubnetInfoInput, SubnetInfoOutput, 
        EC2InfoInput, EC2InfoOutput
    )


@workflow.defn
class AWSVPCandEC2Workflow:

    workflow.logger.workflow_info_on_message = False
    #workflow.logger.workflow_info_on_extra = False

    @workflow.run
    async def run(self, input: AWSInfrastructureWorkflowInput) -> AWSInfrastructureWorkflowOutput:
        workflow.logger.info(f"AWS VPC and EC2 Workflow started with input: {input}")   
        vpc_input_info: VPCInfoInput = VPCInfoInput(
            region=input.region,
            cidr_block=input.cidr_block)

        #create the VPC and retrieve the VPC ID
        vpc_output_info: VPCInfoOutput = await workflow.execute_activity_method(
            AWSInfrastructureActivities.create_vpc,
            vpc_input_info,
            start_to_close_timeout=timedelta(seconds=20)
        )

        #pause to watch progress in the Temporal Web UI.
        await asyncio.sleep(5)

        #create the subnets and retrieve the subnet ID
        #need to split the VPC CIDR block into smaller CIDR blocks for the subnets
        split_prefix: int = IPv4Network(input.cidr_block).prefixlen + 1
        subnet_cidr_blocks: list[IPv4Network] = list(IPv4Network(input.cidr_block).subnets(new_prefix=split_prefix))
        subnets: list[SubnetInfoOutput] = []
        for subnet_cidr in subnet_cidr_blocks:
            subnet_input_info = SubnetInfoInput(
                vpc_id=vpc_output_info.vpc_id,
                region=input.region,
                cidr_block=str(subnet_cidr),
                availability_zone="us-east-1a"
            )

            subnet_output_info = await workflow.execute_activity_method(
                AWSInfrastructureActivities.create_subnet,
                subnet_input_info,
                start_to_close_timeout=timedelta(seconds=20)
            )
            subnets.append(subnet_output_info)

        #pause to watch progress in the Temporal Web UI.
        await asyncio.sleep(5)

        #create the EC2 instance in the first subnet and retrieve the instance ID and public IP
        ec2_input_info: EC2InfoInput = EC2InfoInput(
            region=input.region,
            instance_type=input.instance_type,
            subnet_id=subnets[0].subnet_id,
            operating_system=input.operating_system
        )
        ec2_output_info: EC2InfoOutput = await workflow.execute_activity_method(
            AWSInfrastructureActivities.create_ec2_instance,
            ec2_input_info,
            start_to_close_timeout=timedelta(seconds=300)
        )

        return AWSInfrastructureWorkflowOutput(
            region=input.region,
            vpc_id=vpc_output_info.vpc_id,
            subnet_ids=[subnet.subnet_id for subnet in subnets],
            instance_id=ec2_output_info.instance_id,
            instance_ip=ec2_output_info.public_ip
        )
