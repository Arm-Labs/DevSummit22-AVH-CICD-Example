# Arm Virtual Hardware in CI/CD workflows

This demo shows how to use 3rd party hardware AVH to automatically test and deploy application using GitHub Actions. On each
commit and pull request a test job is started using a virtual STM32U5 IoT Discovery Kit, which confirms the firmware is functional. Another GHA job is available to deploy the firmware to real hardware using Amazon IoT firmware update service.

## Arm TrustZone for Cortex-M - Demo Applications

[**Arm TrustZone for Cortex-M**](https://www.arm.com/technologies/trustzone-for-cortex-m) enables System-Wide Security for IoT Devices. The technology reduces the potential for attack by isolating the critical security firmware, assets and private information from the rest of the application.

This repository contains example applications that leverage this technology.  The architecture of the application is shown in the diagram below.

![Architecture](https://user-images.githubusercontent.com/8268058/174683600-c28fa6ee-16f6-4e4b-8259-282eb62a9b9a.png)

**Applications Parts:**
- [AWS Demos](app/AWS/README.md) - For the CI/CD flow only the OTA demo is used
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
* `AVH_CERT` - Virtual device self-signed certificate

### AWS

### Hardware

You'll need to follow the demo application documentation to setup and provision the hardware board. Follow the docs available [here](AWS#over-the-air-updates-via-mqtt-demo) for `Over-the-air updates via MQTT Demo` on B-U585I-IOT02A board.

At the end of the setup you need to have:

* Board booting to AWS OTA application, connecting to the cloud and polling for updates
* AWS IoT Core Thing setup according to the guide above
* Following GitHub secrets set:
  * `AVH_MQTT_ENDPOINT` - A MQTT endpoint address
  * `AVH_OTA_KEY` - AWS OTA Singer public key
  * `OTA_SIGNING_PROFILE` - Signing profile name
  * `OTA_S3_BUCKET` - AWS S3 bucket name used for firmware storage during OTA
  * `OTA_TARGET` - AWS IoT Thing ARN of your device
  * `OTA_POLICY` - Name of OTA policy attached to certificate
  * `OTA_ROLE_ARN` - ARN of the AWS OTA service role

