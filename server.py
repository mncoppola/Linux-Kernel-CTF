import cherrypy
import json
from daemonize import Daemonize
from digitalocean import ClientV2
from pprint import pformat

DROPLETS_FILE = "droplets.json"
API_KEY_FILE = "API_KEY"

def get_api_key():
    with open(API_KEY_FILE, "r") as f:
        return f.read().rstrip()

# Reading from a file every time allows live updates to the droplets list
def get_droplets():
    with open(DROPLETS_FILE, "r") as f:
        data = f.read()
        if not data:
            return []
        else:
            return json.loads(data)

class Root(object):
    def strongly_expire(func):
        def newfunc(*args, **kwargs):
            cherrypy.response.headers["Expires"] = "Sun, 19 Nov 1978 05:00:00 GMT"
            cherrypy.response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0"
            cherrypy.response.headers["Pragma"] = "no-cache"
            return func(*args, **kwargs)
        return newfunc

    @cherrypy.expose
    def index(self):
        return "Usage: /reboot?ip_address=1.2.3.4&amp;password=password"

    @cherrypy.expose
    @strongly_expire
    def reboot(self, ip_address=None, password=None):
        if not ip_address or not password:
            return "Usage: /reboot?ip_address=1.2.3.4&amp;password=password"

        body = ""

        for droplet in get_droplets():
            if droplet["ip_address"] == ip_address and droplet["password"] == password:
                client = ClientV2(token=get_api_key())
                ret = client.droplets.power_cycle(droplet_id=droplet["id"])
                body += "Power cycling %s:<br><br><pre>\n" % ip_address
                body += pformat(ret)
                body += "</pre>"
                return body

        return "Couldn't find that IP address / password combination"

def main():
    # Start web server
    cherrypy.config.update({"server.socket_host": "0.0.0.0", "server.socket_port": 80})
    cherrypy.quickstart(Root(), "/")

if __name__ == "__main__":
    pid = "/tmp/ctf-server.pid"
    daemon = Daemonize(app="CTF server", pid=pid, action=main)
    daemon.start()
