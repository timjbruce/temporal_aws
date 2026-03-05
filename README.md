# AWS Infrastructure with Temporal

This project deploys base AWS networking (VPC, Subnets) and compute infrastructure (EC2) using Temporal to manage the workflow.

## Usage

`python starter.py <region> <cidr_block> <instance_type> <os>`

- `region`: AWS region to deploy the infrastructure. For example, us-east-1.

- `cidr_block`: An IPv4 CIDR block to use for the VPC setup. The block will be evenly divided across your subnets.

** Note: For this implementation, 2 public subnets will be created given the CIDR for the VPC. No Internet Gateways or NAT Gateways will be built at this time. **

- `instance_type`: AWS Instance Type and Size, in the format of instance_type.size (e.g. t2.small).

- `OS`: Operating system for instance, either windows (Windows) or amazonlinux2 (Amazon Linux 2).

### Background Tasks

A Temporal Development server needs to be running to receive these requests. To process requests, run `python worker.py`.

## AWS Support

## AWS Best Practices with Credentials

This project is currently stubbed using Moto and does not actually access your credentials. That being said, a fuller version would include the ability to create a session using credentials.

### Libraries Required

The project requires the AWS `boto3` and `botocore` libraries with `moto` to make the calls to generate the infrastructure. Use and modify with your own caution.

### Permissions

The role session needs to have permissions to list, update, create, describe, and destroy the following AWS primitives:

- VPC
- Subnet
- EC2 Instance

### Credentials File

It is recommended to use the CLI short-term credentials for use with this solution. Information about this can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-short-term.html)

## Process

### Happy Path

The process starts by loading the credentials you have specified and attempting a login to AWS using these. Once logged in, the program will deploy a new VPC first. Once the VPC is deployed, it will create the 2 public subnets. 

The EC2 instance will then be created using the latest AMI for either Windows or Amazon Linux 2.

### Unhappy Path

There are a number of issues that can occur with deploying the architecture via this pattern. All of these issues will cause the workflow to error out. In an attempt to minimize the impact of this, many of these items will be checked at the start of the workflow.

1. The credentials may be expired or invalid. 
2. The credentials may not have necessary permissions. 
3. Account limits could be reached for VPCs, Internet Gateways, or EC2 instances.
4. The CIDR block could be invalid.
5. An issue could occur with AWS API calls during the process.

## Future Improvements

1. Generate Private Subnets
2. Add Internet Gateway to the VPC
3. Add NAT Gateway to the VPC
4. Create roles that can be attached to the instances
5. Add Security Groups to the instances, locked down to appropriate OS ports for RDP and SSH
6. Updating of Route Tables for IGW and NAT GW.
7. Autoscaling Group support
8. Save state to databases, enable reverting to prior states
9. Enabling updates
10. Allowing specifications of subnet CIDR ranges
11. Add lookups to AWS for Regions, AZs, AMIs
12. Pre-check on Account for limits
13. Add public IP to the instance request