import urllib3
import boto3
import json
import os
import re
import sys
import logging
from datetime import datetime, timedelta
client = boto3.client('sns')
emr = boto3.client('emr')
ec2 = boto3.client('ec2')

def handler(event, context):
    main_function(event)
    
def main_function(event):
    print(event)
    message = event['Records'][0]['Sns']['Message']
    message = json.loads(message)
    detail = message.get('detail')
    det = str(detail)
    if(det=="None"):
        trigger = message.get("Trigger", {})
        cur_reason = trigger.get('MetricName', '')
        key=""
        var=0
        if(cur_reason == "CPUUtilization"):
            key=os.environ['CPUUTILIZATION_FILE']
        elif(cur_reason == "DiskSpaceUtilization"):
            key=os.environ['DISKSPACEUTILIZATION_FILE']
        elif(cur_reason == "MemoryUtilization"):
            key=os.environ['MEMORYUTILIZATION_FILE']
        else:
            var=1
        # print(key)
        if(var==0):
            var = email_consolidation(key)
            current_time = datetime.now() + timedelta(hours=6)
            string = str(current_time)
            encoded_string = string.encode("utf-8")
            s3 = boto3.resource("s3")
            s3.Bucket(os.environ['BUCKET']).put_object(Key=key, Body=encoded_string)
        
            
        if(var==1):
            # message = event['Records'][0]['Sns']['Message']
            subject = event['Records'][0]['Sns']['Subject']
            if "-YarnUtilization" in subject or "-HDFSUtilization" in subject :
           
                abc=subject.split("-")
                x=len(abc)
                Cluster_Id=abc[2]
                Cluster_Id="j-"+Cluster_Id
                nameResponse = emr.describe_cluster(ClusterId=Cluster_Id)
                global Cluster_Name
                Cluster_Name = nameResponse['Cluster']['Name']

                Alarm_Description = message['AlarmDescription']
                val = int(re.search(r'\d+', Alarm_Description).group())
                threshold_val = message['Trigger']['Threshold']
                print(threshold_val)
                type_of_alert = ""
                if(threshold_val<=int(os.environ['THRESHOLD_VALUE'])):
                    type_of_alert = "Warning"
                else:
                    type_of_alert = "Alert"
              #  final_message="Type of Alert    :  " + type_of_alert + "\nDescription        :  " + Alarm_Description
                final_message="Type of Alert : " + type_of_alert + "\nCluster Name : " + Cluster_Name + "\nCluster Id : " + Cluster_Id + "\nDescription : " + Alarm_Description
              
            else:   
               abc=subject.split("j-")
               x=len(abc)
               r=abc[1]
               xyz = r.split("-i")
               Cluster_Id=xyz[0]
               Cluster_Id="j-"+Cluster_Id
               nameResponse = emr.describe_cluster(ClusterId=Cluster_Id)
               Cluster_Name = nameResponse['Cluster']['Name']
               ID = xyz[1]
               Instance_Id = ID.split('_')[0]
               Instance_Id = "i" + Instance_Id
            
               reservations = ec2.describe_instances(InstanceIds=[Instance_Id]).get("Reservations")
               for reservation in reservations:
                  for instance in reservation['Instances']:
                    PrivateIpAddress = instance.get("PrivateIpAddress")
                    # tag = instance.get("Tags")
                    # y=len(tag)
                    # for num in range(y):
                    #     node = tag[num].get("Value")
                    #     if(node=="CORE" or node=="TASK" or node=="MASTER"):
                    #         break;
                    
                    break;
                  break;
            
               Alarm_Description = message['AlarmDescription']
               val = int(re.search(r'\d+', Alarm_Description).group())
               threshold_val = message['Trigger']['Threshold']
               type_of_alert = ""
            
               if(threshold_val<=int(os.environ['THRESHOLD_VALUE'])):
                 type_of_alert = "Warning"
               else:
                 type_of_alert = "Alert"
        
               instance_group = emr.list_instance_groups(ClusterId=Cluster_Id)
               n = instance_group['InstanceGroups'][0]
               # node = n.get('InstanceGroupType')
        
               final_message="Type of Alert : " + type_of_alert + "\nCluster Name : " + Cluster_Name + "\nCluster Id : " + Cluster_Id + "\nInstance Name : " + Instance_Id + "\nDescription : " + Alarm_Description + "\nPrivate IP Address : " + PrivateIpAddress
               
            
            msg_SNS(final_message)
        
            trigger = message.get("Trigger", {})
            if(type_of_alert == "Alert"):
                
                for record in event.get("Records", []):
                    alarm_details = record.get("Sns", {})
                    message = json.loads(alarm_details.get("Message", "{}"))
                    
                
                    dimensions = trigger.get("Dimensions", [])
                    dimension = ""
                    if dimensions is not None and len(dimensions) > 0:
                        dimension = f"{dimensions[0].get('name', '')}={dimensions[0].get('value', '')}"
                
                    description = message.get("AlarmDescription", "")
                current_time = datetime.now() + timedelta(hours=6)
                string = str(current_time)
                cur_time=string.split('.')[0]
                
                payload = {
                    "instance": f"AWS: {trigger.get('Namespace', '')}/{trigger.get('MetricName', '')}/{dimension} Time: {cur_time}",
                    "short_description": f"{subject}",
                    "ci": os.environ['APPLICATION_CI'],
                    "description": f"{Cluster_Name}, {Cluster_Id} is in alert situation as {Alarm_Description}.",
                    "event_type": "aws-alarm",
                    "reported_by": os.environ['REPORTED_BY'],
                    "uai": os.environ['UAI']
                }
                print (payload)
                snow_integeration(payload)
                
    else:
        
        Cluster_Name = detail.get('name')
        Cluster_Id = detail.get('clusterId')
        state = detail.get('state')
        final_message="Type of Alert :  Cluster State Change"  + "\nState :  " + state + "\nCluster Name :  " + Cluster_Name + "\nCluster Id :  " + Cluster_Id
    
        if(state=="STARTING"):
            msg_SNS(final_message)
        
        elif(state=="TERMINATED_WITH_ERRORS"):
            nameResponse = emr.describe_cluster(ClusterId=Cluster_Id)
            temp = nameResponse['Cluster']
            master_DNS = temp.get('MasterPublicDnsName')
            
            final_message_1 = "Type of Alert :  Cluster State Change"  +  "\nState :  " + state + "\nCluster Name :  " + Cluster_Name + "\nCluster Id :  " + Cluster_Id + "\nMasterPublic DNS Name :  " + master_DNS
            
            msg_SNS(final_message_1)
            
            current_time = datetime.now() + timedelta(hours=6)
            string = str(current_time)
            cur_time=string.split('.')[0]
            payload = {
                "instance": f"AWS: System/Linux Time: {cur_time}",
                "short_description": f"Cluster with Master DNS: {master_DNS} terminated",
                "ci": os.environ['APPLICATION_CI'],
                "description": f"{Cluster_Name}, {Cluster_Id} got terminated.",
                "event_type": "aws-alarm",
                "reported_by": os.environ['REPORTED_BY'],
                "uai": os.environ['UAI']
            }
            print(payload)
            snow_integeration(payload)
        elif(state=="TERMINATED"):
            nameResponse = emr.describe_cluster(ClusterId=Cluster_Id)
            temp = nameResponse['Cluster']
            master_DNS = temp.get('MasterPublicDnsName')
            
            final_message_1 = "Type of Alert :  Cluster State Change"  +  "\nState :  " + state + "\nCluster Name :  " + Cluster_Name + "\nCluster Id :  " + Cluster_Id + "\nMasterPublic DNS Name :  " + master_DNS
            
            msg_SNS(final_message_1)
  
def email_consolidation(key):
    current_time = datetime.now() + timedelta(hours=6)
    string = str(current_time)
    encoded_string = string.encode("utf-8")
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=os.environ['BUCKET'], Key=key)
        content = response['Body'].read().decode('utf-8')
                
        s3_path =  key
                
        if(content == ""):
            var=1
            return var
        else:
            prev_date=content.split(' ')[0]
            curr_date = string.split(' ')[0]
            var = 0
            if(prev_date != curr_date):
                var = 1
                return var
                
            pre_hour = content.split(' ')[1].split('.')[0].split(':')[0]
            cur_hour = string.split(' ')[1].split('.')[0].split(':')[0]
            prev_hour = int(pre_hour)
            curr_hour = int(cur_hour)
                    
            if(curr_hour-prev_hour>1):
                var = 1
                return var
                    
            pre_min = content.split(' ')[1].split('.')[0].split(':')[1]
            cur_min = string.split(' ')[1].split('.')[0].split(':')[1]
            prev_min = int(pre_min)
            curr_min = int(cur_min)
                    
            if(curr_hour - prev_hour ==1):
                curr_min+=60
                    
            if(curr_min - prev_min > int(os.environ['TIME_DIFF'])):
                var = 1
                
        return var   
    except:
        var=1
        current_time = datetime.now() + timedelta(hours=6)
        string = str(current_time)
        encoded_string = string.encode("utf-8")
        s3 = boto3.resource("s3")
        s3.Bucket(os.environ['BUCKET']).put_object(Key=key, Body=encoded_string)
        return var

def snow_integeration(payload):
    if "SUPPORT_GROUP" in os.environ:
        payload["assignment_group"] = os.environ["SUPPORT_GROUP"]
            
    http = urllib3.PoolManager()
    headers = urllib3.make_headers(basic_auth=f"{os.environ['EVENT_MANAGEMENT_USER']}:{os.environ['EVENT_MANAGEMENT_PASSWORD']}")
    r = http.request('POST', os.environ['EVENT_MANAGEMENT_URL'],
                      headers=headers,
                      timeout=30,
                      body=json.dumps(payload))
    print(r.data)

def msg_SNS(messages):
    ALERTACTION = os.environ['ALERTACTION']
    env = ALERTACTION.split("-")[-4]
    client.publish(
        TopicArn=os.environ['ALERTACTION'],
        Message= messages,
        Subject=f'AWS Notifiactions {Cluster_Name} {env}',
    )