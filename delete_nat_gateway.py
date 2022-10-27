import boto3
from datetime import datetime as dt
from datetime import timedelta
import io
import json
import os
import time
from tokenize import Ignore


def cw_metric(region, nat_active_id):
    #Set Log Range as last 14 days
    end_date = dt.today().isoformat(timespec='seconds')
    start_date = (dt.today() - timedelta(days=14)).isoformat(timespec='seconds')
    print("Log Range: %s to %s" % (start_date, end_date))

    #Fetch metric statistics to check metrics generated in 'BytesOutToDestination'
    cloudwatch_client = boto3.client('cloudwatch', region_name=region)
    cw_response = cloudwatch_client.get_metric_statistics(
        Namespace='AWS/NATGateway',
        MetricName='BytesOutToDestination',
        Dimensions=[
        {
            'Name': 'NatGatewayId',
            'Value': nat_active_id
        }
        ],
        StartTime=start_date,
        EndTime=end_date,
        Period=1296000,
        Statistics=[
            'Sum'
        ],
        Unit='Bytes'
    )
    for i in range(0,len(cw_response['Datapoints'])):
        if i == [] or () or None :
            Ignore  
        else: 
            metric_statistics = json.dumps(cw_response['Datapoints'][i]['Sum'], indent=4, sort_keys=True, default=int)
            return metric_statistics

def send_sns(message, subject):
    snsclient = boto3.client("sns")
    topic_arn = os.environ["SNS_ARN"]
    snsclient.publish(
        TopicArn=topic_arn, Message=message, Subject=subject)
        
def lambda_handler(event, context):
    #SNS Notification Counter
    notification = 0
    
    #Fetch all Regions
    ec2client = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2client.describe_regions()['Regions']]
    for region in regions:
        client = boto3.client('ec2', region_name=region)
        # Describe NAT Gateway to filter NAT Gateway IP 
        nat_gateway_describe = client.describe_nat_gateways()
        for i in range(len(nat_gateway_describe['NatGateways'])):
            if nat_gateway_describe['NatGateways'][i]['State'] != 'deleted':
                nat_active_id = nat_gateway_describe['NatGateways'][i]['NatGatewayId']
                nat_gateway_eip_alloc = nat_gateway_describe['NatGateways'][i]['NatGatewayAddresses'][0]['AllocationId']
                metric_statistics = cw_metric(region, nat_active_id)
                if metric_statistics == str(0.0) and os.environ['Retain'] == 'false':
                    # Delete unused NAT Gateway
                    nat_gateway_delete=client.delete_nat_gateway(
                        NatGatewayId=nat_active_id
                    )
                    print("Nat Gateway " + nat_gateway_delete['NatGatewayId'] + " has been deleted")
                    time.sleep(60)
                    describe_eip = client.describe_addresses()
                    for eip_dict in describe_eip['Addresses']:
                        if "AssociationId" not in eip_dict:
                            print(eip_dict['PublicIp'] + " doesn't have any NAT Gateways associated, releasing")
                            client.release_address(AllocationId=nat_gateway_eip_alloc)
                elif metric_statistics == str(0.0) and os.environ['Retain'] == 'true':
                    message = "To delete unused NAT Gateways in account, update lambda function's ('nat_eip_auto_delete') environment variable 'Retain' to false."
                    subject = "Unused NAT Gateways"
                    send_sns(message, subject)
                    notification += 1
                    if notification == 1:
                        break
                else:
                    pass
