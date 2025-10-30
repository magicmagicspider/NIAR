#!/bin/bash
# Bettercap 工作模式查看脚本

echo "========================================"
echo "   Bettercap 双实例状态查询"
echo "========================================"
echo

# 1. 查看配置
echo "【1】双实例配置:"
curl -s http://localhost:8000/api/settings/bettercap | python3 -c "
import sys, json
try:
    config = json.load(sys.stdin)
    scan_url = config.get('scan_url', 'N/A')
    ban_url = config.get('ban_url', 'N/A')
    mode = config.get('probe_mode', 'N/A')
    throttle = config.get('probe_throttle', 'N/A')
    
    print(f'  🔍 扫描实例: {scan_url}')
    print(f'  🛡️  Ban实例: {ban_url}')
    print(f'  ⚙️  探测模式: {mode}')
    if mode == 'active':
        print(f'  ⏱️  探测间隔: {throttle} 秒')
except:
    print('  ❌ 无法获取配置')
"
echo

# 2. 查看扫描实例状态（8081）
echo "【2】扫描实例状态（端口8081）:"
curl -s -u user:pass http://127.0.0.1:8081/api/session 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    modules = data.get('modules', [])
    
    probe_running = False
    recon_running = False
    
    for module in modules:
        if isinstance(module, dict):
            name = module.get('name', '')
            running = module.get('running', False)
            if name == 'net.probe' and running:
                probe_running = True
            if name == 'net.recon' and running:
                recon_running = True
    
    if probe_running and recon_running:
        print('  ✅ net.probe: 运行中')
        print('  ✅ net.recon: 运行中')
        print('  🎯 状态: 正常扫描中')
    elif recon_running:
        print('  ✅ net.recon: 运行中')
        print('  ⚠️  net.probe: 未运行')
    else:
        print('  ⚠️  没有扫描模块运行')
except:
    print('  ❌ 无法连接到扫描实例API')
" || echo "  ❌ 扫描实例未运行"
echo

# 3. 查看Ban实例状态（8082）
echo "【3】Ban实例状态（端口8082）:"
curl -s -u user:pass http://127.0.0.1:8082/api/session 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    modules = data.get('modules', [])
    
    ban_running = False
    spoof_running = False
    
    for module in modules:
        if isinstance(module, dict):
            name = module.get('name', '')
            running = module.get('running', False)
            if name == 'arp.ban' and running:
                ban_running = True
            if name == 'arp.spoof' and running:
                spoof_running = True
    
    if ban_running and spoof_running:
        print('  ✅ arp.ban: 运行中')
        print('  ✅ arp.spoof: 运行中')
        print('  🎯 状态: 正在执行Ban')
    elif spoof_running:
        print('  ✅ arp.spoof: 运行中')
        print('  ⚠️  arp.ban: 未运行')
    else:
        print('  ℹ️  没有Ban模块运行（待命状态）')
except:
    print('  ❌ 无法连接到Ban实例API')
" || echo "  ❌ Ban实例未运行"
echo

# 4. 查看 Bettercap 任务状态
echo "【4】Bettercap 定时任务状态:"
curl -s http://localhost:8000/api/tasks/ | python3 -c "
import sys, json
try:
    tasks = json.load(sys.stdin)
    bettercap_tasks = [t for t in tasks if t.get('scan_tool') == 'bettercap']
    
    if bettercap_tasks:
        for task in bettercap_tasks:
            status = '✅ 运行中' if task.get('enabled') else '⏸️  已暂停'
            print(f\"  任务 {task['id']}: {task['name']} - {status}\")
            print(f\"    网段: {', '.join(task.get('cidrs', []))}\")
    else:
        print('  ⚠️  没有 Bettercap 任务')
except:
    print('  ❌ 无法获取任务列表')
"
echo

# 5. 查看扫描实例探测参数
echo "【5】扫描实例探测参数:"
curl -s -u user:pass http://127.0.0.1:8081/api/session 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    env = data.get('env', {})
    
    throttle = env.get('net.probe.throttle', 'N/A')
    timeout = env.get('net.probe.timeout', 'N/A')
    mdns = env.get('net.probe.mdns', 'N/A')
    targets = env.get('net.recon.targets', 'N/A')
    
    if throttle != 'N/A':
        print(f'  ⏱️  探测间隔: {throttle} 秒')
        print(f'  ⏰ 探测超时: {timeout} 秒')
        print(f'  📡 mDNS: {mdns}')
        print(f'  🎯 扫描目标: {targets}')
    else:
        print('  ℹ️  参数未设置（可能任务未运行或使用默认值）')
except:
    print('  ❌ 无法获取参数')
" || echo "  ❌ 无法连接到 Bettercap"

echo
echo "========================================"
echo "查询完成！"
echo "========================================"

