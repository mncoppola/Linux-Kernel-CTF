Linux Kernel CTF
================

A set of scripts to help with hosting a Linux kernel exploitation CTF challenge. Deploys a challenge VM for each team.

Maintains a list of deployed VMs in droplets.json. Designed around the use of Ubuntu droplets in DigitalOcean, though it should be easy to switch out either.

# Requirements

* Configure challenge details in deploy.py (challenge name must match kernel module source directory)
* Put DigitalOcean API key in the file API_KEY
* Configure droplet details in deploy.py

## deploy.py

Automatically deploy DigitalOcean droplets and install the challenge

    deploy.py multiple <number>
        Deploy and install the challenge on <number> droplets (with names team1 .. teamX)

    deploy.py single <droplet name>
        Deploy a single droplet with name <droplet name> and install the challenge

    deploy.py ip <IP address>
        Install the challenge on an already deployed droplet

## server.py

Simple HTTP server on port 80 that teams can query to power cycle their VM

    /reboot?ip_address=1.2.3.4&password=password

## print.py

Print out droplets.json in a human-readable form
