<sub>🌐 <b>中文</b> · <a href="README.en.md">English</a></sub>

<div align="center">

# Marketing Link Checker

### 把 Campaign 上线前的人工链接核对，变成可重复的自动质检

**UTM · Discount Code · Redirect · Destination · Browser Check**

</div>

---

## 为什么做这个工具

在 EDM / Campaign 上线前，运营通常需要反复检查：

- UTM / Campaign 参数有没有填错
- 折扣码有没有漏、有没有带到正确链接
- 短链 / 深链最终跳到哪里
- 页面是否正常打开
- 是否跳到正确站点

这类工作机械、重复，但一个链接错误就可能直接影响活动转化。

这个工具来自真实邮件运营流程：**把“上线前人工逐条核对”沉淀成一个可重复的 QA 工具。**

---

## 能检查什么

### 链接与追踪参数

识别常见：

- `utm_*`
- `campaign / campaignid`
- `utm_campaign`
- `source / medium`
- 其他常见广告追踪参数

### 折扣码

支持识别：

- `discount_code`
- `discount`
- `coupon / coupon_code`
- `promo / promo_code`
- `code`

### 跳转链路

支持检查：

- 常规 URL
- 嵌套 URL 参数
- Redirect / Fallback
- OneLink / Shortlink
- 最终目标站点

### 可选浏览器检查

如服务器环境安装 Node.js + Playwright，可启用真实浏览器打开验证，用于发现仅靠 HTTP 请求难以识别的页面问题。

---

## 工作流

```text
输入 / 粘贴 Campaign 链接
        ↓
解析追踪参数与嵌套链接
        ↓
检查折扣码 / Campaign 参数
        ↓
跟踪 Redirect 与最终目标页
        ↓
可选：Playwright 真实浏览器检查
        ↓
结果汇总 / CSV 导出
```

---

## 使用方式

### 本地运行

```powershell
python .\link_checker_app.py
```

浏览器访问：

```text
http://127.0.0.1:8765/
```

也可以直接双击：

```text
start-local.bat
```

### 团队内网

设置：

```text
HOST=0.0.0.0
PORT=8765
```

同一内网的团队成员即可通过服务器地址访问。

### Render / Railway / Heroku 类平台

启动命令：

```bash
python link_checker_app.py
```

---

## 浏览器真实打开检查

安装：

```bash
npm install
npx playwright install chromium
```

配置：

```text
NODE_EXE=node
BROWSER_CHECK_SCRIPT=browser_check.mjs
```

---

## 安全说明

真实 Campaign 链接可能包含内部活动参数、折扣码或未公开页面。

因此：

- 团队使用优先部署在公司内网
- 如部署公网，建议增加访问密码 / 登录限制
- 不要把真实内部物料表公开上传到仓库

---

## 这个项目想证明什么

它不是一个“为了写代码而写的工具”。

它来自一个非常具体的运营问题：

> **Campaign 上线前的人工 QA 重复、容易漏检，而且错误成本比检查成本高。**

我做的事情是把这段流程拆成规则，再交给工具自动执行。

对运营岗位来说，这个项目更想证明：

- 能识别重复工作中的标准化机会
- 能把业务规则转成工具逻辑
- 能把个人效率工具沉淀为团队 SOP
- AI / Coding Agent 可以服务真实运营，而不是只生成内容

---

## 技术说明

- Python Web Service
- 可选 Node.js + Playwright 浏览器验证
- Docker / Render / Railway 部署配置
- 主服务可在无额外 Python 三方依赖的情况下运行
