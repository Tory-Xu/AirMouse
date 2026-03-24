import ctypes
import threading
import time
import mouse_service
import keyboard_service
import config_manager
from ctypes import wintypes
from pynput.mouse import Controller as MouseController, Button as MouseButton

pmouse = MouseController()

# --- XInput 底层结构体定义 ---
class XINPUT_GAMEPAD(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),  # 显式指定无符号，解决负数问题
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]

class XINPUT_STATE(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]

# 加载 Windows 系统 XInput 库
try:
    xinput = ctypes.windll.xinput1_4
except Exception:
    try:
        xinput = ctypes.windll.xinput1_3
    except Exception:
        xinput = None
        print("ERROR: 找不到 XInput DLL，请确保是在 Windows 环境下运行。")

# --- 状态变量 ---
gamepad_connected = False
gamepad_name = "未连接"
selected_index = 0 # 对应 Player 1-4 (0-3)

# 模拟 inputs 的 state 字典，保持向后兼容
state = {
    'ABS_X': 0, 'ABS_Y': 0,
    'ABS_RX': 0, 'ABS_RY': 0,
    'ABS_Z': 0, 'ABS_RZ': 0, 
    'HAT_X': 0, 'HAT_Y': 0
}
active_keys = set()
_cached_cfg = None

# XInput 按键位掩码与原本 inputs 事件码的映射
BTN_MAP = {
    0x1000: 'BTN_SOUTH', 0x2000: 'BTN_EAST', 0x4000: 'BTN_WEST', 0x8000: 'BTN_NORTH',
    0x0100: 'BTN_TL', 0x0200: 'BTN_TR', 0x0040: 'BTN_THUMBL', 0x0080: 'BTN_THUMBR',
    0x0020: 'BTN_SELECT', 0x0010: 'BTN_START'
}

def update_config(data):
    global _cached_cfg
    _cached_cfg = data

def get_current_cfg():
    global _cached_cfg
    if _cached_cfg is None:
        _cached_cfg = config_manager.load_gp_macros()
    return _cached_cfg

def get_gamepad_list(force_rescan=False):
    """XInput 不需要手动刷新，这里仅检测 4 个槽位的连接情况"""
    if not xinput: return []
    res = []
    temp_state = XINPUT_STATE()
    for i in range(4):
        if xinput.XInputGetState(i, ctypes.byref(temp_state)) == 0:
            res.append({"name": f"XInput 控制器 {i+1}", "index": i})
    return res

def handle_btn(btn_code, pressed):
    if not gamepad_connected: return
    
    mapping = {
        'BTN_SOUTH': 'btn_0', 'BTN_EAST': 'btn_1', 'BTN_WEST': 'btn_2', 'BTN_NORTH': 'btn_3',
        'BTN_TL': 'btn_4', 'BTN_TR': 'btn_5', 'BTN_THUMBL': 'btn_10', 'BTN_THUMBR': 'btn_11',
        'BTN_SELECT': 'btn_8', 'BTN_START': 'btn_9'
    }
    
    cfgId = mapping.get(btn_code)
    if not cfgId: return
    
    data = get_current_cfg()
    if not data or not data.get('current') or not data.get('enabled', True): return
    current_map = data['profiles'][data['current']]
    action = current_map.get(cfgId, 'none')
    
    execute_action(action, pressed)

def execute_action(action, pressed):
    if action == 'none': return
    if action.startswith('click_'):
        btn_map = {'left': MouseButton.left, 'right': MouseButton.right, 'middle': MouseButton.middle}
        btn_str = action.split('_')[1]
        try:
            if pressed: pmouse.press(btn_map[btn_str])
            else: pmouse.release(btn_map[btn_str])
        except Exception: pass
    elif action.startswith('key_'):
        if '+' in action:
            if pressed:
                keys = [k.replace('key_', '') for k in action.split('+')]
                keyboard_service.handle_combo({'keys': keys})
        else:
            mapped_key = action.replace('key_', '')
            # 普通按键映射：放开 no_repeat，允许系统自动触发长按重复
            # 只有摇杆映射才需要强制 no_repeat
            keyboard_service.handle_key_action({'key': mapped_key, 'action': 'down' if pressed else 'up'})

def handle_stick(mode, xVal, yVal, res_m, res_k):
    if mode == "mouse":
        if abs(xVal)>0: res_m['mx'] += xVal
        if abs(yVal)>0: res_m['my'] += yVal
        return
    if mode.startswith("scroll"):
        mult = -1 if mode == "scroll_rev" else 1
        if abs(xVal)>0: res_m['sx'] += xVal * mult
        if abs(yVal)>0: res_m['sy'] += yVal * mult
        return
    
    layout = {}
    if mode == "wasd": layout = {'up': "w", 'down': "s", 'left': "a", 'right': "d"}
    elif mode == "hjkl": layout = {'up': "k", 'down': "j", 'left': "h", 'right': "l"}
    elif mode == "arrows": layout = {'up': "up", 'down': "down", 'left': "left", 'right': "right"}
    else: return
    
    threshold = 0.5
    if yVal < -threshold: res_k.add(layout['up'])
    if yVal > threshold: res_k.add(layout['down'])
    if xVal < -threshold: res_k.add(layout['left'])
    if xVal > threshold: res_k.add(layout['right'])

def main_loop():
    """统合所有逻辑的高级轮询线程"""
    global gamepad_connected, gamepad_name, active_keys
    
    last_buttons = 0
    prev_lt, prev_rt = False, False
    prev_hat = {'u': False, 'd': False, 'l': False, 'r': False}
    
    x_state = XINPUT_STATE()
    target_fps = 120
    frame_time = 1.0 / target_fps
    
    rem_mx, rem_my = 0.0, 0.0
    rem_sx, rem_sy = 0.0, 0.0

    while True:
        start_t = time.perf_counter()
        
        if not xinput:
            time.sleep(1)
            continue

        # 获取当前选中槽位的状态
        res_code = xinput.XInputGetState(selected_index, ctypes.byref(x_state))
        
        if res_code != 0: # ERROR_SUCCESS is 0
            if gamepad_connected:
                print(f"[Gamepad] XInput 设备断开 (槽位 {selected_index})")
            gamepad_connected = False
            gamepad_name = "未发现手柄"
            # 清理按键状态
            for k in list(active_keys):
                keyboard_service.handle_key_action({'key': k, 'action': 'up', 'no_repeat': True})
            active_keys.clear()
            time.sleep(1)
            continue
        
        if not gamepad_connected:
            print(f"[Gamepad] XInput 设备已连接 (槽位 {selected_index})")
            gamepad_connected = True
            gamepad_name = f"XInput 手柄 {selected_index + 1}"

        gp = x_state.Gamepad
        
        # 1. 处理普通按键按下/抬起 (Bitmask)
        current_buttons = gp.wButtons
        changed = current_buttons ^ last_buttons
        if changed:
            for bit, code in BTN_MAP.items():
                if changed & bit:
                    handle_btn(code, bool(current_buttons & bit))
            last_buttons = current_buttons

        # 2. 更新摇杆坐标并归一化 (-1.0 to 1.0)
        # 注意：Y轴在 XInput 中 向上为正
        state['ABS_X'] = gp.sThumbLX
        state['ABS_Y'] = gp.sThumbLY
        state['ABS_RX'] = gp.sThumbRX
        state['ABS_RY'] = gp.sThumbRY
        state['ABS_Z'] = gp.bLeftTrigger
        state['ABS_RZ'] = gp.bRightTrigger
        
        # 3. 处理 D-Pad (映射为 inputs 的 HAT 事件)
        u = bool(current_buttons & 0x0001); d = bool(current_buttons & 0x0002)
        l = bool(current_buttons & 0x0004); r = bool(current_buttons & 0x0008)
        state['HAT_X'] = 1 if r else (-1 if l else 0)
        state['HAT_Y'] = 1 if d else (-1 if u else 0)

        # 4. 执行持续逻辑 (移动、连按等)
        data = get_current_cfg()
        if data and data.get('current') and data.get('enabled', True):
            current_map = data['profiles'][data['current']]
            sens = float(data.get('sens', 5.0))
            scroll_sens = float(data.get('scroll_sens', 5.0))
            dz = float(data.get('deadzone', 0.15))
            curve_type = data.get('curve', 'medium')
            
            def apply_dz_local(val, max_val):
                norm = val / max_val
                return norm if abs(norm) > dz else 0

            l_x = apply_dz_local(gp.sThumbLX, 32767.0)
            l_y = apply_dz_local(gp.sThumbLY, 32767.0) # 修正：这里不再反向，后面统一算
            r_x = apply_dz_local(gp.sThumbRX, 32767.0)
            r_y = apply_dz_local(gp.sThumbRY, 32767.0)
            
            # LT/RT 映射 (带消抖逻辑，防止在阈值边缘跳变)
            lt_val = gp.bLeftTrigger
            rt_val = gp.bRightTrigger
            
            # 使用迟滞逻辑 (Hysteresis): 
            # 只有压下超过 45 才算按下，必须松开到 20 以下才算释放
            target_lt = True if lt_val > 45 else (False if lt_val < 20 else prev_lt)
            target_rt = True if rt_val > 45 else (False if rt_val < 20 else prev_rt)
            
            if target_lt != prev_lt: 
                print(f"[Gamepad] LT 状态: {target_lt} (原始值: {lt_val})")
                execute_action(current_map.get('btn_6', 'none'), target_lt)
                prev_lt = target_lt
                
            if target_rt != prev_rt: 
                print(f"[Gamepad] RT 状态: {target_rt} (原始值: {rt_val})")
                execute_action(current_map.get('btn_7', 'none'), target_rt)
                prev_rt = target_rt

            # D-Pad 变化映射
            if u != prev_hat['u']: execute_action(current_map.get('btn_12', 'none'), u); prev_hat['u'] = u
            if d != prev_hat['d']: execute_action(current_map.get('btn_13', 'none'), d); prev_hat['d'] = d
            if l != prev_hat['l']: execute_action(current_map.get('btn_14', 'none'), l); prev_hat['l'] = l
            if r != prev_hat['r']: execute_action(current_map.get('btn_15', 'none'), r); prev_hat['r'] = r

            res_m = {'mx':0.0, 'my':0.0, 'sx':0.0, 'sy':0.0}
            res_k = set()
            # 统一计算摇杆结果，注意 Y 轴在 XInput 向上为正，如果是模拟鼠标通常需要反转
            handle_stick(current_map.get('stick_left', 'none'), l_x, -l_y, res_m, res_k)
            handle_stick(current_map.get('stick_right', 'none'), r_x, -r_y, res_m, res_k)

            # 响应曲线
            mx_raw, my_raw = res_m['mx'], res_m['my']
            mag = (mx_raw**2 + my_raw**2)**0.5
            accel = 1.0 + (mag**2 * 5.0) if curve_type == 'aggressive' else (1.0 + mag**1.5 * 2.5 if curve_type == 'medium' else 1.0)
            
            dx_float = mx_raw * accel * sens * 4.0 + rem_mx
            dy_float = my_raw * accel * sens * 4.0 + rem_my
            sx_float = res_m['sx'] * scroll_sens * 0.05 + rem_sx
            sy_float = res_m['sy'] * scroll_sens * 0.05 + rem_sy
            
            dx, dy = int(dx_float), int(dy_float)
            sx, sy = int(sx_float), int(sy_float)
            rem_mx, rem_my = dx_float - dx, dy_float - dy
            rem_sx, rem_sy = sx_float - sx, sy_float - sy

            if dx != 0 or dy != 0: mouse_service.handle_move({'dx': dx, 'dy': dy})
            if sx != 0 or sy != 0: mouse_service.handle_scroll({'dx': sx, 'dy': sy})

            # 更新 WASD 等映射键状态
            for k in list(active_keys):
                if k not in res_k:
                    keyboard_service.handle_key_action({'key': k, 'action': 'up', 'no_repeat': True})
                    active_keys.remove(k)
            for k in res_k:
                if k not in active_keys:
                    keyboard_service.handle_key_action({'key': k, 'action': 'down', 'no_repeat': True})
                    active_keys.add(k)

        # 控制环路频率
        elapsed = time.perf_counter() - start_t
        if elapsed < frame_time:
            time.sleep(frame_time - elapsed)

def start_threads():
    threading.Thread(target=main_loop, daemon=True).start()
