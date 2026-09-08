<sub>🌐 <a href="README.md">中文</a> · <b>English</b></sub>

<div align="center">

# Marketing Link Checker

### Turn repetitive pre-launch campaign link checks into reusable QA

**UTM · Discount Code · Redirect · Destination · Browser Check**

</div>

---

## Why I built it

Before an EDM / marketing campaign goes live, operators often need to repeatedly check:

- whether UTM / campaign parameters are correct
- whether discount codes are present and attached to the right URL
- where short links / deep links finally redirect
- whether the destination page opens successfully
- whether the final domain / site is correct

The work is repetitive, but one broken link can directly hurt campaign conversion.

This tool came from a real marketing workflow: **turn manual pre-launch link checking into repeatable QA.**

---

## What it checks

### Tracking parameters

Recognizes common parameters such as:

- `utm_*`
- `campaign / campaignid`
- `utm_campaign`
- `source / medium`
- other common ad-tracking parameters

### Discount codes

Recognizes:

- `discount_code`
- `discount`
- `coupon / coupon_code`
- `promo / promo_code`
- `code`

### Redirect chains

Supports:

- regular URLs
- nested URL parameters
- redirect / fallback links
- OneLink / short links
- final destination-domain checks

### Optional browser verification

When Node.js + Playwright are available, the service can perform real-browser opening checks for page issues that plain HTTP requests may miss.

---

## Workflow

```text
Paste campaign links
        ↓
Parse tracking parameters & nested URLs
        ↓
Validate discount / campaign parameters
        ↓
Follow redirects and final destination
        ↓
Optional Playwright browser check
        ↓
Summary / CSV export
```

---

## Usage

### Local

```powershell
python .\link_checker_app.py
```

Open:

```text
http://127.0.0.1:8765/
```

Or double-click:

```text
start-local.bat
```

### Team intranet

Set:

```text
HOST=0.0.0.0
PORT=8765
```

Then teammates on the same network can access the service through the host machine.

### Render / Railway / Heroku-style hosting

Start command:

```bash
python link_checker_app.py
```

---

## Real-browser checks

Install:

```bash
npm install
npx playwright install chromium
```

Configure:

```text
NODE_EXE=node
BROWSER_CHECK_SCRIPT=browser_check.mjs
```

---

## Security

Real campaign materials may contain internal parameters, discount codes or unpublished landing pages.

Recommended practice:

- prefer intranet deployment for team usage
- add authentication if deployed publicly
- never commit real internal campaign sheets to a public repository

---

## What this project demonstrates

This is not a tool built for the sake of coding.

It came from a specific operating problem:

> **Pre-launch QA is repetitive and easy to miss, while the cost of a broken campaign link is much higher than the cost of checking it.**

The goal was to turn operating rules into tool logic.

For an operations / marketing role, the project demonstrates:

- identifying standardization opportunities in repetitive work
- translating business rules into automated checks
- turning a personal efficiency tool into a reusable team SOP
- using AI / coding agents for real operating work, not just content generation

---

## Technical notes

- Python web service
- optional Node.js + Playwright browser verification
- Docker / Render / Railway deployment configs
- core service can run without additional third-party Python packages
