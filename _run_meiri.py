import sys, os
sys.path.insert(0, r"E:\ProjectAI\anjian20251212")
import run_script

cmd_dir = r"D:\game\按键精灵2014\screen\cmd"
# Find the 每日 folder by UTF-8 bytes
each_target = b'\xe6\xaf\x8f\xe6\x97\xa5'
meiri_folder = None
for f in os.listdir(cmd_dir):
    if f.encode('utf-8') == each_target:
        meiri_folder = os.path.join(cmd_dir, f)
        break

if not meiri_folder:
    print("[ERROR] 每日 folder not found")
    sys.exit(1)

print("每日 folder:", meiri_folder)
# Find .ks script inside the folder
for sf in os.listdir(meiri_folder):
    if sf.endswith('.ks'):
        script_path = os.path.join(meiri_folder, sf)
        print("Found .ks:", repr(sf))
        print("Full path:", script_path)
        break

run_script.execute_script(script_path, 1, 1.0)
