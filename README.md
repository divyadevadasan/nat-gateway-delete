# AWS Resource Optimization - Delete Unused NAT Gateways and EIP

## Use Case

NAT Gateway are EC2 instances by itself managed by AWS internally to allow EC2 instances in a private subnet to send outbound network traffic to the internet. 

Every NAT Gateway has an Elastic IP associated with it. Unused NAT Gateways and EIPs add un-necessary cost to the customer.

As a part of the resource utilization project, customers can opt to deploy a solution to auto delete unused NAT Gateways and EIPs which did not have any network traffic for 14 days.

**Environments Supported**
* AMS Accelerate
* AMS Advanced

**AWS Services used**
1. Lambda Function
2. Lambda Execution Role (accelerate accounts)
3. CWEvents

**CloudFormation Parameters Used**
1. Lambda function name "ams_nat_eip_auto_delete".
2. Lambda function zip filename "delete_nat_gateway.zip".
3. Lambda Execution role-name "ams_nat_eip_delete_role"

## Solution Architecture

<img width="685" alt="image" src="https://user-images.githubusercontent.com/116830841/198347348-e01dc628-3d38-4ad5-babc-6a2af139007f.png">


1. Lambda function is periodically triggered by CWEvents every 15 days. 
2. Lambda loops through all the regions in the account and identifies active NAT Gateways. It filters CW namespace "AWS/NATGateway" for metric "BytesOutToDestination" for all the active NAT Gateways. 
3. Lambda function logic works as follows:
    a. If the "BytesOutToDestination" metric statistics of the NAT Gateway sums to "0" and if the environment variable tag Retain is set to "False", the NAT Gateway is considered as unused and deleted along with its Elastic IP. 
    b. If the "BytesOutToDestination" metric statistics of the NAT Gateway sums to "0" and if the environment variable tag Retain is set to "True", the unused NAT Gateway is retained and customer receives a notification to delete unused NAT Gateways. 
    c. If the "BytesOutToDestination" metric statistics of the NAT Gateway sums to any value > "0", the Lambda function ignores and loops through other regions. 

**Deployment Process** 
The following are the ops onboarding steps for both Advanced and Accelerate accounts. 

## Accelerate Accounts:

#### Customer Onboarding Steps:
1. Raise a SR to deploy the solution into the account and provide the S3 bucket name to deploy the lambda zip file and CF stack template "delete_nat_gateway_template_accelerate.json". 
2. Copy the object URL of template "delete_nat_gateway_template_accelerate.json".
3. Open the AWS CloudFormation console at `https://console.aws.amazon.com/cloudformation`
4. Choose Create Stack. In the Specify template section, select Amazon S3 URL option and specify a URL to the template in S3.
5. Under Parameters, retain the default values. 
6. Enter stack name as "amspattern-delete-nat-gateway" and deploy the stack.

#### CloudFormation Stack-set deployment (optionally deployed by customer):
1. Upload the Lambda zip file "delete_nat_gateway.zip" and CF stack template "delete_nat_gateway_template_accelerate.json" to S3. 
2. To fetch the Organization ID from AWS Organizations Console:
    - Sign in to the AWS Organizations console
    - Navigate to the Settings page. This page displays details about the organization, including the organization ID and the account name and email address assigned to the organization's management account. 
    
(or) Alternatively, via Cloudshell/awscli using the following command:
```
aws organizations describe-organization
```
3. Update the S3 bucket policy with "s3:GetObject" permission to allow CloudFormation stack-set role to read the lambda zip file. 
4. Update the s3 bucket name from `<bucket-name>` to the s3 bucket name shared by the customer via SR and `o-<org-id>` with the organization ID of customer's organization. 
```
{
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "AllowGetObject",
            "Effect": "Allow",
            "Principal": ",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::bucket-name/delete_nat_gateway.zip",
            "Condition": {
                "StringEquals": {
                    "aws:PrincipalOrgID": "o-<org-id>"
                }
            }
        }
    ]
}
```
4. Navigate to the CloudFormation's Stack-set console. Create StackSet with the following parameters:
    - Permissions: Service-managed permissions
    - Upload the S3 template URL: `https://<s3-bucket>.s3.amazonaws.com/delete_nat_gateway_template_accelerate.json`
    - StackSet Name: "amspattern-nat-gateway-delete"
    - In Configure StackSet options, retain all the default values and update the S3 bucket parameter with the `<s3-bucket>` name.
    - In Set deployment options, select the following configuration:
        Add stacks to stack set: Deploy new stacks
        Deployment targets: Deploy to organization
        Specify regions: Specific the list of regions.
    - Click Submit and create Stack. 

#### Ops Onboarding Steps:
Upload the lambda zip file and CF template to the S3 bucket and share the S3 URLs with the customer via SR.

## Advanced Accounts:

#### Customer input:
Requires an RFC from the customer to deploy the solution into the account.

#### Ops onboarding steps:
1. AMS Ops will upload the Lambda zip file and CF stack template "delete_nat_gateway_template_advanced.json" to `mc-a<account-id>-internal-<region>`
2. Create a CR to deploy "ams-nat-auto-delete-role" (for advanced accounts).
3. Navigate to S3 bucket `mc-a<account-id>-internal-<region>`. Copy the object URL of template "delete_nat_gateway_template_advanced.json".
4. Navigate to CF console and create a stack using the S3 bucket template. 
5. Under Parameters, retain the default values. 
6. Enter stack name as "amspattern-delete-nat-gateway" and deploy the stack.

#### CloudFormation Stack-set deployment (optionally deployed by operations based on customer request):
1. Upload the Lambda zip file "delete_nat_gateway.zip" and CF stack template "delete_nat_gateway_template_advanced.json" to S3 bucket `mc-a<account-id>-internal-<region>`. 
2. To fetch the Organization ID from AWS Organizations Console:
    - Sign in to the AWS Organizations console
    - Navigate to the Settings page. This page displays details about the organization, including the organization ID and the account name and email address assigned to the organization's management account.

(or) Alternatively, via Cloudshell/awscli using the following command:

```
aws organizations describe-organization
```

3. Update the S3 bucket policy with "s3:GetObject" permission to allow CloudFormation stack-set role to read the cloudformation template and lambda zip file. 
4. Update the s3 bucket name from `mc-a<account-id>-internal-<region>` to the s3 bucket name shared by the customer via SR and `o-<org-id>` with the organization ID of customer's organization. 
```
{
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "AllowGetObject",
            "Effect": "Allow",
            "Principal": ",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::mc-a<account-id>-internal-<region>/delete_nat_gateway.zip",
            "Condition": {
                "StringEquals": {
                    "aws:PrincipalOrgID": "o-<org-id>"
                }
            }
        }
    ]
}
```
5. Navigate to the CloudFormation's StackSet console. Create StackSet with the following parameters:
    - Permissions: Service-managed permissions
    - Upload the S3 template URL: `https://mc-a<account-id>-internal-<region>.s3.amazonaws.com/delete_nat_gateway_template_accelerate.json`
    - StackSet Name: "amspattern-nat-gateway-delete"
    - In Configure StackSet options, retain all the default values and update the S3 bucket parameter with the `<s3-bucket>` name.
    - In Set deployment options, select the following configuration:
        Add stacks to stack set: Deploy new stacks
        Deployment targets: Deploy to organization
        Specify regions: Specific the list of regions.
    - Click Submit and create Stack. 

### Documentation:
* [How to find the org-id](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_details.html#orgs_view_ou)
* [How to create a stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html)
* [Creating a service request on Accelerate](https://docs.aws.amazon.com/managedservices/latest/accelerate-guide/creating-a-sr.html)
