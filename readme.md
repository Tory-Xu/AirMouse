# Remote Touchpad & Keyboard
内部代号：feishu（飞鼠）

这是一个基于 Python 后端的轻量级远程控制工具，可将移动设备（Android/iOS）转化为电脑的：触控板、键盘、语音输入工具、宏按键面板。

<table style="border: none;">
  <tr style="border: none;">
    <td style="border: none;">
      <img src="img/Screenshot_20260120-225705.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260123-224640.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260121-210258.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260123-224503.jpg" width="400">
    </td>
  </tr>
</table>

2026 03 22
增加手柄映射功能
<img width="2274" height="1263" alt="image" src="https://github.com/user-attachments/assets/64ea98af-8477-4033-88f0-90103079fd03" />


## 🌟 项目亮点

### 1. 简单启动
Windows 可直接安装 EXE，无需安装 Python 或手机客户端。安装后默认随当前用户登录自动启动，并驻留在系统托盘。

### 2. 触控操作

* **单指**：移动 / 左键单击。
* **双指**：滚动 / 右键单击。
* **三指**：拖拽 / 中键单击。
* **gyro**：陀螺仪飞鼠

并且有提供鼠标前进、后退、中键、上下滚轮的按钮。



## 🪟 Windows 安装包

从 GitHub Releases 下载 `AirMouse-Setup-版本号-x64.exe` 后直接安装。安装器默认创建桌面快捷方式并启用开机自启动。

> 当前安装包未进行 Authenticode 代码签名，Windows SmartScreen 可能显示“未知发布者”。

首次启动时如 Windows 防火墙询问网络访问权限，请勾选“专用网络”并允许访问，否则手机可能无法连接电脑。

托盘菜单支持打开控制中心、复制手机访问地址、切换开机自启动和退出程序。开机自启动使用普通用户权限；如需控制以管理员权限运行的程序，请先退出托盘中的 AirMouse，再右键快捷方式选择“以管理员身份运行”。

### 本地构建安装包

要求 Windows 10/11 x64、Python 3.11 和 Inno Setup 6：

```bat
scripts\build_windows.bat -Version 2.0.0
```

安装包和 SHA-256 校验文件会输出到 `release` 目录。推送 `v*` 标签时，GitHub Actions 也会自动构建并发布相同产物。

## 🛠️ 源码运行要求

* **Python 3.11**

## 🚀 快速启动
> 1 安装python3.11 ， 2 双击直接启动 AirMouseserver.bat ，会自动检查依赖和启动服务器。  
> 3 如果需要控制高权限程序，需要使用管理员权限启动。

 **安装依赖**：
```bash
pip install -r requirements.txt
```

 **运行服务端**：
```bash
python server.py
```




### 手机扫码连接

1. 确保手机与电脑在同一局域网，在电脑上打开 `https://localhost:5888/`。
2. 首页“手机扫码连接”会显示电脑的网卡、访问地址和二维码，使用手机相机扫码即可打开控制中心。也可以复制地址，例如 `https://192.168.31.18:5888/`。
3. 首次访问需在手机浏览器中信任本机的自签名证书。请使用 HTTPS；Chrome 的陀螺仪权限要求安全连接。

连接区在桌面默认展开，在手机默认折叠。程序只显示已启用网卡的有效 IPv4，排除回环、链路本地等不可用地址；优先选择当前访问地址，从 localhost 打开时优先使用默认出站地址。多网卡时可按网卡名称和 IP 切换，请选择与手机处于同一局域网的网卡。未检测到地址时，连接 Wi-Fi 或网线后点击“刷新”；电脑 IP 变化后也需要刷新。

二维码由后端使用 `qrcode` 本地生成 PNG 并随首页返回，不调用外部二维码服务，也不依赖外网响应。

### 固定连接 IP

在路由器中配置：**路由器管理页 → DHCP 地址保留 → 将电脑当前网卡 MAC 与 IP 绑定 → 保存并重新连接**。不同路由器也可能将该功能称为“静态租约”。

有线网卡和无线网卡的 MAC 不同，需要分别绑定。Wi-Fi 如果启用了随机 MAC，请为当前网络保持固定的 MAC，避免地址保留失效。重新连接后刷新首页，并使用更新后的二维码。AirMouse 负责检测和展示地址，固定 IP 由路由器配置。

### 手机文字输入

键盘页默认进入“文字输入”模式，支持手机原生输入法的拼音选词、英文、表情、粘贴和多行编辑。先在电脑上点选目标输入位置，再在手机上编辑并点击“发送到电脑”；空格和换行会原样发送，输入法正在组词时不能发送。

收到成功回执后清空已发送的草稿，并显示“最近发送”。等待回执期间继续编辑的新草稿会保留。回执表示系统输入调用完成，不能保证目标应用接收了全部内容；文字会输入到电脑当前获得焦点的控件。

发送期间不接受重复提交。5 秒未收到有效回执或连接中断时，会保留草稿并提示“结果未确认”，不会自动重发或在重连后补发。请先检查电脑上的内容，再决定是否手动重发，避免重复输入。输入调用失败也可能已输入部分内容。

可随时切换“全键盘”，保留原有按键布局与平板模式；模式切换会保留文字草稿并释放按键、停止重复计时。文字模式自然适配横竖屏，全键盘模式保留手机竖屏时旋转显示的布局。草稿和最近发送内容仅存在当前页面内存中，刷新或离开页面后不保留。

### 回归验证

安装 Python 依赖后执行：

```bash
python -m unittest discover -s tests -v
node --test tests/text_input.test.cjs
```

前端状态测试使用 Node.js 22 或更新版本，无需安装 npm 依赖。Windows 发布工作流使用 Python 3.11，除安装、启动和卸载外，还检查打包后的首页 PNG 二维码、键盘页和本地脚本资源。

真机回归时，在 Android Chrome 和 iOS Safari 分别检查拼音选词、文字修改与粘贴、系统键盘弹出、横竖屏切换、全键盘长按后切换模式，以及断线和超时后的草稿保留。

---

## 📂 项目结构

* `server.py`: Python 后端逻辑，处理 Socket 信号并调用系统接口。
* `templates/index.html`: 触控板页面。
* `templates/keyboard.html`: 键盘输入页面。
* `templates/voice.html`: 语音输入页面。
* `macro.html`: 宏按键页面。
* `macro_config.json`: 宏按键配置文件。
---

## 🔧 调优说明
- 建议使用安卓手机+chrome浏览器。
- 虽然 ios  safari 浏览器也可以正常使用，但是鼠标的移动会变得卡卡的。

# macos相关
使用mac版本需要线修改一些py代码，才能正常使用。
```py
# 删除printscreen键

SPECIAL_KEYS = {
    'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    'shift': Key.shift, 'shift_r': Key.shift_r,
    'alt': Key.alt, 'alt_r': Key.alt_r,
    'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space, 'delete': Key.delete,
    'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12
}

# 修改滚动方向,它滚动方向和 Windows 是反过来的
@socketio.on('scroll')
def handle_scroll(data):
    # 处理双指滑动或按钮连发发来的滚动信号
    mouse.scroll(0, -data['dy']) 
```

    
## 更新日志
2026-01-23 Day3
- [x]  两个手指快速抬起导致识别成鼠标跳转修复
- [x]  “单指长按拖拽”功能
- [x]  将触控板逻辑提取为独立模块 `touchpad.js`，实现多页面同步更新


2026-01-21 Day2
- [x]  点击返回时强制清除所有长按功能，以防止影响触控
- [x]  飞鼠增加一些微小动作滤除，防手抖

- [x]  键盘上下左右 无效 另外位置也不舒服
- [x]  键盘del 按钮位置不对 应该在F12右边
- [x]  缺少printscreen 按钮
- [x]  缺少反斜杠按钮（在括号右边）

- [x]  输入条太小并不能实时语音上屏（之前让他实时上屏存在一点问题）
- [x]  或许我可以再搞个独立页面专门用来语音上屏,并且可以切换实时上屏和输入框模式
- [x]  记住gyro模式，如果之前是开启那么回到页面自动开启
- [x]  键盘模式默认就横过来展示，无视手机的方向（如果检测到是手机）
  
2026-01-21 Day1
- [x]  实现整体基础架构
- [x]  实现飞鼠功能还有鼠标控制功能以及三指拖动功能等
- [x]  实现键盘功能
