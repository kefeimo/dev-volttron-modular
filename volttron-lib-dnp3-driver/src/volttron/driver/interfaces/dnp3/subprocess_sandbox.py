import subprocess
import time
import os
import sys


def main():
    new_env = os.environ.copy()
    new_env["VOLTTRON_HOME"] = r"/home/kefei/.dev-volttron-2"



    try:
        volttron_script_path = r"/home/kefei/project/dev-volttron-modular/env/bin/volttron"
        cmd_str = rf"{sys.executable} {volttron_script_path}"
        cmd = cmd_str.split()
        process = subprocess.Popen(
            cmd,
            # shell=True,
            env=new_env,
            # stderr=subprocess.PIPE,
            # stdout=subprocess.PIPE
        )

        for i in range(20):
            print(process.stdout)
            time.sleep(2)
    except Exception as e:
        print(e)
    finally:
        cmd = rf"vctl shutdown --platform"
        rs = subprocess.run(
            cmd,
            shell=True,
            env=new_env,
            # stderr=subprocess.PIPE,
            # stdout=subprocess.PIPE
        )


if __name__ == "__main__":
    main()
