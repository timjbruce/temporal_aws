import asyncio
import boto3
import logging
import os

from concurrent.futures import ThreadPoolExecutor # Needed for Boto3/Moto
from moto import mock_aws
from temporalio.client import Client
from temporalio.worker import Worker

from shared import TASK_QUEUE_NAME
from activities import AWSInfrastructureActivities
from workflow import AWSVPCandEC2Workflow

def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


async def main():
    logging.basicConfig(level=logging.INFO)

    client = await Client.connect("localhost:7233", namespace="default")

    # pass the boto3 client session to the activities class so that it can make API calls to AWS
    with mock_aws():
        session = boto3.Session()
        activities = AWSInfrastructureActivities(session)

        worker = Worker(
            client,
            task_queue=TASK_QUEUE_NAME,
            workflows=[AWSVPCandEC2Workflow],
            activities=[activities.create_vpc, 
                        activities.create_subnet,
                        activities.create_ec2_instance],
            activity_executor=ThreadPoolExecutor(max_workers=10)
        )
        logging.info(f"Starting the worker....{client.identity}")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
