import asyncio
from distutils.log import error
import os
import re
from websockets import client as ws
import sys
import avh_api_async as AvhAPI
from pprint import pprint
import ssl

vmName = 'DevSummit22-demo'
fmwFile = os.path.join(sys.path[0], '../target/b_u585i_iot02a/firmware')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

if len(sys.argv) < 3 or sys.argv[1] == "-h" or sys.argv[1] == "--help":
  print('Usage: %s <ApiEndpoint> <ApiToken> [[vmName] [fmwFile]]', sys.argv[0])
  exit(-1)

apiEndpoint = sys.argv[1]
apiToken = sys.argv[2]
if len(sys.argv) > 3:
  vmName = sys.argv[3]
if len(sys.argv) > 4:
  fmwFile = sys.argv[4]

async def waitForState(instance, state):
  global api_instance

  instanceState = await api_instance.v1_get_instance_state(instance.id)
  while (instanceState != state):
    if (instanceState == 'error'):
      raise Exception('VM entered error state')
    await asyncio.sleep(1)
    instanceState = await api_instance.v1_get_instance_state(instance.id)

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

    print('Finding DevSummit22-demo instance...')
    api_response = await api_instance.v1_get_instances(name=vmName)
    pprint(api_response)
    if len(api_response) != 1:
      print('Could not find instance')
      exit(-1)
    instance = api_response[0]

    error = None
    try:
      print('Setting the VM to use the bsp test software: {}'.format(fmwFile))
      api_response = await api_instance.v1_create_image('fwbinary', 'plain', 
        name=os.path.basename(fmwFile),
        instance=instance.id,
        file=fmwFile
      )
      pprint(api_response)

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

asyncio.run(asyncio.wait_for(main(), 120))
exit(0)