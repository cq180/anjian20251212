import sys, os
sys.path.insert(0, r"E:\ProjectAI\anjian20251212")
import run_script

cmd_dir = r"D:\game\按键精灵2014\screen\cmd"

# Find folder by UTF-8 bytes
target_buttons = {
    b'\xe5\x90\xaf\xe5\x8a\xa8': 'qidong',
    b'\xe5\x85\xb3\xe9\x97\xad': 'guanbi',
    b'\xe9\x80\xa2\xe9\xad\x94': 'fengmo',
    b'\xe9\x80\xb4killall': 'killall',
}

for f in os.listdir(cmd_dir):
    if f.encode('utf-8') in target_buttons:
        script_path = os.path.join(cmd_dir, f)
        print("Found:", script_path)
        run_script.execute_script(script_path, 1, 1.0)
        break
else:
    print("[ERROR] qidong folder not found in", cmd_dir)