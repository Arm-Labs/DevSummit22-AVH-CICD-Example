# Arm Virtual Hardware in CI/CD workflows

This example shows how to use 3rd party hardware AVH to automatically test and deploy applications using GitHub Actions. On each
commit and pull request a test job is started using a virtual STM32U5 IoT Discovery Kit, which confirms the firmware is functional. Another GHA job is available to deploy the firmware to real hardware using Amazon AWS IoT firmware update service.

## GitHub Action workflows

Both flows build the application using our experimental cloud build service. It's not publicly available yet, but if you're trying to reproduce this setup you can simply use GitHub Action to build the code. Stay tuned for more information about our build service. In the meantime you can have a look at [Keil Studio Cloud](https://www.keil.arm.com/) a modern embedded IDE in the cloud.

### Test flow

Test flow runs on pull requests and direct code pushes to _main_ branch. It builds the AWS OTA example application, creates an AWS IoT Thing and runs the application using AVH service on a virtual STM32U5 Discovery kit.

Currently we are only checking if the virtual board boots correctly and whether the firmware version matches the source code, but it would be trivial to extend the checks to confirm successful cloud connection.

<img width="1082" alt="GitHub Actions AVH based test flow" src="https://user-images.githubusercontent.com/107253/197732292-9707b1f3-76d9-498f-b99a-d9d006b5cb7f.png">

### Deploy flow

Deploy flow is triggered manually by the user. It builds the AWS OTA example application and starts an AWS IoT update job. It requires a pre-configured and connected _IoT Thing_ that will be target of the update job.

Currently this flow ends when the update job is created, it doesn't wait to validate the firmware update result, but it should be relatively easy to add such a check.

<img width="1045" alt="GitHub Actions deploy flow using AWS IoT firmware update service" src="https://user-images.githubusercontent.com/107253/197732430-e4a9cb0d-4ce2-42c3-830e-f95a466918d0.png">


## Arm TrustZone for Cortex-M - Applications

[**Arm TrustZone for Cortex-M**](https://www.arm.com/technologies/trustzone-for-cortex-m) enables System-Wide Security for IoT Devices. The technology reduces the potential for attack by isolating the critical security firmware, assets and private information from the rest of the application.

This repository contains example applications that leverage this technology.  The architecture of the application is shown in the diagram below.

![Architecture](https://user-images.githubusercontent.com/8268058/174683600-c28fa6ee-16f6-4e4b-8259-282eb62a9b9a.png)

**Applications Parts:**
- [AWS Demos](app/AWS/README.md) - For the CI/CD flow example only the OTA demo is used
- Secure second stage bootloader (BL2): [Prebuilt BL2](bl2/README.md)
- Trusted Firmware (TF-M): [Prebuilt TF-M](tfm/README.md)

## Prerequisites

* Access to 3rd party hardware AVH service
* AWS account with IAM user access
* GitHub repository with Actions enabled
* Keil Studio Cloud account and a corresponding access token
* STM32U5 IoT Discovery Kit hardware

## Set-up

### GitHub

Enable following GitHub actions workflows in the repository: [.github/workflows](.github/workflows).

You'll need to set following repository action secrets:

*Prerequisites*

* `KSC_ACCESS_TOKEN` - Access token for Keil Studio Cloud
* `GIT_ACCESS_TOKEN` - Access token for GitHub with repository access rights (your GitHub account needs to have access to Arm-Debug/solar-build-and-run which currently is private)
* `AVH_ACCESS_TOKEN` - Access token for AVH 3rd party hardware service
* `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` - AWS IAM user credentials

*Created during the setup*

* `AVH_MQTT_ENDPOINT` - A MQTT endpoint address, you can find it in your AWS IoT Core settings
* `AVH_OTA_KEY` - AWS OTA Singer public key
* `OTA_SIGNING_PROFILE` - Signing profile name
* `OTA_S3_BUCKET` - AWS S3 bucket name used for firmware storage during OTA
* `OTA_TARGET` - AWS IoT Thing ARN of your device
* `OTA_ROLE_ARN` - ARN of the AWS OTA service role
* `OTA_POLICY` - Name of OTA policy attached to certificate

### Arm Virtual Hardware

Set `AVH_ACCESS_TOKEN` GitHub secret to the access token for AVH 3rd party hardware service. You can request access to closed beta [here](https://avh.arm.com)

No extra setup is needed, the test flow automatically takes care of creating virtual environment, flashing the firmware, running the test and cleaning up.

### AWS

*For the test workflow*

* Set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` GitHub secrets to your IAM user credentials. You can create and manage IAM users in IAM service in AWS Console.
* Set the `AVH_MQTT_ENDPOINT` GitHub Secret to your AWS IoT Core MQTT endpoint address. You can determine the endpoint for your AWS account with the `aws iot describe-endpoint` command (if you have the AWS client installed and configured) or you can find it on the Settings page of the AWS IoT Core console.
* Create AWS IoT code signing profile and key pair. Set the signing profile name in `OTA_SIGNING_PROFILE` and public key in `AVH_OTA_KEY` GitHub secrets. Follow the steps in [here](app/AWS/OTA.md#setup-code-signing-key) to create and setup the keys. The secret has to be set as:
```
-----BEGIN PUBLIC KEY-----
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=
-----END PUBLIC KEY-----
```
* Create a OTA policy for device certificate and set `OTA_POLICY` GitHub secret to the policy name. You can create the policy using _AWS Web console_ or use the following command (changing the name to a desired one). *Note: This policy allows very broad access to AWS IoT MQTT APIs. Use a more restrictive policy for any production environments.*
```
aws iot create-policy \
    --policy-name="XXXXXXXXXXX" \
    --policy-document="{ \"Version\": \"2012-10-17\", \"Statement\": [{\"Effect\": \"Allow\", \"Action\": \"iot:*\", \"Resource\": \"*\"}]}"
```

*For the deploy workflow*

* Start with the _test workflow_ setup.
* Follow [these steps](app/AWS/OTA.md#setup-ota-s3-bucket-service-role-and-policies-in-aws) to create the S3 bucket and setup access to it. Set `OTA_S3_BUCKET` to point to your S3 bucket and `OTA_ROLE_ARN` to OTA service role ARN (which looks like this `arn:aws:iam::your_account_id:role/your_role_name`).
* Continue to the [Hardware setup](#hardware).

### Hardware

You'll need to setup a STM32U5 Discovery kit (B-U585I-IOT02A) hardware board so that it can connect to AWS IoT service and wait for update.

Provision the STM32U5 hardware board following [these instructions](app/AWS/Provision.md). Set `OTA_TARGET` to ARN of the _AWS IoT Thing_ you created during the provisioning of the board. _Thing_ ARN has the following format `arn:aws:iot:<region>:<account id>:thing/<thing name>`, you can copy it from your _Thing_ page in _AWS Console_.
