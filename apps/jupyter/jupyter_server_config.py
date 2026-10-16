import os

c = get_config()  # noqa: F821
c.ServerApp.ip = "0.0.0.0"
c.ServerApp.port = 8888
c.ServerApp.open_browser = False
c.ServerApp.root_dir = "/home/jovyan/work"
c.ServerApp.allow_remote_access = True
c.IdentityProvider.token = os.environ["JUPYTER_TOKEN"]
