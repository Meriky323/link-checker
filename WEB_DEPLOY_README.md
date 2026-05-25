# PatPat 链接检查工具 - 网页部署说明

这个工具已经改成可部署的网页服务。部署后，团队成员可以通过一个网址访问，不需要在每个人电脑上运行本地脚本。

## 文件说明

- `link_checker_app.py`：主网页服务，包含页面和链接检查接口
- `browser_check.mjs`：浏览器真实打开检查脚本，可选功能
- `requirements.txt`：Python 依赖说明，当前主服务不需要额外 pip 包
- `package.json`：如果要启用“浏览器真实打开检查”，需要安装 Playwright
- `Procfile`：Heroku/Railway/Render 等平台可识别的启动命令
- `render.yaml`：Render 部署示例配置

## 推荐部署方式 1：公司内网服务器

适合处理公司物料表，不把链接数据放到公网。

1. 把整个文件夹复制到服务器。
2. 确认服务器有 Python 3.10+。
3. 设置环境变量：

```bat
set HOST=0.0.0.0
set PORT=8765
```

PowerShell：

```powershell
$env:HOST="0.0.0.0"
$env:PORT="8765"
python .\link_checker_app.py
```

4. 其他人访问：

```text
http://服务器IP:8765/
```

## 推荐部署方式 2：Render / Railway / Heroku 类平台

1. 把这些文件上传到一个 GitHub 仓库。
2. 在平台创建 Web Service。
3. 启动命令填写：

```bash
python link_checker_app.py
```

4. 环境变量设置：

```text
HOST=0.0.0.0
PORT=平台自动提供，一般不用手动设置
```

5. 部署完成后，平台会给你一个 HTTPS 网址。

## 关于“浏览器真实打开检查”

这个功能需要 Node.js、Playwright 和浏览器环境。部署到普通 Python 服务时，默认可能不可用。

如果要启用，需要服务器执行：

```bash
npm install
npx playwright install chromium
```

并确保 Python 服务能调用：

```text
NODE_EXE=node
BROWSER_CHECK_SCRIPT=browser_check.mjs
```

如果部署平台不支持浏览器沙盒，建议先使用：

- `检查链接`
- `检查链接与折扣码`

这两个功能不依赖 Playwright。

## 安全建议

物料表里可能包含内部 campaign、转链和折扣码。建议：

- 优先部署在公司内网
- 如果部署公网，至少加访问密码或登录限制
- 不建议把工具裸露给所有互联网用户

## 本地启动

在本机运行：

```powershell
python .\link_checker_app.py
```

然后打开：

```text
http://127.0.0.1:8765/
```
