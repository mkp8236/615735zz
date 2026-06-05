"""
云手机本地运行 - 基础操作库 (无Root, 无ADB, 无无障碍)
适用场景: 传奇小游戏等挂机脚本

所有颜色输入统一使用 "#RRGGBB" 字符串格式。
"""

import subprocess
import time
import random
import io
import os
import ctypes
import numpy as np
from PIL import Image

# ==================== 进程伪装 (可选) ====================
def disguise_process(name=b"sh"):
    """修改当前进程名，躲避进程扫描。默认伪装为 sh"""
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.prctl(15, name, 0, 0, 0)  # PR_SET_NAME = 15
    except:
        pass  # 失败不影响运行

# ==================== 颜色解析 ====================
def parse_color(color_str):
    """
    将 "#RRGGBB" 字符串转换为 (R, G, B) 元组。
    支持带 # 或不带 #，例如 "#909090" 或 "909090"。
    """
    s = color_str.strip().lstrip('#')
    if len(s) != 6:
        raise ValueError(f"颜色格式不正确，需要6位十六进制: {color_str}")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r, g, b)

# ==================== 屏幕相关 ====================
def get_screen_size():
    """获取屏幕宽高 (width, height)"""
    out = subprocess.check_output(["wm", "size"]).decode()
    # 输出格式: Physical size: 1080x1920 或 1080x1920
    w, h = map(int, out.strip().split()[-1].split("x"))
    return w, h

def screenshot():
    """截取当前屏幕，返回 PIL Image 对象 (RGB)"""
    proc = subprocess.Popen(["screencap", "-p"], stdout=subprocess.PIPE)
    img_bytes = proc.stdout.read()
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return img

def screenshot_np():
    """截取屏幕并转为 numpy 数组 (H, W, 3) uint8"""
    return np.array(screenshot())

# ==================== 触控操作 ====================
def tap(x, y, offset=5):
    """
    点击屏幕 (x, y)，加入随机偏移
    offset: 最大偏移像素，默认 ±5
    """
    x += random.randint(-offset, offset)
    y += random.randint(-offset, offset)
    subprocess.run(["input", "tap", str(x), str(y)])

def long_press(x, y, duration_ms=800, offset=3):
    """
    长按屏幕 (x, y)
    duration_ms: 按压持续时间 (毫秒)
    """
    x += random.randint(-offset, offset)
    y += random.randint(-offset, offset)
    subprocess.run(["input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms)])

def swipe(x1, y1, x2, y2, duration_ms=300, offset=3):
    """
    滑动 (x1,y1) -> (x2,y2)
    加入轻微轨迹抖动
    """
    x1 += random.randint(-offset, offset)
    y1 += random.randint(-offset, offset)
    x2 += random.randint(-offset, offset)
    y2 += random.randint(-offset, offset)
    subprocess.run(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])

def keyevent(key_code):
    """发送按键事件，如返回键 keyevent 4, Home键 keyevent 3"""
    subprocess.run(["input", "keyevent", str(key_code)])

def input_text(text):
    """输入文本 (仅限英文/数字)"""
    subprocess.run(["input", "text", str(text)])

# ==================== 延时函数 ====================
def delay(ms):
    """固定延时 (毫秒)"""
    time.sleep(ms / 1000.0)

def random_delay(base_ms, range_ms):
    """
    均匀随机延时: base ± range 毫秒
    示例: random_delay(800, 200) → 600~1000ms
    """
    t = base_ms + random.randint(-range_ms, range_ms)
    if t < 50:
        t = 50
    time.sleep(t / 1000.0)

def gaussian_delay(mean_ms, std_ms):
    """
    高斯分布延时 (毫秒)
    mean_ms: 均值, std_ms: 标准差
    模拟人类反应波动
    """
    t = abs(random.gauss(mean_ms, std_ms))
    if t < 50:
        t = 50
    time.sleep(t / 1000.0)

# ==================== 颜色与图像识别 ====================
def get_pixel_color(img_np, x, y):
    """获取图像某点的 RGB 值，返回 (R, G, B) 元组"""
    return tuple(img_np[y, x])

def is_color_match(pixel, target_color_str, tolerance=10):
    target_rgb = parse_color(target_color_str)
    # 将 pixel 转为 Python int，避免 uint8 溢出
    return all(abs(int(pixel[i]) - target_rgb[i]) <= tolerance for i in range(3))

def find_color_center(img_np, target_color_str, tolerance=10):
    """
    单色块中心定位
    target_color_str: "#RRGGBB" 字符串
    找到所有匹配目标颜色的像素，返回其中心坐标 (x, y)，失败返回 None
    """
    r, g, b = parse_color(target_color_str)
    mask = np.all(np.abs(img_np - [r, g, b]) <= tolerance, axis=2)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(np.mean(xs)), int(np.mean(ys))

def multi_point_find(img_np, points, tolerance=10, region=None):
    """
    多点找色，支持指定搜索区域以提高效率。
    :param img_np: 截图数组 (H, W, 3)
    :param points: [(dx, dy, "#RRGGBB"), ...]
    :param tolerance: 颜色容差
    :param region: (x, y, w, h) 搜索区域左上角坐标及宽高，None 则全图搜索
    :return: 基准点绝对坐标 (x, y) 或 None
    """
    h, w = img_np.shape[:2]

    # 确定搜索区域
    if region is not None:
        rx, ry, rw, rh = region
        # 边界裁剪
        rx = max(0, rx)
        ry = max(0, ry)
        rw = min(rw, w - rx)
        rh = min(rh, h - ry)
        sub_img = img_np[ry:ry+rh, rx:rx+rw]
        offset_x, offset_y = rx, ry
    else:
        sub_img = img_np
        offset_x, offset_y = 0, 0

    base_dx, base_dy, base_color_str = points[0]
    base_rgb = parse_color(base_color_str)
    r0, g0, b0 = base_rgb

    # 在子图中寻找基准点
    mask = np.all(np.abs(sub_img - [r0, g0, b0]) <= tolerance, axis=2)
    ys, xs = np.where(mask)

    # 检查每个候选点
    for y, x in zip(ys, xs):
        ok = True
        for dx, dy, color_str in points[1:]:
            expected_rgb = parse_color(color_str)
            ny = y + dy
            nx = x + dx
            if not (0 <= ny < sub_img.shape[0] and 0 <= nx < sub_img.shape[1]):
                ok = False
                break
            pixel = sub_img[ny, nx]
            if not all(abs(pixel[i] - expected_rgb[i]) <= tolerance for i in range(3)):
                ok = False
                break
        if ok:
            # 转换为原图坐标
            return x + base_dx + offset_x, y + base_dy + offset_y
    return None

def multi_compare(img_np, coords_colors, tolerance=10):
    """
    多点比色: 判断给定坐标列表的颜色是否全部匹配
    coords_colors: [(x, y, "#RRGGBB"), ...]
    返回 True/False
    """
    for x, y, color_str in coords_colors:
        expected_rgb = parse_color(color_str)
        pixel = img_np[y, x]
        if not all(abs(pixel[i] - expected_rgb[i]) <= tolerance for i in range(3)):
            return False
    return True

def find_template_numpy(img_np, template_np, threshold=0.8):
    """
    模板匹配 (纯numpy, 速度较慢，适合小模板 < 50x50)
    使用归一化相关系数，threshold 为匹配度阈值
    返回匹配到的中心坐标列表 [(x, y), ...]
    """
    h_img, w_img = img_np.shape[:2]
    h_t, w_t = template_np.shape[:2]
    if h_t > h_img or w_t > w_img:
        return []

    # 转灰度并归一化
    gray_img = np.mean(img_np, axis=2).astype(np.float32)
    gray_temp = np.mean(template_np, axis=2).astype(np.float32)
    temp_mean = np.mean(gray_temp)
    temp_std = np.std(gray_temp) + 1e-6
    temp_norm = (gray_temp - temp_mean) / temp_std

    points = []
    for y in range(h_img - h_t + 1):
        for x in range(w_img - w_t + 1):
            sub = gray_img[y:y+h_t, x:x+w_t]
            sub_mean = np.mean(sub)
            sub_std = np.std(sub) + 1e-6
            sub_norm = (sub - sub_mean) / sub_std
            corr = np.mean(sub_norm * temp_norm)
            if corr >= threshold:
                center_x = x + w_t // 2
                center_y = y + h_t // 2
                points.append((center_x, center_y))
    return points

# ==================== 坐标自适应 ====================
def scale_coord(x, y, base_size=(720, 1280), current_size=None):
    """
    将基于基准分辨率的坐标转换为当前屏幕坐标
    base_size: 开发时的屏幕尺寸 (宽, 高)
    current_size: 当前屏幕尺寸，默认自动获取
    """
    if current_size is None:
        current_size = get_screen_size()
    bw, bh = base_size
    cw, ch = current_size
    new_x = int(x * cw / bw)
    new_y = int(y * ch / bh)
    return new_x, new_y

# ==================== 便捷封装 ====================
def wait_and_check(timeout_ms, check_func, interval_ms=500):
    """
    轮询检查，直到条件满足或超时
    check_func: 返回 True 表示条件满足
    interval_ms: 检查间隔
    """
    elapsed = 0
    while elapsed < timeout_ms:
        if check_func():
            return True
        delay(interval_ms)
        elapsed += interval_ms
    return False

def show_message(*args, title="脚本提示"):
    """
    类似按键精灵 ShowMessage，支持多变量拼接。
    示例:
        show_message("当前血量:", hp, "/ 最大血量:", max_hp)
        show_message("找到BOSS，坐标(", boss_x, ",", boss_y, ")")
    日志路径: /sdcard/script_logs/showmessage.log
    """
    # 把所有参数转成字符串并拼接
    msg = "".join(str(arg) for arg in args)

    log_dir = "/sdcard/script_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "showmessage.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {title}: {msg}\n")

# ==================== 基础初始化 ====================
# 如果需要自动伪装进程，取消下面这行的注释：
disguise_process(b"sh")