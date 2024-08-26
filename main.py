import os
import time
import importlib
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(script_dir, "application_config.txt")

def is_api_key_present():
    return os.path.exists(config_file) and os.path.getsize(config_file) > 0

def run_gradio_app():
    if not is_api_key_present():
        p = subprocess.Popen(["python3", "-c", "from d3mwp import ask_for_api_key; ask_for_api_key().launch(share=False, inline=False)"])
        
        while not is_api_key_present():
            time.sleep(1)

        p.terminate()

    d3mwp = importlib.import_module("d3mwp")
    d3mwp.main_app().launch(share=False, inline=False)

if __name__ == '__main__':
    run_gradio_app()