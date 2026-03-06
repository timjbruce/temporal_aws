import asyncio
import sys

from shared import TASK_QUEUE_NAME, AWSInfrastructureWorkflowInput
from temporalio.client import Client
from workflow import AWSVPCandEC2Workflow
from uuid import uuid4


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233", namespace="default")

    id = str(uuid4())
    # Execute a workflow
    input: AWSInfrastructureWorkflowInput = AWSInfrastructureWorkflowInput(
        region=sys.argv[1], 
        cidr_block=sys.argv[2],
        instance_type=sys.argv[3],
        operating_system=sys.argv[4]
    )
    id = str(uuid4())
    handle = await client.start_workflow(
        AWSVPCandEC2Workflow.run,
        input,
        id=id,
        task_queue=TASK_QUEUE_NAME,
    )

    print(f"Started workflow. Workflow ID: {handle.id}, RunID {handle.result_run_id}")

    result = await handle.result()

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())