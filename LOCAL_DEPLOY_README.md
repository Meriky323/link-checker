# PatPat Link Checker 本地部署验收说明

## 1. 启动

双击：

```text
start-local.bat
```

或在 PowerShell 运行：

```powershell
cd "本文件夹路径"
.\start-local.ps1
```

## 2. 本机访问

打开：

```text
http://127.0.0.1:8765/
```

## 3. 给同一内网的 IT/同事访问

启动窗口会显示类似：

```text
http://192.168.x.x:8765/
```

把这个地址发给 IT。

## 4. 如果别人打不开

通常是 Windows 防火墙未放行端口。请 IT 放行：

```text
TCP 8765 inbound
```

管理员 PowerShell 可执行：

```powershell
New-NetFirewallRule -DisplayName "PatPat Link Checker 8765" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow
```

## 5. 停止服务

关闭启动窗口，或在窗口里按：

```text
Ctrl+C
```

## 6. 部署文件

核心文件：

- `link_checker_app.py`
- `browser_check.mjs`
- `start-local.ps1`
- `start-local.bat`

Docker/服务器部署文件：

- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `package.json`
