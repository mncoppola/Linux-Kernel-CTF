import json
import os
import paramiko
import random
import string
import sys
import tarfile
import time
from digitalocean import ClientV2

# Challenge config
USERNAME = "csaw"
CHALLENGE = "superawesomechallenge"
ARCH = "x86_64"
FLAG = "flag{xxx}"
KEY_PATH = "/path/to/ssh/key/id_rsa"

# Digital Ocean stuff
IMAGE_ID = "ubuntu-14-04-x64"
IMAGE_SIZE = "512mb"
IMAGE_REGION = "nyc3"
API_KEY_FILE = "API_KEY"

DROPLETS_FILE = "droplets.json"

def usage():
    print "Usage:"
    print "  %s multiple <number>" % sys.argv[0]
    print "  %s single <droplet name>" % sys.argv[0]
    print "  %s ip <IP address>" % sys.argv[0]
    sys.exit(1)

def get_api_key():
    with open(API_KEY_FILE, "r") as f:
        return f.read().rstrip()

def get_pub_key():
    with open("%s.pub" % KEY_PATH) as f:
        return f.read().rstrip()

def add_key():
    client = ClientV2(token=get_api_key())
    data = client.keys.all()
    for key in data["ssh_keys"]:
        if get_pub_key() == key["public_key"]:
            print "[+] SSH key %s is already registered under this account as '%s', using that key" % (KEY_PATH, key["name"])
            return key["id"]
    key_name = "%s CTF" % CHALLENGE
    print "[+] Didn't find %s in the list of registered SSH keys, adding as '%s'" % (KEY_PATH, key_name)
    data = client.keys.create(name=key_name, public_key=get_pub_key())
    return data["id"]

def get_droplets():
    with open(DROPLETS_FILE, "r") as f:
        data = f.read()
        if not data:
            return []
        else:
            return json.loads(data)

def put_droplets(droplets):
    with open(DROPLETS_FILE, "w") as f:
        f.write(json.dumps(droplets))

def new_droplet(name, key_id):
    client = ClientV2(token=get_api_key())
    data = client.droplets.create(name=name, region=IMAGE_REGION, size=IMAGE_SIZE, image=IMAGE_ID, ssh_keys=[key_id])
    droplet_id = data["droplet"]["id"]
    print "[+] Initiated new droplet creation (%s, %s, %s, %s), waiting for completion..." % (name, IMAGE_ID, IMAGE_SIZE, IMAGE_REGION)
    while True:
        time.sleep(5)
        data = client.droplets.get_droplet_actions(droplet_id=droplet_id)
        if data["actions"][0]["status"] == "completed":
            break
    data = client.droplets.get(droplet_id=droplet_id)
    return droplet_id, data["droplet"]["networks"]["v4"][0]["ip_address"]

def get_droplet_info(ip):
    client = ClientV2(token=get_api_key())
    data = client.droplets.all()
    for droplet in data["droplets"]:
        for v4 in droplet["networks"]["v4"]:
            if v4["ip_address"] == ip:
                return droplet["id"], droplet["name"]
    print "[-] Failed to find droplet ID for IP address %s on this account!" % ip
    sys.exit(1)

def gen_password(n):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(n))

def make_tarfile(outfile, src_dir):
    with tarfile.open(outfile, "w:gz") as tar:
        tar.add(src_dir, arcname=os.path.basename(src_dir))

def exec_cmd(ip, user, command):
    success = False
    while success == False:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, 22, user, key_filename=KEY_PATH, timeout=30)
            (stdin, stdout, stderr) = ssh.exec_command(command)
            for line in stdout.readlines():
                print line,
            ssh.close()
            success = True
        except Exception as e:
            print "[-] Failed to execute '%s', trying again... (%s)" % (command, e)
            time.sleep(5)

def exec_root(ip, command):
    exec_cmd(ip, "root", command)

def exec_user(ip, command):
    exec_cmd(ip, USERNAME, command)

def scp_put(ip, user, src, dst):
    success = False
    while success == False:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, 22, user, key_filename=KEY_PATH, timeout=30)
            sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
            sftp.put(src, dst)
            sftp.close()
            ssh.close()
            success = True
        except Exception as e:
            print "[-] Failed to scp '%s' -> '%s', trying again... (%s)" % (src, dst, e)
            time.sleep(5)

def scp_put_root(ip, src, dst):
    scp_put(ip, "root", src, dst)

def scp_put_user(ip, src, dst):
    scp_put(ip, USERNAME, src, dst)

def setup_challenge(droplet_id, droplet_name, ip):
    print "[+] Setting up IP address %s" % ip

    print "[+] Disabling OS security settings..."
    exec_root(ip, "echo kernel.kptr_restrict = 0 >> /etc/sysctl.conf")
    exec_root(ip, "echo kernel.dmesg_restrict = 0 >> /etc/sysctl.conf")

    print "[+] Updating system..."
    exec_root(ip, "apt-get update")
    exec_root(ip, "apt-get install make gcc -y")
    exec_root(ip, "apt-get dist-upgrade -y")
    exec_root(ip, "reboot")

    print "[+] Upgrade complete, waiting for reboot..."
    time.sleep(60)

    print "[+] Creating %s user..." % USERNAME
    exec_root(ip, "useradd -m -s /bin/bash %s" % USERNAME)
    password = gen_password(16)
    exec_root(ip, "echo '%s:%s' | chpasswd" % (USERNAME, password))
    print "[+] Set %s password to: %s" % (USERNAME, password)
    exec_root(ip, "mkdir /home/%s/.ssh" % USERNAME)
    exec_root(ip, "chmod 700 /home/%s/.ssh" % USERNAME)
    exec_root(ip, "echo %s > /home/%s/.ssh/authorized_keys" % (get_pub_key(), USERNAME))
    exec_root(ip, "chmod 600 /home/%s/.ssh/authorized_keys")
    exec_root(ip, "chown -R %s:%s /home/%s/.ssh" % (USERNAME, USERNAME, USERNAME))

    print "[+] Dropping flag..."
    exec_root(ip, "echo '%s' > /root/flag" % FLAG)
    exec_root(ip, "chmod 400 /root/flag")

    print "[+] Copying over challenge..."
    challenge_tar = "%s.tar.gz" % CHALLENGE
    make_tarfile(challenge_tar, CHALLENGE)
    scp_put_user(ip, challenge_tar, "/home/%s/%s" % (USERNAME, challenge_tar))
    exec_user(ip, "tar xvf %s" % challenge_tar)
    exec_user(ip, "rm %s" % challenge_tar)

    print "[+] Compiling challenge..."
    exec_user(ip, "cd %s; make linux-%s KDIR=/lib/modules/`uname -r`/build" % (CHALLENGE, ARCH))

    print "[+] Installing challenge..."
    exec_root(ip, "cp /home/%s/%s/%s.ko /lib/modules/`uname -r`/" % (USERNAME, CHALLENGE, CHALLENGE))
    exec_root(ip, "depmod -a")
    exec_root(ip, "echo %s >> /etc/modules" % CHALLENGE)
    exec_root(ip, "reboot")

    print "[+] Challenge installation complete! Adding to %s" % DROPLETS_FILE

    droplet = {
        "id": droplet_id,
        "name": droplet_name,
        "ip_address": ip,
        "password": password,
    }

    droplets = get_droplets()
    droplets.append(droplet)
    put_droplets(droplets)

def main():
    if len(sys.argv) != 3:
        usage()

    cmd = sys.argv[1]

    if cmd == "single":
        key_id = add_key()
        droplet_name = sys.argv[2]
        droplet_id, ip = new_droplet(droplet_name, key_id)
        print "[+] IP address of new droplet: %s" % ip
        setup_challenge(droplet_id, droplet_name, ip)
    elif cmd == "multiple":
        num = int(sys.argv[2])
        key_id = add_key()
        for x in xrange(num):
            droplet_name = "team%d" % (x + 1)
            droplet_id, ip = new_droplet(droplet_name, key_id)
            print "[+] IP address of new droplet: %s" % ip
            setup_challenge(droplet_id, droplet_name, ip)
    elif cmd == "ip":
        ip = sys.argv[2]
        droplet_id, droplet_name = get_droplet_info(ip)
        setup_challenge(droplet_id, droplet_name, ip)
    else:
        usage()

if __name__ == "__main__":
    main()
