import asyncio
from distutils.log import error
import os
import re
from websockets import client as ws
import sys
import avh_api_async as AvhAPI
from pprint import pprint
import ssl

if len(sys.argv) < 4 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
  print('Usage: %s <ApiToken> <CloudCert> <SignerKey> [fmwFile [vmName]', sys.argv[0])
  exit(-1)

apiEndpoint = 'https://app.avh.arm.com/api'
vmName = 'DevSummit22-demo'
fmwFile = os.path.join(sys.path[0], '../target/b_u585i_iot02a/firmware')

apiToken = sys.argv[1]
cert = sys.argv[2]
ota_signer_key = sys.argv[3]

if len(sys.argv) > 4:
  fmvFile = sys.argv[4]
if len(sys.argv) > 5:
  vmName = sys.argv[5]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

async def waitForState(instance, state):
  global api_instance

  instanceState = await api_instance.v1_get_instance_state(instance.id)
  while (instanceState != state):
    if (instanceState == 'error'):
      raise Exception('VM entered error state')
    await asyncio.sleep(1)
    instanceState = await api_instance.v1_get_instance_state(instance.id)

async def createSTM32U5():
  global exitStatus
  global api_instance

  print('Finding DevSummit22-demo instance...')
  api_response = await api_instance.v1_get_instances(name=vmName)
  pprint(api_response)
  if len(api_response) != 1:
    print('Could not find instance')
    exit(-1)
  instance = api_response[0]

  error = None
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
    await waitForState(instance, 'on')
    print('done')

  except Exception as e:
    print('Encountered error; cleaning up...')
    error = e

  if error != None:
    raise error

  return instance

async def provisionAwsOtaDemo(instance):
  global api_instance
  global ctx
  done = False

  consoleEndpoint = await api_instance.v1_get_instance_console(instance.id)
  console = await ws.connect(consoleEndpoint.url, ssl=ctx)
  try:
    #TODO Check if the demo is in provisioning mode & process incoming messages

    await console.send("conf get\n")

    print('Provisioning the config...')
    await console.send("conf set wifi_ssid Arm\n")
    await console.send("conf set wifi_credential Arm\n")
    await console.send("conf set mqtt_endpoint XXX.eu-west-1.amazonaws.com\n")
    await console.send("conf set thing_name bartek-ds22-demo-thing\n")
    await console.send("conf commit\n")
    await console.send("conf get\n")
    print('done')

    print('Provisioning the pki...')
    await console.send("pki generate key\n")
    await console.send("pki generate csr\n")


    #Following doesn't work; too fast?
    # await console.send("pki import key ota_signer_pub\n")
    # await console.send(ota_signer_key)

    # await console.send("pki import cert\n")
    # await console.send(cert)

    print('done')

    async for message in console:
      print(message.decode('UTF-8', errors='ignore'))

    print("Rebooting the device...")
    await console.send("reset\n")

  finally:
    console.close_timeout = 1
    await console.close()

# Defining the host is optional and defaults to https://app.avh.arm.com/api
# See configuration.py for a list of all supported configuration parameters.

exitStatus = 0

async def main():
  global exitStatus
  global api_instance

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
      instance = await createSTM32U5()
      await provisionAwsOtaDemo(instance)

    except Exception as e:
      print('Encountered error; cleaning up...')
      error = e

    if error != None:
      raise error

asyncio.run(asyncio.wait_for(main(), 120))
exit(0)