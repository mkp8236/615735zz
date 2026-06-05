from base import *   # 导入本地版 tap、get_screen 等
import subprocess
import io
from PIL import Image
import numpy as np
import random



# ========== 模式切换 ==========
LOCAL_MODE = True  # True=云手机本地运行, False=电脑远程调试
# ==============================

if not LOCAL_MODE:
    # 电脑远程调试：重新定义需要 ADB 的函数，覆盖 base 中的版本
    ADB_PATH = r"C:\leidian\LDPlayer9\adb.exe"
    DEVICE = "127.0.0.1:5573"

    def run_cmd(cmd):
        subprocess.run([ADB_PATH, "-s", DEVICE, "shell"] + cmd)

    def tap(x, y, offset=5):
        x += random.randint(-offset, offset)
        y += random.randint(-offset, offset)
        run_cmd(["input", "tap", str(x), str(y)])

    def get_screen():
        proc = subprocess.Popen(
            [ADB_PATH, "-s", DEVICE, "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE
        )
        return proc.stdout.read()

    def screenshot():
        img_bytes = get_screen()
        return Image.open(io.BytesIO(img_bytes)).convert("RGB")

    def screenshot_np():
        return np.array(screenshot())

    # 如果有其他需要 ADB 的函数（如 swipe, long_press），也在这里同样覆盖



# 定义多点找色的特征点（以游戏内的实际坐标和颜色为准）
# 格式：[(基准dx, 基准dy, (R,G,B)), (偏移dx1, 偏移dy1, (R,G,B)), ...]
points =     [
        (0, 0, "#B0000B"),   # 基准点
        (-53, -5, "#989898"),
        (-50, -15, "#E0E0E0"),
        (-38, -3, "#000000"),
        (-45, 30, "#000000"),
        (-38, 38, "#FFFFFF"),
        (-17, 41, "#000000"),
        (-1, 8, "#2F000B"),
        (-24, -10, "#AE000B"),
    ]




while True:

    # 取一帧
     img_np = screenshot_np()

    # 执行多点找色
     result =multi_point_find(img_np, points, tolerance=25)

     if result:
      x, y = result
      print(f"找到目标，坐标: ({x}, {y})")
      tap(x, y)   # 点击它
      gaussian_delay(3000, 200)

     else:
      print("未找到目标")
      break

