# Arm Virtual Hardware in CI/CD workflow demo

This demo shows how to use 3rd party hardware AVH to automatically test and deploy application using GitHub Actions. On each
commit and pull request a test job is started using a virtual STM32U5 IoT Discovery Kit, which confirms the firmware is functional. Another GHA job is available to deploy the firmware to real hardware using Amazon IoT firmware update service.

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

* `AVH_OTA_KEY` - AWS OTA Singer public key
* `OTA_SIGNING_PROFILE` - Signing profile name
* `OTA_S3_BUCKET` - AWS S3 bucket name used for firmware storage during OTA
* `OTA_TARGET` - AWS IoT Thing ARN of your device
* `OTA_ROLE_ARN` - ARN of the AWS OTA service role
* `AVH_CERT` - Virtual device self-signed certificate

### AWS

### AVH

### Hardware

## Arm TrustZone for Cortex-M - Demo Applications

[**Arm TrustZone for Cortex-M**](https://www.arm.com/technologies/trustzone-for-cortex-m) enables System-Wide Security for IoT Devices. The technology reduces the potential for attack by isolating the critical security firmware, assets and private information from the rest of the application.

This repository contains example applications that leverage this technology.  The architecture of the application is shown in the diagram below.

![Architecture](https://user-images.githubusercontent.com/8268058/174683600-c28fa6ee-16f6-4e4b-8259-282eb62a9b9a.png)

**Applications Parts:**
- [AWS Demos](app/AWS/README.md)
- Secure second stage bootloader (BL2): [Prebuilt BL2](bl2/README.md) for various platforms
- Trusted Firmware (TF-M): [Prebuilt TF-M](tfm/README.md) for various platforms

The various AWS Demos implement for example Over-the-Air (OTA) Firmware Update. The process is shown in the following video.

[![OTA Demo on STM32U5](https://user-images.githubusercontent.com/8268058/174682995-313ee4b7-4afd-438e-aa09-9cd754696bc1.png)
](https://armkeil.blob.core.windows.net/developer/Files/videos/KeilMDK/OTA_Update_U5.mp4)
