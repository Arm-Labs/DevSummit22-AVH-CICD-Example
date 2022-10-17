import asyncio
from distutils.log import error
import os
from websockets import client as ws
import sys
import avh_api_async as AvhAPI
from pprint import pprint
import ssl
import time
import re
import boto3

if len(sys.argv) < 6 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
  print('Usage: %s <ApiToken> <mqttEndpoint> <certPolicy> <SignerKey> <expectedVersion> [fmwFile [vmName]', sys.argv[0])
  exit(-1)

apiEndpoint = 'https://app.avh.arm.com/api'
vmName = 'DevSummit22-demo'
thingName = 'DevSummit22-demo-{}'.format(int(time.time()))
fmwFile = os.path.join(sys.path[0], '../target/b_u585i_iot02a/image/firmware')

apiToken = sys.argv[1]
mqttEndpoint = sys.argv[2]
certPolicy = sys.argv[3]
ota_signer_key = sys.argv[4]
version = sys.argv[5]

if len(sys.argv) > 6:
  fmwFile = sys.argv[6]
if len(sys.argv) > 7:
  vmName = sys.argv[7]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

async def waitForState(api_instance, instance, state):
  instanceState = await api_instance.v1_get_instance_state(instance.id)
  while (instanceState != state):
    if (instanceState == 'error'):
      raise Exception('VM entered error state')
    await asyncio.sleep(1)
    instanceState = await api_instance.v1_get_instance_state(instance.id)

async def check_version(console, version):
  done = False
  text = ''
  async for message in console:
    if done:
      break

    text += message.decode('utf-8')
    while '\n' in text:
      offset = text.find('\n')
      line, text = text[:offset], text[offset+1:]

      match = re.search(r'OTA over MQTT demo, Application version ([0-9\.]+)', line)
      if (match):
        if (match.group(1) == version):
          print('Test PASSED: version {}'.format(version))
          done = True
          break
        else:
          print('Test FAILED: version {} expected {}'.format(match.group(1), version))
          raise Exception('Test FAILED: Version mismatch')

async def wait_for_pattern(console, pattern):
  text = ''
  match = None

  print("Waiting for pattern: {}".format(pattern))
  async for message in console:
    text += message.decode('utf-8')
    while '\n' in text:
      offset = text.find('\n')
      line, text = text[:offset], text[offset+1:]

      match = re.search(pattern, line)
      if (match):
        print("Done")
        return match

async def createSTM32U5(api_instance, vmName):
  print('Finding DevSummit22-demo instance...')
  api_response = await api_instance.v1_get_instances(name=vmName)
  pprint(api_response)
  if len(api_response) != 1:
    raise Exception('Failed to find vm instance')
  instance = api_response[0]

  print('Setting the VM to use the demo image: {}'.format(fmwFile))
  api_response = await api_instance.v1_create_image('fwbinary', 'plain', 
    name=os.path.basename(fmwFile),
    instance=instance.id,
    file=fmwFile
  )
  pprint(api_response)

  print('Resetting VM to use the new software')
  api_response = await api_instance.v1_reboot_instance(instance.id)

  print('Waiting for VM to finish resetting...')
  await waitForState(api_instance, instance, 'on')
  print('done')

  return instance

async def captureDeviceCert(console):
  done = False
  capture = False
  cert = ''
  text = ''
  async for message in console:
    if done:
      break

    text += message.decode('utf-8')
    while '\n' in text:
      offset = text.find('\n')
      line, text = text[:offset], text[offset+1:]

      if '-----BEGIN CERTIFICATE-----' in line:
        capture = True

      if capture:
        cert += line
        cert += '\n'

      if '-----END CERTIFICATE-----' in line:
        done = True
        break

  return cert

async def provisionAwsOtaDemo(console, thingName, mqttEndpoint, ota_signer_key):
  #TODO Check if the demo is in provisioning mode & process incoming messages

  await wait_for_pattern(console, 'Command Line Interface')

  print('Provisioning the config...')
  await console.send("conf set wifi_ssid Arm\r\n")
  await console.send("conf set wifi_credential Arm\r\n")
  await console.send("conf set mqtt_endpoint {}\r\n".format(mqttEndpoint))
  await console.send("conf set thing_name {}\r\n".format(thingName))
  await console.send("conf commit\r\n")
  print('done')

  print('Provisioning the pki...')
  await console.send("pki generate key\r\n")
  await console.send("pki generate csr\r\n")
  await console.send("pki generate cert\r\n")

  cert = await captureDeviceCert(console)

  await console.send("pki import key ota_signer_pub\r\n")
  await console.send(ota_signer_key)

  print('done')

  return cert

async def cleanAwsIotThing(thingName, certArn, certId, certPolicy):
  print('Cleaning up AWS IoT thing...')
  try:
    iot = boto3.client('iot')
  except Exception as e:
    print('Failed to cleanup AWS IoT thing')
    raise e
  try:
    iot.detach_policy(policyName=certPolicy, target=certArn)
  except:
    pass
  try:
    iot.detach_thing_principal(thingName=thingName, principal=certArn)
  except:
    pass
  try:
    iot.update_certificate(certificateId=certArn, newStatus='INACTIVE')
  except:
    pass
  try:
    iot.delete_certificate(certificateId=certId)
  except:
    pass
  try:
    iot.delete_thing(thingName=thingName)
  except:
    pass

  print('done')

async def createAwsIotThing(cert, thingName, certPolicy):
  certArn = ''
  certId = ''
  print('Creating AWS IoT thing...')
  try:
    iot = boto3.client('iot')
    res = iot.create_thing(thingName=thingName)
    res = iot.register_certificate_without_ca(certificatePem=cert, status='ACTIVE')
    certArn = res.get('certificateArn')
    certId = res.get('certificateId')
    iot.attach_thing_principal(thingName=thingName, principal=certArn)
    iot.attach_policy(policyName=certPolicy, target=certArn)
  except Exception as e:
    await cleanAwsIotThing(thingName, certArn, certId, certPolicy)
    print('Failed to create AWS IoT thing')
    raise e
  print('done')
  return certArn, certId

async def main():
  error = None
  console = None

  configuration = AvhAPI.Configuration(
      host = apiEndpoint
  )

  async with AvhAPI.ApiClient(configuration=configuration) as api_client:
    api_instance = AvhAPI.ArmApi(api_client)
    awsCert = (None, None) # (certArn, certId)

    token_response = await api_instance.v1_auth_login({
      "apiToken": apiToken,
    })

    print('Logged in')
    configuration.access_token = token_response.token

    print('Finding a project...')
    api_response = await api_instance.v1_get_projects()
    pprint(api_response)
    projectId = api_response[0].id

    try:
      instance = await createSTM32U5(api_instance, vmName)

      consoleEndpoint = await api_instance.v1_get_instance_console(instance.id)
      console = await ws.connect(consoleEndpoint.url, ssl=ctx)
      cert = await provisionAwsOtaDemo(console, thingName, mqttEndpoint, ota_signer_key)
      awsCert = await createAwsIotThing(cert, thingName, certPolicy)

      print("Rebooting the device...")
      await console.send("reset\r\n")
      await asyncio.wait_for(check_version(console, version), timeout=30)

    except asyncio.TimeoutError as e:
      print('Test FAILED: no version message received')
      error = e
    except Exception as e:
      print('Encountered error; cleaning up...')
      error = e
    finally:
      await cleanAwsIotThing(thingName, awsCert[0], awsCert[1], certPolicy)

      if console:
        console.close_timeout = 1
        await console.close()

    if error != None:
      raise error

asyncio.run(asyncio.wait_for(main(), 120))
exit(0)