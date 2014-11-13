import json

DROPLETS_FILE = "droplets.json"

def get_droplets():
    with open(DROPLETS_FILE, "r") as f:
        data = f.read()
        if not data:
            return []
        else:
            return json.loads(data)

def main():
    for droplet in get_droplets():
        print droplet["name"]
        print droplet["ip_address"]
        print "%s:%s" % (droplet["username"], droplet["password"])
        print
        print

if __name__ == "__main__":
    main()
