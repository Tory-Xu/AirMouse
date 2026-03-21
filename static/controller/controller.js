const socket = io();
const v = () => { if (navigator.vibrate) navigator.vibrate(25); };

let gamepadStart = false;
let sensitivity = parseFloat(localStorage.getItem('gp_sens') || 5.0);
let deadzone = parseFloat(localStorage.getItem('gp_deadzone') || 0.15);

// 默认映射
const defaultMapping = {
    // 摇杆映射
    "axis_0": "mouse_move_x", 
    "axis_1": "mouse_move_y",
    "axis_2": "mouse_scroll_x",
    "axis_3": "mouse_scroll_y",
    
    // 按键映射
    "btn_0": "click_left",   // A / Cross
    "btn_1": "click_right",  // B / Circle
    "btn_2": "none",         // X / Square
    "btn_3": "key_esc",      // Y / Triangle
    "btn_4": "click_left",   // L1
    "btn_5": "click_right",  // R1
    "btn_6": "click_middle", // L2
    "btn_7": "drag",         // R2
    "btn_8": "key_space",    // Select
    "btn_9": "key_enter",    // Start
    "btn_10": "none",        // L3
    "btn_11": "none",        // R3
    "btn_12": "key_up",      // D-pad Up
    "btn_13": "key_down",    // D-pad Down
    "btn_14": "key_left",    // D-pad Left
    "btn_15": "key_right",   // D-pad Right
    "btn_16": "none"         // Guide
};

// 当前使用的映射
let currentMap = JSON.parse(localStorage.getItem('gp_mapping')) || defaultMapping;
let previousButtonStates = [];

// 初始化 UI
function initUI() {
    const sensInput = document.getElementById('param-sens');
    const sensVal = document.getElementById('sens-val');
    sensInput.value = sensitivity;
    sensVal.innerText = sensitivity.toFixed(1);

    sensInput.addEventListener('input', (e) => {
        sensitivity = parseFloat(e.target.value);
        sensVal.innerText = sensitivity.toFixed(1);
        localStorage.setItem('gp_sens', sensitivity);
    });

    const deadInput = document.getElementById('param-deadzone');
    const deadVal = document.getElementById('dead-val');
    deadInput.value = deadzone;
    deadVal.innerText = deadzone.toFixed(2);

    deadInput.addEventListener('input', (e) => {
        deadzone = parseFloat(e.target.value);
        deadVal.innerText = deadzone.toFixed(2);
        localStorage.setItem('gp_deadzone', deadzone);
    });

    const list = document.getElementById('mapping-list');
    const tpl = document.getElementById('map-select-template').innerHTML;

    // 渲染摇杆
    for(let i=0; i<4; i++) {
        let name = i === 0 ? "左摇杆 左右" : i === 1 ? "左摇杆 上下" : i === 2 ? "右摇杆 左右" : "右摇杆 上下";
        list.appendChild(createRow(`axis_${i}`, name, tpl, true));
    }

    // 渲染按键
    const btnNames = ["A 按键 (Cross)","B 按键 (Circle)","X 按键 (Square)","Y 按键 (Triangle)",
                      "L1 (LB)","R1 (RB)","L2 (LT)","R2 (RT)",
                      "Select (View)","Start (Menu)","左摇杆按下 (L3)","右摇杆按下 (R3)",
                      "十字键 上","十字键 下","十字键 左","十字键 右","系统导航键 Guide"];
    for(let i=0; i<17; i++) {
        list.appendChild(createRow(`btn_${i}`, btnNames[i] || `Button ${i}`, tpl, false));
    }
}

function createRow(id, name, templateHTML, isAxis) {
    const row = document.createElement('div');
    row.className = 'map-row';
    
    const label = document.createElement('span');
    label.className = 'map-label';
    label.innerText = name;

    const selectContainer = document.createElement('div');
    selectContainer.innerHTML = templateHTML;
    const select = selectContainer.querySelector('select');
    
    if (isAxis) {
        // 修改为对应的轴选项
        select.innerHTML = `
            <option value="none">无动作</option>
            <option value="mouse_move_x">鼠标 X 轴移动</option>
            <option value="mouse_move_y">鼠标 Y 轴移动</option>
            <option value="mouse_scroll_x">横向滚动</option>
            <option value="mouse_scroll_y">纵向滚动</option>
        `;
    }

    // 设置并监听
    if(currentMap[id]) select.value = currentMap[id];
    
    select.addEventListener('change', (e) => {
        currentMap[id] = e.target.value;
        localStorage.setItem('gp_mapping', JSON.stringify(currentMap));
    });

    row.appendChild(label);
    row.appendChild(selectContainer.firstElementChild);
    return row;
}

// 摇杆输入缓存
let moveX = 0, moveY = 0;
let scrollX = 0, scrollY = 0;
let isDragging = false;

// Polling Loop
function updateGamepad() {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    let activePad = null;
    
    for (let i = 0; i < gamepads.length; i++) {
        if (gamepads[i] && gamepads[i].connected) {
            activePad = gamepads[i];
            break;
        }
    }

    const statusEl = document.getElementById('gp-status');
    if (activePad) {
        if (!gamepadStart) {
            gamepadStart = true;
            statusEl.innerText = '🟢 已连接: ' + activePad.id;
            statusEl.classList.add('connected');
        }

        handleGamepadInput(activePad);
    } else {
        if (gamepadStart) {
            gamepadStart = false;
            statusEl.innerText = '🔴 等待手柄连接 (请按任意键唤醒)';
            statusEl.classList.remove('connected');
        }
    }

    requestAnimationFrame(updateGamepad);
}

function applyDeadzone(value) {
    return Math.abs(value) > deadzone ? value : 0;
}

function handleGamepadInput(pad) {
    // Axes
    moveX = 0; moveY = 0; scrollX = 0; scrollY = 0;

    for (let i = 0; i < pad.axes.length; i++) {
        let val = applyDeadzone(pad.axes[i]);
        if (val === 0) continue;
        
        const action = currentMap[`axis_${i}`];
        if (action === 'mouse_move_x') moveX += val * sensitivity * 4;
        if (action === 'mouse_move_y') moveY += val * sensitivity * 4;
        if (action === 'mouse_scroll_x') scrollX += val * sensitivity * 2;
        if (action === 'mouse_scroll_y') scrollY += val * sensitivity * 2;
    }

    if (moveX !== 0 || moveY !== 0) {
        socket.emit('move', { dx: moveX, dy: moveY });
    }
    if (scrollX !== 0 || scrollY !== 0) {
        socket.emit('scroll', { dx: scrollX, dy: scrollY });
    }

    // Buttons
    for (let i = 0; i < pad.buttons.length; i++) {
        const pressed = pad.buttons[i].pressed;
        const wasPressed = previousButtonStates[i] || false;
        
        if (pressed !== wasPressed) {
            handleButtonChange(i, pressed);
            previousButtonStates[i] = pressed;
        }
    }
}

function handleButtonChange(btnIndex, pressed) {
    const action = currentMap[`btn_${btnIndex}`];
    if (!action || action === 'none') return;

    if (action.startsWith('click_')) {
        if (pressed) {
            v();
            const btn = action.split('_')[1];
            socket.emit('click', { button: btn });
        }
    } else if (action === 'drag') {
        if (pressed) {
            v();
            isDragging = true;
            socket.emit('drag_start');
        } else {
            isDragging = false;
            socket.emit('drag_end');
        }
    } else if (action.startsWith('key_')) {
        const keyMap = {
            'key_space': 'space',
            'key_enter': 'enter',
            'key_esc': 'esc',
            'key_backspace': 'backspace',
            'key_up': 'up',
            'key_down': 'down',
            'key_left': 'left',
            'key_right': 'right'
        };
        const mappedKey = keyMap[action];
        if (mappedKey) {
            if (pressed) {
                v();
                socket.emit('key_action', { key: mappedKey, action: 'down' });
            } else {
                socket.emit('key_action', { key: mappedKey, action: 'up' });
            }
        }
    }
}

// 启动
document.addEventListener('DOMContentLoaded', () => {
    initUI();
    window.addEventListener("gamepadconnected", (e) => {
        console.log("Gamepad connected", e.gamepad);
    });
    requestAnimationFrame(updateGamepad);
});
