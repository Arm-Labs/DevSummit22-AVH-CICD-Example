import asyncio
from distutils.log import error
import os
from tabnanny import check
from websockets import client as ws
import sys
import avh_api_async as AvhAPI
from pprint import pprint
import ssl
import time
import re

if len(sys.argv) < 5 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
  print('Usage: %s <ApiToken> <CloudCert> <SignerKey> <expectedVersion> [fmwFile [vmName]', sys.argv[0])
  exit(-1)

apiEndpoint = 'https://app.avh.arm.com/api'
vmName = 'DevSummit22-demo'
fmwFile = os.path.join(sys.path[0], '../target/b_u585i_iot02a/image/firmware')

apiToken = sys.argv[1]
cert = sys.argv[2]
ota_signer_key = sys.argv[3]
version = sys.argv[4]

if len(sys.argv) > 5:
  fmvFile = sys.argv[5]
if len(sys.argv) > 6:
  vmName = sys.argv[6]

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

async def check_version(api_instance, instance, version):
  consoleEndpoint = await api_instance.v1_get_instance_console(instance.id)
  console = await ws.connect(consoleEndpoint.url, ssl=ctx)
  try:
    done = False
    text = ''
    async for message in console:
      if done:
        break

      text += message.decode('utf-8')
      while '\n' in text:
        offset = text.find('\n')
        line, text = text[:offset], text[offset+1:]
        print('<< %s' % line)

        match = re.search(r'OTA over MQTT demo, Application version ([0-9\.]+)', line)
        if (match):
          if (match.group(1) == version):
            print('Test PASSED: version {}'.format(version))
            done = True
            break
          else:
            print('Test FAILED: version {} expected {}'.format(match.group(1), version))
            raise Exception('Test FAILED: Version mismatch')

  finally:
    console.close_timeout = 1
    await console.close()

async def createSTM32U5(api_instance):
  error = None

  print('Finding DevSummit22-demo instance...')
  api_response = await api_instance.v1_get_instances(name=vmName)
  pprint(api_response)
  if len(api_response) != 1:
    print('Could not find instance')
    exit(-1)
  instance = api_response[0]

  try:
    # TODO: For some reason conole is down after image is uploaded; it works fine using web

    # print('Setting the VM to use the demo image: {}'.format(fmwFile))
    # api_response = await api_instance.v1_create_image('fwbinary', 'plain', 
    #   name=os.path.basename(fmwFile),
    #   instance=instance.id,
    #   file=fmwFile
    # )
    # pprint(api_response)

    print('Resetting VM to use the new software')
    api_response = await api_instance.v1_reboot_instance(instance.id)

    print('Waiting for VM to finish resetting...')
    await waitForState(api_instance, instance, 'on')
    print('done')

  except Exception as e:
    print('Encountered error; cleaning up...')
    error = e

  if error != None:
    raise error

  return instance

async def provisionAwsOtaDemo(api_instance, instance):
  consoleEndpoint = await api_instance.v1_get_instance_console(instance.id)
  console = await ws.connect(consoleEndpoint.url, ssl=ctx)
  try:
    #TODO Check if the demo is in provisioning mode & process incoming messages

    #XXX: The board needs to be pre-provisioned and on before running this script; this is due to an issue with
    # flashing new image to a vm. The only part of the provisioning data that doesn't survive a reboot is the cert.

    # print('Provisioning the config...')
    # await console.send("conf set wifi_ssid Arm\r\n")
    # time.sleep(0.1) #Workouround for getchar issue
    # await console.send("conf set wifi_credential Arm\r\n")
    # time.sleep(0.1) #Workouround for getchar issue
    # await console.send("conf set mqtt_endpoint XXX.amazonaws.com\r\n")
    # time.sleep(0.1) #Workouround for getchar issue
    # await console.send("conf set thing_name bartek-ds22-demo-thing\r\n")
    # time.sleep(0.1) #Workouround for getchar issue
    # await console.send("conf commit\r\n")
    # print('done')
    # time.sleep(0.1) #Workouround for getchar issue

    print('Provisioning the pki...')
    # await console.send("pki generate key\r\n")
    # time.sleep(0.1) #Workouround for getchar issue
    # await console.send("pki generate csr\r\n")

    time.sleep(0.5) #Workouround for getchar issue

    await console.send("pki import cert\r\n")
    time.sleep(0.5) #Workouround for getchar issue
    for chr in cert:
      time.sleep(0.05) #Workouround for getchar issue
      await console.send(chr)

    # await console.send("pki import key ota_signer_pub\r\n")
    # time.sleep(0.1) #Workouround for getchar issue
    # for chr in ota_signer_key:
    #   time.sleep(0.05) #Workouround for getchar issue
    #   await console.send(chr)

    print('done')

    print("Rebooting the device...")
    await console.send("reset\r\n")

  finally:
    console.close_timeout = 1
    await console.close()

async def main():
  error = None

  configuration = AvhAPI.Configuration(
      host = apiEndpoint
  )
  # Enter a context with an instance of the API client
  async with AvhAPI.ApiClient(configuration=configuration) as api_client:
    # Create an instance of the API class
    api_instance = AvhAPI.ArmApi(api_client)

    # Log In
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
      instance = await createSTM32U5(api_instance)
      await provisionAwsOtaDemo(api_instance, instance)
      await asyncio.wait_for(check_version(api_instance, instance, version), timeout=30)

    except asyncio.TimeoutError as e:
      print('Test FAILED: no version message received')
      error = e
    except Exception as e:
      print('Encountered error; cleaning up...')
      error = e

    if error != None:
      raise error

asyncio.run(asyncio.wait_for(main(), 120))
exit(0)