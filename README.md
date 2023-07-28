# dos-emr
Centralized repository for building EMR clusters in DOS.


This can be used to spin up multiple EMR clusters, each with their own configuration. This is accomplished via the [Include::Transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html) in CloudFormation.



***Note:*** As of August 2020, 'template-v2.yaml' is the preferred template to use for new clusters. This can be done by specifying the 'Template=template-v2.yaml' parameter when creating the DOS CICD pipeline.


See the [dos-cicd-setup](https://github.build.ge.com/AviationDAAS/dos-cicd-setup/blob/master/README.md) repo for additional documentation specific to creating EMR clusters via CICD.


**NOTE TO DEVELOPERS**


If a new team/role is created and would like to use this repo, please note that the buildspec.yaml expects a directory to exist which may contain bootstrap scripts for the product. It will take the form of *{app-prefix}/scripts*. The build will fail if the directory is not found. Since this is a shared repo, do not remove this line from the buildspec. Rather, create the directory in the repo, even if you currently have no scripts to add.
