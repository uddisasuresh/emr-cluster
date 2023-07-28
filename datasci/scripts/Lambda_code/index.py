import boto3
import json
import os

emr = boto3.client('emr')
cloudwatch = boto3.client('cloudwatch')
s3 = boto3.resource('s3')
cloudwatchRes = boto3.resource('cloudwatch')
metric = cloudwatchRes.Metric('namespace', 'name')
paginator = cloudwatch.get_paginator('list_metrics')
paginator2 = emr.get_paginator('list_instances')

def handler(event, context):
    # clusterName = event.get("detail").get("name")
    clusterId = event['detail']['clusterId']
    nameResponse = emr.describe_cluster(ClusterId=clusterId)
    clusterName = nameResponse['Cluster']['Name']
    clusterName=clusterName.split('-')[0]
    name = clusterName+'-'+clusterId
    state = ["TERMINATING","TERMINATED","TERMINATED_WITH_ERRORS"]
    if (event['detail-type']=="EMR Cluster State Change" and event['detail']['state'] in state):
        print("Cluster is terminating/terminated")
        response = cloudwatch.describe_alarms(AlarmNamePrefix = name)
        AlarmName=[]
        if response['MetricAlarms']:
            for x in response['MetricAlarms']:
                AlarmName.append(x['AlarmName'])
        cloudwatch.delete_alarms(AlarmNames=AlarmName)
        cloudwatch.delete_dashboards(DashboardNames=[name])
    elif (event['detail-type']=="EMR Cluster State Change" and event['detail']['state']=="STARTING"):
        resp = emr.list_clusters(ClusterStates=['TERMINATED'])
        print("Cluster is starting")
        AlarmName = []
        Dashboards = []
        cleanupDashboard = []
        allDashboard = cloudwatch.list_dashboards()
        for termDash in allDashboard['DashboardEntries']:
            Dashboards.append(termDash['DashboardName'])
        for cleanup in resp['Clusters']:
            cleanupName = cleanup['Name'] + '_' + cleanup['Id']
            print(cleanupName)
            alarmCleanup = cloudwatch.describe_alarms(AlarmNamePrefix=cleanupName)
            if alarmCleanup['MetricAlarms']:
                for x in alarmCleanup['MetricAlarms']:
                    AlarmName.append(x['AlarmName'])
            if cleanupName in Dashboards:
                cleanupDashboard.append(cleanupName)
        cloudwatch.delete_alarms(AlarmNames=AlarmName)
        cloudwatch.delete_dashboards(DashboardNames=[cleanupDashboard])
    else:
        response = emr.list_instances(ClusterId=clusterId)
        nodeDownsize=[]
        ids=[]
        for y in paginator2.paginate(ClusterId=clusterId):
            for x in y['Instances']:
                if (x['Status']['State'] != "TERMINATED"):
                    ids.append(x['Ec2InstanceId'])
        print(ids)
        if ids:
            response = cloudwatch.describe_alarms(AlarmNamePrefix=name)
            if response['MetricAlarms']:
                for x in response['MetricAlarms']:
                    if x['Dimensions']:
                        for dim in x['Dimensions']:
                            if dim['Name'] == 'InstanceId':
                                if dim['Value'] not in ids:
                                    nodeDownsize.append(dim['Value'])
            for id in ids:
                for response in paginator.paginate(Dimensions=[{'Name': 'InstanceId', 'Value': id}],
                                                   MetricName='CPUUtilization',
                                                   Namespace='AWS/EC2'):
                    if response['Metrics']:
                        for d in response['Metrics']:
                            aName = name+'-'+ id + '_CPU_Utilization'
                            print(aName)
                            metric.put_alarm(
                                AlarmName=aName,
                                ComparisonOperator='GreaterThanThreshold',
                                EvaluationPeriods=1,
                                MetricName='CPUUtilization',
                                Namespace='AWS/EC2',
                                Period=1200,
                                Statistic='Average',
                                #Threshold=85.0,
                                Threshold=int(os.environ['CPU_WARN_THRESHOLD']),
                                ActionsEnabled=True,
                                AlarmDescription='Alarm when server CPU exceeds 85%',
                                Dimensions=d['Dimensions'],
                                AlarmActions=[os.environ['ALERTACTION']]
                            )
                    if response['Metrics']:
                        for d in response['Metrics']:
                            aName = name+'-'+ id + '_AlertCPU_Utilization'
                            print(aName)
                            metric.put_alarm(
                                AlarmName=aName,
                                ComparisonOperator='GreaterThanThreshold',
                                EvaluationPeriods=1,
                                MetricName='CPUUtilization',
                                Namespace='AWS/EC2',
                                Period=900,
                                Statistic='Average',
                                #Threshold=95.0,
                                Threshold=int(os.environ['CPU_CRIT_THRESHOLD']),
                                ActionsEnabled=True,
                                AlarmDescription='Alarm when server CPU exceeds 95%',
                                Dimensions=d['Dimensions'],
                                AlarmActions=[os.environ['ALERTACTION']]
                            )        
                for response in paginator.paginate(Dimensions=[{'Name': 'InstanceId', 'Value': id}],
                                                   MetricName='DiskSpaceUtilization',
                                                   Namespace='System/Linux'):
                    if response['Metrics']:
                        for d in response['Metrics']:
                            aName = name + '-' + id + '_DiskSpaceUtilization'
                            print(aName)
                            for dim in d['Dimensions']:
                                if dim['Name'] == 'MountPath':
                                    metric.put_alarm(
                                        AlarmName=aName+dim['Value'],
                                        ComparisonOperator='GreaterThanThreshold',
                                        EvaluationPeriods=1,
                                        MetricName='DiskSpaceUtilization',
                                        Namespace='System/Linux',
                                        Period=300,
                                        Statistic='Average',
                                        #Threshold=80.0,
                                        Threshold=int(os.environ['DISK_THRESHOLD']),
                                        ActionsEnabled=True,
                                        AlarmDescription='Alarm when Disk Space exceeds 80%',
                                        Dimensions=d['Dimensions'],
                                        AlarmActions=[os.environ['ALERTACTION']]
                                    )
                    if response['Metrics']:
                        for d in response['Metrics']:
                            aName = name + '-' + id + '_Critical_DiskSpaceUtilization'
                            print(aName)
                            for dim in d['Dimensions']:
                                if dim['Name'] == 'MountPath':
                                    metric.put_alarm(
                                        AlarmName=aName+dim['Value'],
                                        ComparisonOperator='GreaterThanThreshold',
                                        EvaluationPeriods=1,
                                        MetricName='DiskSpaceUtilization',
                                        Namespace='System/Linux',
                                        Period=300,
                                        Statistic='Average',
                                        Threshold=95.0,
                                        #Threshold=int(os.environ['DISK_THRESHOLD']),
                                        ActionsEnabled=True,
                                        AlarmDescription='Alarm when Disk Space exceeds 95%',
                                        Dimensions=d['Dimensions'],
                                        AlarmActions=[os.environ['ALERTACTION']]
                                    )
                for response in paginator.paginate(Dimensions=[{'Name': 'InstanceId', 'Value': id}],
                                                   MetricName='MemoryUtilization',
                                                   Namespace='System/Linux'):
                    if response['Metrics']:
                        aName = name+'-'+ id + '_MemoryUtilization'
                        print(aName)
                        for d in response['Metrics']:
                            metric.put_alarm(
                                AlarmName=aName,
                                ComparisonOperator='GreaterThanThreshold',
                                EvaluationPeriods=1,
                                MetricName='MemoryUtilization',
                                Namespace='System/Linux',
                                Period=1200,
                                Statistic='Average',
                                #Threshold=85.0,
                                Threshold=int(os.environ['MEM_WARN_THRESHOLD']),
                                ActionsEnabled=True,
                                AlarmDescription='Alarm when Memory exceeds 85%',
                                Dimensions=d['Dimensions'],
                                AlarmActions=[os.environ['ALERTACTION']]
                            )
                    if response['Metrics']:
                        aName = name+'-'+ id + '_AlertMemoryUtilization'
                        print(aName)
                        for d in response['Metrics']:
                            metric.put_alarm(
                                AlarmName=aName,
                                ComparisonOperator='GreaterThanThreshold',
                                EvaluationPeriods=1,
                                MetricName='MemoryUtilization',
                                Namespace='System/Linux',
                                Period=900,
                                Statistic='Average',
                                #Threshold=95.0,
                                Threshold=int(os.environ['MEM_CRIT_THRESHOLD']),
                                ActionsEnabled=True,
                                AlarmDescription='Alarm when Memory exceeds 95%',
                                Dimensions=d['Dimensions'],
                                AlarmActions=[os.environ['ALERTACTION']]
                            )        
            downsized = set(nodeDownsize)
            if downsized:
                for i in downsized:
                    response = cloudwatch.describe_alarms(AlarmNamePrefix=name+'-'+i)
                    AlarmName = []
                    if response['MetricAlarms']:
                        for x in response['MetricAlarms']:
                            AlarmName.append(x['AlarmName'])
                    print(AlarmName)
                    cloudwatch.delete_alarms(AlarmNames=AlarmName)
            # cResponse = cloudwatch.get_dashboard(DashboardName=name)
            # if cResponse:
            #     data = json.load(cResponse['DashboardBody'])
            # else:
            obj = s3.Object(os.environ['BUCKET'], 'emr/bootstrap/dashboard/dashboard.json')
            data = json.load(obj.get()['Body'])
            json_object = data
            for i in range(0, len(json_object['widgets'])):
                if 'InstanceId' in json_object['widgets'][i]['properties']['metrics'][0]:
                    index = json_object['widgets'][i]['properties']['metrics'][0].index('InstanceId') + 1
                    json_object['widgets'][i]['properties']['metrics'][0][index] = ids[0]
                    json_object['widgets'][i]['properties']['metrics'] = json_object['widgets'][i]['properties']['metrics'][
                                                                         :1]
                    for j in range(1, len(ids)):
                        temp = json_object['widgets'][i]['properties']['metrics'][0][:]
                        temp[index] = ids[j]
                        json_object['widgets'][i]['properties']['metrics'].append(temp)
                elif 'JobFlowId' in json_object['widgets'][i]['properties']['metrics'][0]:
                    index = json_object['widgets'][i]['properties']['metrics'][0].index('JobFlowId') + 1
                    json_object['widgets'][i]['properties']['metrics'][0][index] = clusterId
            json_object = json.dumps(json_object, indent=4)
            cloudwatch.put_dashboard(
                DashboardName=name,
                DashboardBody=json_object
            )