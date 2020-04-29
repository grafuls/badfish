![badfish](/image/badfish-original-licensed.small.png)

[![Build Status](https://travis-ci.com/redhat-performance/badfish.svg?branch=master)](https://travis-ci.com/redhat-performance/badfish)
[![Build Status](https://img.shields.io/docker/cloud/build/quads/badfish.svg)](https://cloud.docker.com/repository/registry-1.docker.io/quads/badfish/builds)

   * [About Badfish](#badfish)
      * [Scope](#scope)
      * [Features](#features)
      * [Requirements](#requirements)
      * [Setup](#setup)
      * [Usage](#usage)
      * [Usage via Docker](#usage-via-docker)
      * [Common Operations](#common-operations)
         * [Enforcing an OpenStack Director-style interface order](#enforcing-an-openstack-director-style-interface-order)
         * [Enforcing a Foreman-style interface order](#enforcing-a-foreman-style-interface-order)
         * [Forcing a one time boot to a specific device](#forcing-a-one-time-boot-to-a-specific-device)
         * [Forcing a one time boot to a specific mac address](#forcing-a-one-time-boot-to-a-specific-mac-address)
         * [Forcing a one time boot to a specific type](#forcing-a-one-time-boot-to-a-specific-type)
         * [Forcing a one-time boot to PXE](#forcing-a-one-time-boot-to-pxe)
         * [Rebooting a System](#rebooting-a-system)
         * [Power Cycling a System](#power-cycling-a-system)
         * [Resetting iDRAC](#resetting-idrac)
         * [Check current boot order](#check-current-boot-order)
         * [Variable number of retries](#variable-number-of-retries)
         * [Firmware inventory](#firmware-inventory)
         * [Clear Job Queue](#clear-job-queue)
         * [Bulk actions via text file with list of hosts](#bulk-actions-via-text-file-with-list-of-hosts)
         * [Verbose Output](#verbose-output)
         * [Log to File](#log-to-file)
      * [iDRAC and Data Format](#idrac-and-data-format)
         * [Dell Foreman and PXE Interface](#dell-foreman-and-pxe-interface)
      * [Contributing](#contributing)
      * [Contact](#contact)

# Badfish
Badfish is a Redfish-based API tool for managing bare-metal systems via the [Redfish API](https://www.dmtf.org/standards/redfish)

We will be adding support for a plethora of SuperMicro systems also in the near future.

You can read more [about badfish](https://quads.dev/about-badfish/) at the [QUADS](https://quads.dev/) website.

## Scope
Right now Badfish is focused on managing Dell systems, but can potentially work with any system that supports the Redfish API.

We're mostly concentrated on programmatically enforcing interface/device boot order to accommodate [TripleO](https://docs.openstack.org/tripleo-docs/latest/) based [OpenStack](https://www.openstack.org/) deployments while simultaneously allowing easy management and provisioning of those same systems via [The Foreman](https://theforeman.org/).  Badfish can be useful as a general standalone, unified vendor IPMI/OOB tool however as support for more vendors is added.

## Features
* Toggle and save a persistent interface/device boot order on remote systems
* Optionally one-time boot to a specific interface or to first device listed for PXE booting
* Check current boot order
* Reboot host
* Reset iDRAC
* Clear iDRAC job queue
* Get firmware inventory of installed devices supported by iDRAC
* Bulk actions via plain text file with list of hosts
* Logging to a specific path
* Containerized Badfish image

## Requirements
* iDRAC7,8 or newer
* Firmware version ```2.60.60.60``` or higher
* iDRAC administrative account
* Python >= ```3.6``` or podman/docker

## Setup
### Badfish Standalone cli
```
git clone https://github.com/redhat-performance/badfish && cd badfish
python setup.py build
python setup.py install
```
NOTE:
* This will allow Badfish to be call from the terminal via the ```badfish``` command

### Badfish Standalone
```
git clone https://github.com/redhat-performance/badfish && cd badfish
pip install -r requirements.txt
```
NOTE:
* This will allow the badfish script via ```./src/badfish.py```

## Usage
Badfish operates against a YAML configuration file to toggle between key:value pair sets of boot interface/device strings.  You just need to create your own interface config that matches your needs to easily swap/save interface/device boot ordering or select one-time boot devices.

## Usage via docker
Badfish can now be run via a docker-image. For this you need to first pull the Badfish image via:
```
docker pull quads/badfish
```
You can then run badfish from inside the container:
```
docker run -it --rm --dns $DNS_IP quads/badfish -H $HOST -u $USER -p $PASS --reboot-only
```
NOTE:
* If you are running quads against a host inside a VPN you must specify your VPN DNS server ip address with --dns
* If you would like to use a different file for config/idrac_interfaces.yml you can map a volume to your modified config with `-v idrac_interfaces.yml:config/idrac_interfaces.yml`

## Common Operations

### Enforcing an OpenStack Director-style interface order
In our performance/scale R&D environments TripleO-based OpenStack deployments require a specific 10/25/40GbE NIC to be the primary boot device for PXE, followed by disk, and then followed by the rest of the interfaces.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml -t director
```

### Enforcing a Foreman-style interface order
Foreman and Red Hat Satellite (as of 6.x based on Foreman) require managed systems to first always PXE from the interface that is Foreman-managed (DHCP/PXE).  If the system is not set to build it will simply boot to local disk.  In our setup we utilize a specific NIC for this interface based on system type.

```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml -t foreman
```

### Forcing a one time boot to a specific device
To force systems to perform a one-time boot to a specific device you can use the ```--boot-to``` option and pass as an argument the device you want the one-time boot to be set to. This will change the one time boot BIOS attributes OneTimeBootMode and OneTimeBootSeqDev and on the next reboot it will attempt to PXE boot or boot from that interface string.  You can obtain the device list via the `--check-boot` directive below.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --boot-to NIC.Integrated.1-3-1
```

### Forcing a one time boot to a specific mac address
To force systems to perform a one-time boot to a specific mac address you can use the ```--boot-to-mac``` option and pass as an argument the device mac address for a specific NIC that you want the one-time boot to be set to. This will change the one time boot BIOS attributes OneTimeBootMode and OneTimeBootSeqDev and on the next reboot it will attempt to PXE boot or boot from that interface.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --boot-to-mac A9:BB:4B:50:CA:54
```

### Forcing a one time boot to a specific type
To force systems to perform a one-time boot to a specific type you can use the ```--boot-to-type``` option and pass as an argument the device type of either foreman or director that you want the one-time boot to be set to. For this action you must also include the path to your interfaces yaml. This will change the one time boot BIOS attributes OneTimeBootMode and OneTimeBootSeqDev and on the next reboot it will attempt to PXE boot or boot from the first interface defined for that host type on the interfaces yaml file.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml --boot-to-type foreman
```

### Forcing a one-time boot to PXE
To force systems to perform a one-time boot to PXE, simply pass the ```--pxe``` flag to any of the commands above, by default it will pxe off the first available device for PXE booting.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml -t foreman --pxe
```

### Rebooting a system
In certain cases you might need to only reboot the host, for this case we included the ```--reboot-only``` flag which will force a GracefulRestart on the target host. Note that this option is not to be used with any other option.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --reboot-only
```

### Power cycling a system
For a hard reset you can use ```--power-cycle``` flag which will run a ForceOff instruction on the target host. Note that this option is not to be used with any other option.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --power-cycle
```

### Resetting iDRAC
For the replacement of `racadm racreset`, the optional argument `--racreset` was added. When this argument is passed to ```badfish```, a graceful restart is triggered on the iDRAC itself.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --racreset
```

### Check current boot order
To check the current boot order of a specific host you can use the ```--check-boot``` option which will return an ordered list of boot devices. Additionally you can pass the ```-i``` option which will in turn print on screen what type of host does the current boot order match (Foreman or Director).
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml --check-boot
```

### Variable number of retries
At certain points during the execution of ```badfish``` the program might come across a non responsive resources and will automatically retry to establish connection. We have included a default value of 15 retries after failed attempts but this can be customized via the ```--retries``` optional argument which takes as input an integer with the number of desired retries.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml -t foreman --retries 20
```

### Firmware inventory
If you would like to get a detailed list of all the devices supported by iDRAC you can run ```badfish``` with the ```--firware-inventory``` option which will return a list of devices with additional device info.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --firmware-inventory
```

### Clear Job Queue
If you would like to clear all the jobs that are queued on the remote iDRAC you can run ```badfish``` with the ```--clear-jobs``` option which query for all active jobs in the iDRAC queue and will post a request to clear the queue.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --clear-jobs
```

You can also force the clearing of Dell iDRAC job queues by passing the `--force` option.

```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass --clear-jobs --force
```

This is the same as passing `racadm jobqueue delete -i JID_CLEARALL_FORCE`

### Bulk actions via text file with list of hosts
In the case you would like to execute a common badfish action on a list of hosts, you can pass the optional argument ```--host-list``` in place of ```-H``` with the path to a text file with the hosts you would like to action upon and any addtional arguments defining a common action for all these hosts.
```
./src/badfish.py --host-list /tmp/bad-hosts -u root -p yourpass --clear-jobs
```

### Verbose output
If you would like to see a more detailed output on console you can use the ```--verbose``` option and get a additional debug logs. Note: this is the default log level for the ```--log``` argument.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml -t foreman --verbose
```

### Log to file
If you would like to log the output of ```badfish``` you can use the ```--log``` option and pass the path to where you want ```badfish``` to log it's output to.
```
./src/badfish.py -H mgmt-your-server.example.com -u root -p yourpass -i config/idrac_interfaces.yml -t foreman --log /tmp/bad.log
```

## iDRAC and Data Format

### Dell Foreman and PXE Interface
Your usage may vary, this is what our configuration looks like via ```config/idrac_interfaces.yml```

| Machine Type | Network Interface      |
| ------------ | ----------------------:|
| Dell fc640   |  NIC.Integrated.1-1-1  |
| Dell r620	   |  NIC.Integrated.1-3-1  |
| Dell r630    |  NIC.Slot.2-1-1        |
| Dell r930    |  NIC.Integrated.1-3-1  |
| Dell r720xd  |  NIC.Integrated.1-3-1  |
| Dell r730xd  |  NIC.Integrated.1-3-1  |
| Dell r740xd  |  NIC.Integrated.1-3-1  |
| Dell r640    |  NIC.Integrated.1-1-1  |

## Contributing
We love pull requests and welcome contributions from everyone!  Please use the `development` branch to send pull requests.  Here are the general steps you'd want to follow.

1) Fork the Badfish Github repository
2) Clone the forked repository
3) Push your changes to your forked clone
4) Open a pull request against our `development` branch.

* Here is some useful documentation
  - [Creating a pull request](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request)
  - [Keeping a cloned fork up to date](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/syncing-a-fork)

## Contact

* You can find us on IRC in `#quads` on `irc.freenode.net` if you have questions or need help.  [Click here](https://webchat.freenode.net/?channels=quads) to join in your browser.

