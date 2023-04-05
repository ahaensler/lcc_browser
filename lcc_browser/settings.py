from appdirs import user_data_dir
import os
import yaml
import traceback

data_directory = user_data_dir("lcc-browser", "lcc-browser")
settings_filename = os.path.join(data_directory, "state.yaml")

class Settings(dict):
    def __init__(self,*arg,**kw):
        super().__init__(*arg, **kw)

    def load(self):
        if not os.path.exists(settings_filename):
            print("No setting found at", settings_filename)
            self["node_id"] = "02.01.0D.00.00.00"
            self["html_path"] = os.path.abspath("index.html")
            self["auto_connect"] = False
            self["can_settings"] = {}
            return

        with open(settings_filename, "r") as stream:
            try:
                self |= yaml.safe_load(stream)
            except yaml.YAMLError as e:
                print("Couldn't load settings:", e)
                print(traceback.format_exc())

    def save(self):
        os.makedirs(data_directory, exist_ok=True)
        stream = open(settings_filename, "w")
        yaml.dump(dict(self), stream)

settings = Settings()
