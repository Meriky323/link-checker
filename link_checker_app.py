from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler, HTTPHandler

PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("HOST", "127.0.0.1")
APP_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_EXE = os.environ.get("NODE_EXE", "node")
BROWSER_CHECK_SCRIPT = os.environ.get("BROWSER_CHECK_SCRIPT", os.path.join(APP_DIR, "browser_check.mjs"))
MAX_REDIRECTS = 8
TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {
    "fbclid", "gclid", "gbraid", "wbraid", "msclkid", "yclid", "irclickid",
    "campaign", "campaignid", "adset", "adsetid", "adid", "creative", "source", "medium",
}
CANDIDATE_PARAMS = (
    "af_web_dp", "af_ios_url", "af_android_url", "deep_link_value", "link", "url", "target", "target_url",
    "redirect", "redirect_url", "fallback", "fallback_url", "web_url", "pc_url",
)
DISCOUNT_PARAM_KEYS = ("discount_code", "discount", "coupon", "coupon_code", "promo", "promo_code", "code")
CAMPAIGN_PARAM_KEYS = ("c", "campaign", "utm_campaign", "shortlink")
UTM_PARAM_KEYS = ("utm_term", "utm_campaign", "utm_source", "utm_medium", "c")
NESTED_URL_PARAM_KEYS = CANDIDATE_PARAMS + ("deep_link_sub1", "deep_link_sub2", "deep_link_sub3", "deep_link_sub4", "deep_link_sub5")
SHORTLINK_HOST_PARTS = ("onelink.me", "app.link", "lnk.to", "bit.ly", "tinyurl.com")
TARGET_HOSTS = ("patpat.com",)
HTML_REDIRECT_PATTERNS = (
    re.compile(r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]+content=[\"'][^\"']*url=([^\"';>]+)", re.I),
    re.compile(r"(?:window|document)\.location(?:\.href)?\s*=\s*[\"']([^\"']+)", re.I),
    re.compile(r"location\.replace\(\s*[\"']([^\"']+)", re.I),
)

HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>飞书物料表链接检查工具</title>
  <style>
    :root {
      --pink: #ff4fb8;
      --hot: #ff315a;
      --orange: #ff8a00;
      --sun: #ffd400;
      --green: #17c964;
      --cyan: #00d5ff;
      --blue: #3264ff;
      --purple: #8b5cf6;
      --ink: #191326;
      --muted: #6f5d7c;
      --paper: rgba(255,255,255,.88);
      --line: rgba(25,19,38,.12);
      --shadow: 0 26px 70px rgba(119, 31, 103, .18);
      --shadow-pop: 0 16px 0 rgba(25,19,38,.08), 0 28px 60px rgba(255,79,184,.18);
      --radius-xl: 30px;
      --radius-md: 18px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
      background:
        radial-gradient(circle at 8% 10%, rgba(255,79,184,.34), transparent 18rem),
        radial-gradient(circle at 92% 4%, rgba(255,212,0,.42), transparent 22rem),
        radial-gradient(circle at 18% 88%, rgba(0,213,255,.32), transparent 24rem),
        linear-gradient(135deg, #fff7ad 0%, #ffe3f4 34%, #dff8ff 68%, #ecffe8 100%);
      overflow-x: hidden;
    }
    body::before, body::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
    }
    body::before {
      opacity: .45;
      background-image:
        radial-gradient(circle, rgba(255,49,90,.38) 0 5px, transparent 6px),
        radial-gradient(circle, rgba(50,100,255,.3) 0 4px, transparent 5px),
        linear-gradient(90deg, rgba(255,255,255,.28) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,.28) 1px, transparent 1px);
      background-size: 120px 120px, 96px 96px, 32px 32px, 32px 32px;
      background-position: 12px 18px, 70px 44px, 0 0, 0 0;
      mask-image: linear-gradient(to bottom, #000, transparent 90%);
    }
    body::after {
      background:
        conic-gradient(from 10deg at 82% 78%, rgba(255,138,0,.16), rgba(255,79,184,.16), rgba(0,213,255,.12), rgba(255,138,0,.16));
      filter: blur(22px);
      opacity: .8;
    }
    .page {
      position: relative;
      z-index: 1;
      max-width: 1360px;
      margin: 0 auto;
      padding: 26px 22px 52px;
      animation: pagePop .5s cubic-bezier(.2,.9,.2,1) both;
    }
    @keyframes pagePop { from { opacity: 0; transform: translateY(14px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
    .paste-panel {
      position: relative;
      border: 3px solid rgba(255,255,255,.8);
      border-radius: var(--radius-xl);
      background: linear-gradient(145deg, rgba(255,255,255,.92), rgba(255,255,255,.72));
      box-shadow: var(--shadow-pop);
      overflow: hidden;
      backdrop-filter: blur(18px) saturate(1.25);
    }
    .paste-panel::before {
      content: "LINKS MAKE WORK EXCEL!";
      position: absolute;
      left: 22px;
      top: 74px;
      z-index: 0;
      font-size: clamp(34px, 6vw, 78px);
      font-weight: 1000;
      letter-spacing: -.06em;
      line-height: .85;
      color: rgba(255,79,184,.08);
      transform: rotate(-2deg);
      pointer-events: none;
    }
    .paste-panel::after {
      content: "";
      position: absolute;
      right: -72px;
      top: -84px;
      width: 260px;
      height: 260px;
      border-radius: 52% 48% 42% 58%;
      background: conic-gradient(from 20deg, var(--pink), var(--sun), var(--green), var(--cyan), var(--purple), var(--pink));
      opacity: .28;
      animation: blobSpin 9s linear infinite;
    }
    @keyframes blobSpin { to { transform: rotate(360deg); } }
    .panel-head {
      position: relative;
      z-index: 2;
      min-height: 96px;
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 0 220px 0 22px;
      border-bottom: 2px dashed rgba(25,19,38,.12);
      background: linear-gradient(90deg, rgba(255,79,184,.16), rgba(255,212,0,.18), rgba(0,213,255,.14));
      font-size: 19px;
      font-weight: 1000;
      letter-spacing: .02em;
    }
    .panel-head::after {
      content: "告别 Excel 手动核对，Make Link Checking Easy Today!";
      margin-left: auto;
      padding: 9px 15px;
      border-radius: 999px;
      color: #fff;
      background: linear-gradient(90deg, var(--hot), var(--orange), var(--blue));
      box-shadow: 0 10px 24px rgba(255,49,90,.22);
      font-size: 13px;
      white-space: nowrap;
    }
    .chevron {
      width: 36px;
      height: 36px;
      display: inline-grid;
      place-items: center;
      border-radius: 13px;
      background: #fff;
      color: var(--hot);
      font-size: 24px;
      box-shadow: 0 7px 0 rgba(25,19,38,.08);
    }
    .panel-body { position: relative; z-index: 2; padding: 22px 18px 20px; }
    .desc { max-width: 900px; margin: 0 0 20px; color: var(--muted); font-size: 14px; line-height: 1.75; font-weight: 700; }
    .desc::before { content: "🌈 "; }
    .paste-grid { display: grid; grid-template-columns: .74fr 1.34fr 1.34fr .9fr; gap: 16px; }
    label { display: block; margin: 0 0 8px; color: #37233f; font-size: 13px; font-weight: 1000; letter-spacing: .01em; }
    label::before { content: "✦ "; color: var(--pink); }
    textarea, input, select {
      width: 100%;
      border: 2px solid rgba(25,19,38,.1);
      border-radius: var(--radius-md);
      background: rgba(255,255,255,.93);
      color: #2b1735;
      font: inherit;
      outline: none;
      transition: border-color .16s ease, box-shadow .16s ease, background .16s ease, transform .16s ease;
    }
    textarea {
      height: 164px;
      padding: 15px 15px 15px 18px;
      resize: vertical;
      line-height: 1.55;
      box-shadow: inset 6px 0 0 var(--pink), 0 12px 24px rgba(139,92,246,.08);
      font-family: Consolas, "Microsoft YaHei", monospace;
    }
    textarea:nth-of-type(2n), input:nth-of-type(2n) { box-shadow: inset 6px 0 0 var(--cyan), 0 12px 24px rgba(0,213,255,.08); }
    textarea::placeholder, input::placeholder { color: #aa93b3; }
    textarea:focus, input:focus, select:focus {
      border-color: var(--pink);
      box-shadow: 0 0 0 5px rgba(255,79,184,.16), 0 16px 30px rgba(255,79,184,.14);
      background: #fff;
      transform: translateY(-1px);
    }
    .paste-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 17px; }
    button {
      height: 50px;
      border: 0;
      border-radius: 999px;
      background: linear-gradient(135deg, #fff, #fff4fb);
      color: var(--ink);
      font: inherit;
      font-weight: 1000;
      cursor: pointer;
      box-shadow: 0 8px 0 rgba(25,19,38,.1), 0 18px 34px rgba(255,79,184,.14);
      transition: transform .14s ease, box-shadow .14s ease, opacity .14s ease, filter .14s ease;
    }
    button:hover { transform: translateY(-3px) rotate(-.3deg); box-shadow: 0 11px 0 rgba(25,19,38,.08), 0 24px 42px rgba(50,100,255,.18); }
    button:active { transform: translateY(2px); box-shadow: 0 4px 0 rgba(25,19,38,.12); }
    button:disabled { opacity: .55; cursor: not-allowed; transform: none; filter: grayscale(.25); }
    .toolbar {
      display: grid;
      grid-template-columns: 200px 202px 238px 1fr;
      gap: 18px;
      align-items: start;
      margin: 24px 0 22px;
    }
    .stack { display: grid; gap: 12px; }
    .toolbar select, .toolbar input { height: 42px; padding: 0 15px; border-radius: 999px; background: rgba(255,255,255,.92); box-shadow: 0 10px 20px rgba(50,100,255,.09); }
    .primary { background: linear-gradient(135deg, var(--blue), var(--cyan)); color: white; }
    .green { background: linear-gradient(135deg, var(--green), #8be04e); color: #0c2d16; }
    #runCheck { background: linear-gradient(135deg, var(--hot), var(--orange), var(--sun)); color: white; }
    #exportCsv { background: linear-gradient(135deg, var(--purple), var(--pink)); color: white; }
    .ghost { background: rgba(255,255,255,.72); }
    .meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(110px, 1fr));
      gap: 11px;
    }
    .stat {
      min-height: 72px;
      padding: 12px 14px;
      border-radius: 22px;
      border: 2px solid rgba(255,255,255,.72);
      background: linear-gradient(145deg, rgba(255,255,255,.9), rgba(255,244,251,.82));
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
      box-shadow: 0 10px 0 rgba(25,19,38,.06), 0 20px 38px rgba(139,92,246,.12);
    }
    .stat:nth-child(1) { background: linear-gradient(145deg, #fff, #fff4b8); }
    .stat:nth-child(2) { background: linear-gradient(145deg, #fff, #d9ffd9); }
    .stat:nth-child(3) { background: linear-gradient(145deg, #fff, #ffd9e8); }
    .stat:nth-child(4) { background: linear-gradient(145deg, #fff, #dff6ff); }
    .stat b { display: block; margin-top: 5px; color: var(--ink); font-size: 28px; line-height: 1; }
    .table-shell { overflow: auto; padding: 4px 0 8px; }
    .data-grid {
      width: 100%;
      min-width: 1200px;
      border-collapse: separate;
      border-spacing: 0 12px;
    }
    .data-grid th {
      padding: 0 10px 6px 0;
      text-align: left;
      font-size: 12px;
      font-weight: 1000;
      color: #3b1750;
      letter-spacing: .02em;
    }
    .data-grid th span { display: inline-block; padding: 5px 10px; border-radius: 999px; background: linear-gradient(90deg, #fff, #fff0f9); border: 2px solid rgba(255,79,184,.18); box-shadow: 0 8px 18px rgba(255,79,184,.08); }
    .data-grid td { padding: 0 10px 0 0; }
    .data-grid input {
      height: 42px;
      padding: 0 13px;
      border-radius: 16px;
      background: rgba(255,255,255,.94);
      box-shadow: 0 10px 22px rgba(50,100,255,.07);
    }
    .data-grid tr { animation: rowIn .24s ease both; }
    @keyframes rowIn { from { opacity: .4; transform: translateY(6px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } }
    .seq { width: 128px; }
    .web { width: 420px; }
    .app { width: 420px; }
    .labelcol { width: 250px; }
    .result { width: 340px; }
    .status-ok, .status-bad, .status-warn {
      display: inline-block;
      margin-bottom: 4px;
      padding: 3px 10px;
      border-radius: 999px;
      font-weight: 1000;
    }
    .status-ok { color: #073d1e; background: linear-gradient(90deg, #b7ffca, #e9ff9b); }
    .status-bad { color: #67111a; background: linear-gradient(90deg, #ffd0de, #ffd9a6); }
    .status-warn { color: #5b3a00; background: linear-gradient(90deg, #fff0a6, #ffd6f0); }
    .status-cell { font-size: 13px; line-height: 1.5; color: #563b60; font-weight: 700; }
    .hint {
      margin: 14px 0 0;
      padding: 14px 16px;
      color: #4a3556;
      font-size: 13px;
      line-height: 1.65;
      border: 2px solid rgba(255,255,255,.78);
      border-radius: 20px;
      background: linear-gradient(90deg, rgba(255,255,255,.82), rgba(255,240,249,.72));
      box-shadow: 0 12px 28px rgba(139,92,246,.1);
      font-weight: 800;
    }
    .empty {
      padding: 38px 0;
      color: var(--muted);
      text-align: center;
      border: 3px dashed rgba(255,79,184,.28);
      border-radius: 24px;
      background: rgba(255,255,255,.72);
      box-shadow: var(--shadow);
      font-weight: 900;
    }
    .mascot {
      position: absolute;
      right: 26px;
      top: -18px;
      z-index: 3;
      width: 172px;
      height: 126px;
      pointer-events: auto;
      cursor: grab;
      transform-origin: 50% 82%;
    }
    .mascot::after {
      content: "摸摸我～";
      position: absolute;
      right: 10px;
      top: -26px;
      padding: 5px 10px;
      border-radius: 999px;
      background: #fff;
      color: #ff4fb8;
      border: 2px solid rgba(255,79,184,.28);
      font-size: 12px;
      font-weight: 1000;
      opacity: 0;
      transform: translateY(8px) scale(.92);
      transition: .18s ease;
      white-space: nowrap;
      box-shadow: 0 10px 20px rgba(255,79,184,.14);
    }
    .mascot:hover::after { opacity: 1; transform: translateY(0) scale(1); }
    .mascot:hover { animation: petHappy .56s ease-in-out infinite; }
    @keyframes petHappy {
      0%,100% { transform: translateX(0) translateY(0) rotate(-2deg) scale(1); }
      25% { transform: translateX(-8px) translateY(-3px) rotate(-5deg) scale(1.025); }
      50% { transform: translateX(8px) translateY(-5px) rotate(5deg) scale(1.04); }
      75% { transform: translateX(-4px) translateY(-2px) rotate(-3deg) scale(1.02); }
    }
    .mascot .dog-body {
      position: absolute;
      left: 50px;
      top: 62px;
      width: 74px;
      height: 54px;
      border-radius: 38px 38px 28px 28px;
      background: #fff5e8;
      border: 4px solid #24142e;
      box-shadow: 0 8px 0 rgba(25,19,38,.1);
    }
    .mascot .dog-spot { position: absolute; left: 9px; top: 11px; width: 24px; height: 20px; border-radius: 50%; background: #f4b26b; opacity: .9; }
    .mascot .dog-head {
      position: absolute;
      left: 38px;
      top: 22px;
      width: 90px;
      height: 70px;
      border-radius: 48% 48% 44% 44%;
      background: #fff5e8;
      border: 4px solid #24142e;
      box-shadow: 0 7px 0 rgba(25,19,38,.1);
      z-index: 2;
    }
    .mascot .ear { position: absolute; top: 30px; width: 30px; height: 46px; background: #f4b26b; border: 4px solid #24142e; border-radius: 60% 60% 72% 72%; transform-origin: 50% 0; z-index: 1; }
    .mascot .ear.left { left: 25px; transform: rotate(28deg); }
    .mascot .ear.right { left: 112px; transform: rotate(-28deg); }
    .mascot .bow { position: absolute; left: 68px; top: 4px; width: 36px; height: 25px; z-index: 4; animation: bowBounce 2.2s ease-in-out infinite; }
    .mascot .bow::before, .mascot .bow::after { content: ""; position: absolute; top: 2px; width: 18px; height: 18px; border-radius: 50% 45% 50% 45%; background: var(--pink); border: 3px solid #24142e; }
    .mascot .bow::before { left: 0; transform: rotate(-28deg); }
    .mascot .bow::after { right: 0; transform: rotate(28deg); }
    .mascot .bow-knot { position: absolute; left: 13px; top: 8px; width: 11px; height: 11px; border-radius: 50%; background: #ffd400; border: 3px solid #24142e; z-index: 5; }
    @keyframes bowBounce { 0%,100% { transform: translateY(0) rotate(-3deg); } 50% { transform: translateY(-2px) rotate(4deg); } }
    .mascot .eye { position: absolute; top: 49px; width: 8px; height: 10px; border-radius: 50%; background: #24142e; animation: puppyBlink 5s infinite; z-index: 4; }
    .mascot .eye.left { left: 65px; } .mascot .eye.right { left: 98px; }
    @keyframes puppyBlink { 0%, 92%, 100% { transform: scaleY(1); } 95% { transform: scaleY(.12); } }
    .mascot .nose { position: absolute; left: 81px; top: 62px; width: 12px; height: 9px; border-radius: 50%; background: #24142e; z-index: 4; }
    .mascot .smile { position: absolute; left: 73px; top: 70px; width: 28px; height: 13px; border-bottom: 3px solid #24142e; border-radius: 0 0 20px 20px; z-index: 4; }
    .mascot .paw { position: absolute; top: 97px; width: 20px; height: 18px; border-radius: 50%; background: #fff5e8; border: 4px solid #24142e; z-index: 3; }
    .mascot .paw.left { left: 58px; } .mascot .paw.right { left: 96px; }
    .mascot .leg { position: absolute; top: 104px; width: 18px; height: 18px; border-radius: 50%; background: #f4b26b; border: 4px solid #24142e; z-index: 2; }
    .mascot .leg.one { left: 48px; } .mascot .leg.two { left: 108px; } .mascot .leg.three { display: none; }
    .mascot .heart { position: absolute; color: var(--pink); font-size: 20px; opacity: 0; z-index: 6; pointer-events: none; text-shadow: 0 3px 0 rgba(25,19,38,.1); }
    .mascot .heart.one { left: 18px; top: 10px; }
    .mascot .heart.two { left: 130px; top: 22px; animation-delay: .15s; }
    .mascot .heart.three { left: 82px; top: -12px; animation-delay: .3s; }
    .mascot:hover .heart { animation: heartPop 1.05s ease-out infinite; }
    @keyframes heartPop { 0% { opacity: 0; transform: translateY(8px) scale(.45) rotate(-10deg); } 30% { opacity: 1; } 100% { opacity: 0; transform: translateY(-34px) scale(1.25) rotate(12deg); } }
    .mascot .spark { position: absolute; font-size: 22px; animation: sparkle 1.8s ease-in-out infinite; }
    .mascot .spark.one { right: 8px; top: 72px; color: var(--sun); }
    .mascot .spark.two { left: 6px; top: 78px; color: var(--hot); animation-delay: .45s; }
    @keyframes sparkle { 0%,100% { transform: scale(.7) rotate(0); opacity: .65; } 50% { transform: scale(1.16) rotate(14deg); opacity: 1; } }    @media (max-width: 1100px) { .mascot { display: none; } .panel-head { padding: 0 22px; min-height: 70px; } .panel-head::after { display: none; } }
    @media (max-width: 920px) {
      .paste-grid, .paste-actions, .toolbar, .meta { grid-template-columns: 1fr; }
      .page { padding: 14px; }
      .paste-panel { border-radius: 24px; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="paste-panel">
      <div class="mascot" aria-label="可爱的小狗吉祥物">
        <span class="spark one">✦</span>
        <span class="spark two">❤</span>
        <span class="heart one">❤</span>
        <span class="heart two">❤</span>
        <span class="heart three">❤</span>
        <div class="bow"><span class="bow-knot"></span></div>
        <div class="ear left"></div>
        <div class="ear right"></div>
        <div class="dog-head"></div>
        <div class="eye left"></div>
        <div class="eye right"></div>
        <div class="nose"></div>
        <div class="smile"></div>
        <div class="dog-body"><span class="dog-spot"></span></div>
        <div class="paw left"></div>
        <div class="paw right"></div>
        <div class="leg one"></div>
        <div class="leg two"></div>
      </div>
      <div class="panel-head"><span class="chevron">⌄</span><span>按列批量粘贴</span></div>
      <div class="panel-body">
        <p class="desc">适合直接复制整列内容。每列按行对齐，空白会自动补齐。核心是 Web 链接与转链两列；如果 Web 链接里带 /discount/折扣码，工具会一起检查折扣码是否能被识别和保留。</p>
        <div class="paste-grid">
          <div>
            <label for="pasteSeq">序号列</label>
            <textarea id="pasteSeq" placeholder="01&#10;02&#10;03"></textarea>
          </div>
          <div>
            <label for="pasteWeb">Web链接列</label>
            <textarea id="pasteWeb" placeholder="在这里粘贴 Web 链接列，每行一个链接"></textarea>
          </div>
          <div>
            <label for="pasteApp">转链列</label>
            <textarea id="pasteApp" placeholder="在这里粘贴转链列，每行一个转链"></textarea>
          </div>
          <div>
            <label for="pasteLabel">备注/标题列</label>
            <textarea id="pasteLabel" placeholder="可选：备注、标题或模块名"></textarea>
          </div>
        </div>
        <div class="paste-actions">
          <button id="overwrite">按列导入并覆盖当前行</button>
          <button id="append">按列追加到当前行</button>
        </div>
        <div style="margin-top:16px">
          <label for="discountMap">活动标记到折扣码映射（可选，每行一个：活动标记=折扣码）</label>
          <textarea id="discountMap" style="height:88px" placeholder="活动标记=折扣码&#10;例如：campaign01=CODE123"></textarea>
        </div>
        <div style="margin-top:16px">
          <label for="expectedUtm">期望 UTM（可选）</label>
          <input id="expectedUtm" placeholder="输入本次邮件对应的 UTM 标记" />
        </div>
      </div>
    </section>

    <section class="toolbar">
      <button id="addRow">Add Row</button>
      <div class="stack">
        <select id="deleteCount"><option>1</option><option>2</option><option>5</option><option>10</option><option>20</option></select>
        <button id="deleteRow">Delete Row</button>
      </div>
      <div class="stack">
        <button id="runLinkCheck" class="primary">检查链接</button>
        <button id="runBrowserCheck" class="primary">浏览器真实打开检查</button>
        <button id="runCheck" class="green">检查链接与折扣码</button>
        <button id="exportCsv" class="green" disabled>导出结果 CSV</button>
      </div>
      <div class="meta">
        <div class="stat">总行数 <b id="total">0</b></div>
        <div class="stat">匹配 <b id="ok">0</b></div>
        <div class="stat">不匹配 <b id="bad">0</b></div>
        <div class="stat">待确认/错误 <b id="err">0</b></div>
      </div>
    </section>

    <section id="gridHost" class="table-shell"></section>
    <p id="hint" class="hint">提示：如果不同组链接都带同一个折扣码，请填写“期望 UTM”，工具会额外检查转链里的 utm_term / utm_campaign / c 是否匹配，避免混组误判。</p>
  </main>

<script>
const $ = id => document.getElementById(id);
let rows = [];
let lastResults = [];

function lines(id) {
  const text = $(id).value.replace(/\r/g, '');
  if (!text.trim()) return [];
  return text.split('\n').map(v => v.trim()).filter((v, i, arr) => v || i < arr.length - 1);
}
function maxLen(...cols) { return Math.max(0, ...cols.map(c => c.length)); }
function rowFromColumns(i, seq, web, app, label) {
  return {
    sequence_no: seq[i] || (String(i + 1).padStart(2, '0')),
    web_link: web[i] || '',
    tracking_link: app[i] || '',
    note: label[i] || ''
  };
}
function importColumns(mode) {
  const seq = lines('pasteSeq'), web = lines('pasteWeb'), app = lines('pasteApp'), label = lines('pasteLabel');
  const count = maxLen(seq, web, app, label);
  if (!count) { alert('请先在上方至少粘贴一列内容。'); return; }
  const incoming = Array.from({length: count}, (_, i) => rowFromColumns(i, seq, web, app, label));
  rows = mode === 'append' ? rows.concat(incoming) : incoming;
  lastResults = [];
  renderRows();
  setStats([]);
  $('exportCsv').disabled = true;
}
function addRow() {
  rows.push({sequence_no: String(rows.length + 1).padStart(2, '0'), web_link: '', tracking_link: '', note: ''});
  renderRows();
}
function deleteRows() {
  const n = Number($('deleteCount').value || 1);
  rows.splice(Math.max(0, rows.length - n), n);
  lastResults = [];
  renderRows();
  setStats([]);
  $('exportCsv').disabled = true;
}
function updateCell(index, key, value) { rows[index][key] = value; }
    function statusClass(status) {
      if (status === '匹配') return 'status-ok';
      if (status === '不匹配') return 'status-bad';
      return 'status-warn';
    }
function resultFor(i) { return lastResults.find(r => Number(r.row) === i + 2); }
function renderRows() {
  const host = $('gridHost');
  if (!rows.length) {
    host.innerHTML = '<div class="empty">还没有行。可以点击 Add Row，或在上方按列粘贴后导入。</div>';
    $('total').textContent = 0;
    return;
  }
  const body = rows.map((r, i) => {
    const result = resultFor(i);
    const status = result ? `<span class="${statusClass(result.status)}">${result.status}</span><br>${escapeHtml(result.message || '')}` : '';
    return `<tr>
      <td class="seq"><input value="${escapeAttr(r.sequence_no)}" oninput="updateCell(${i}, 'sequence_no', this.value)"></td>
      <td class="web"><input value="${escapeAttr(r.web_link)}" oninput="updateCell(${i}, 'web_link', this.value)"></td>
      <td class="app"><input value="${escapeAttr(r.tracking_link)}" oninput="updateCell(${i}, 'tracking_link', this.value)"></td>
      <td class="labelcol"><input value="${escapeAttr(r.note)}" oninput="updateCell(${i}, 'note', this.value)"></td>
      <td class="result status-cell">${status}</td>
    </tr>`;
  }).join('');
  host.innerHTML = `<table class="data-grid"><thead><tr>
    <th class="seq"><span>sequence_no</span></th>
    <th class="web"><span>web_link</span></th>
    <th class="app"><span>tracking_link</span></th>
    <th class="labelcol"><span>note/title</span></th>
    <th class="result"><span>check_result / discount</span></th>
  </tr></thead><tbody>${body}</tbody></table>`;
  $('total').textContent = rows.length;
}
function escapeHtml(v) { return String(v ?? '').replace(/[&<>]/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[s])); }
function escapeAttr(v) { return escapeHtml(v).replace(/"/g, '&quot;'); }
function csvEscape(v) { return '"' + String(v ?? '').replace(/"/g, '""') + '"'; }
function parseDiscountMap() {
  const map = {};
  $('discountMap').value.split(/\r?\n/).forEach(line => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) return;
    const idx = trimmed.indexOf('=');
    if (idx <= 0) return;
    const marker = trimmed.slice(0, idx).trim();
    const code = trimmed.slice(idx + 1).trim();
    if (marker && code) map[marker] = code;
  });
  return map;
}
function setStats(results) {
  $('total').textContent = rows.length || results.length;
  $('ok').textContent = results.filter(r => r.status === '匹配').length;
  $('bad').textContent = results.filter(r => r.status === '不匹配').length;
  $('err').textContent = results.filter(r => r.status !== '匹配' && r.status !== '不匹配').length;
}
async function runCheck(mode = 'withDiscount') {
  if (!rows.length) { alert('请先添加或导入数据行。'); return; }
  const buttons = [$('runLinkCheck'), $('runBrowserCheck'), $('runCheck')];
  const activeButton = mode === 'browser' ? $('runBrowserCheck') : (mode === 'linkOnly' ? $('runLinkCheck') : $('runCheck'));
  buttons.forEach(button => button.disabled = true);
  activeButton.disabled = true;
  $('hint').textContent = mode === 'browser' ? '正在用浏览器真实打开转链，请稍等...' : (mode === 'linkOnly' ? '正在检查链接落地页，请稍等...' : '正在检查链接与折扣码，请稍等...');
  const payloadRows = rows.map((r, i) => ({...r, __rowNumber: i + 2}));
  try {
    const res = await fetch('/api/check', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ rows: payloadRows, pcColumn: 'web_link', linkColumn: 'tracking_link', timeout: 15, checkDiscount: mode === 'withDiscount', browserMode: mode === 'browser', discountMap: parseDiscountMap(), expectedUtm: $('expectedUtm').value.trim() })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '检查失败');
    lastResults = data.results;
    setStats(lastResults);
    renderRows();
    $('exportCsv').disabled = false;
    $('hint').textContent = `完成：${new Date().toLocaleTimeString()}`;
  } catch (err) {
    alert(err.message);
    $('hint').textContent = '检查失败，请看提示后重试。';
  } finally {
    buttons.forEach(button => button.disabled = false);
  }
}
function exportCsv() {
  const header = ['sequence_no','web_link','tracking_link','note','状态','最终落地','折扣码检测','说明'];
  const lines = rows.map((r, i) => {
    const res = resultFor(i) || {};
    return [r.sequence_no, r.web_link, r.tracking_link, r.note, res.status || '', res.final || '', res.discount || '', res.message || ''].map(csvEscape).join(',');
  });
  const blob = new Blob(['\uFEFF' + header.map(csvEscape).join(',') + '\n' + lines.join('\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'link-check-results.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}
$('overwrite').onclick = () => importColumns('overwrite');
$('append').onclick = () => importColumns('append');
$('addRow').onclick = addRow;
$('deleteRow').onclick = deleteRows;
$('runLinkCheck').onclick = () => runCheck('linkOnly');
$('runBrowserCheck').onclick = () => runCheck('browser');
$('runCheck').onclick = () => runCheck('withDiscount');
$('exportCsv').onclick = exportCsv;
rows = [];
renderRows();
setStats([]);
</script>
</body>
</html>
"""

class RedirectRecorder(HTTPRedirectHandler):
    def __init__(self):
        self.chain = []
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if len(self.chain) >= MAX_REDIRECTS:
            raise HTTPError(req.full_url, code, "too many redirects", headers, fp)
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme:
        parsed = urlparse("https://" + raw)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parsed.port
    netloc = host if not port else f"{host}:{port}"
    path = unquote(parsed.path or "/").rstrip("/") or "/"
    pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        low = key.lower()
        if low.startswith(TRACKING_PREFIXES) or low in TRACKING_KEYS:
            continue
        pairs.append((low, value))
    query = urlencode(sorted(pairs), doseq=True)
    return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))


def page_path_key(raw: str) -> str:
    """Compare the actual page only: domain + path, ignoring everything after ?."""
    raw = effective_web_url(raw or "")
    parsed = urlparse(raw)
    if not parsed.scheme:
        parsed = urlparse("https://" + raw)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = unquote(parsed.path or "/").rstrip("/") or "/"
    return f"{host}{path}"


def extract_candidate(url: str) -> str:
    parsed = urlparse(url or "")
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in CANDIDATE_PARAMS:
        value = params.get(key)
        if value and (value.startswith("http://") or value.startswith("https://")):
            return unquote(value)
    return url


def host_matches(url: str, host_parts: tuple[str, ...]) -> bool:
    host = (urlparse(url or "").hostname or "").lower()
    return any(host == part or host.endswith("." + part) for part in host_parts)


def comparable_target(link: str, final: str) -> str:
    final_candidate = effective_web_url(extract_candidate(final))
    if host_matches(final_candidate, TARGET_HOSTS):
        return final_candidate
    link_candidate = effective_web_url(extract_candidate(link))
    if host_matches(link_candidate, TARGET_HOSTS):
        return link_candidate
    return ""


def is_shortlink(url: str) -> bool:
    return host_matches(url, SHORTLINK_HOST_PARTS)


def is_site_home(url: str) -> bool:
    parsed = urlparse(url or "")
    return host_matches(url, TARGET_HOSTS) and ((parsed.path or "/").rstrip("/") or "/") == "/"


def find_html_redirect(body: str, base_url: str) -> str:
    for pattern in HTML_REDIRECT_PATTERNS:
        match = pattern.search(body or "")
        if match:
            return urljoin(base_url, html.unescape(match.group(1).strip()))
    return ""


def extract_discount_codes(url: str, depth: int = 0) -> list[str]:
    if depth > 3 or not url:
        return []
    url = unquote(url.strip())
    codes = []
    parsed = urlparse(url or "")
    parts = [p for p in unquote(parsed.path or "").split("/") if p]
    for index, part in enumerate(parts):
        if part.lower() == "discount" and index + 1 < len(parts):
            codes.append(parts[index + 1].strip())
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in DISCOUNT_PARAM_KEYS:
        value = params.get(key)
        if value:
            codes.append(value.strip())
    for key in NESTED_URL_PARAM_KEYS:
        value = params.get(key)
        if not value:
            continue
        decoded = unquote(value)
        if "discount/" in decoded.lower() or any((k + "=") in decoded.lower() for k in DISCOUNT_PARAM_KEYS):
            codes.extend(extract_discount_codes(decoded, depth + 1))
    deduped = []
    for code in codes:
        if code and code not in deduped:
            deduped.append(code)
    return deduped


def extract_discount_code(url: str) -> str:
    codes = extract_discount_codes(url)
    return codes[0] if codes else ""


def campaign_markers(url: str) -> list[str]:
    parsed = urlparse(url or "")
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    markers = []
    for key in CAMPAIGN_PARAM_KEYS:
        value = params.get(key)
        if value and value not in markers:
            markers.append(value)
    return markers


def utm_values(url: str, depth: int = 0) -> list[str]:
    if depth > 3 or not url:
        return []
    url = unquote(url.strip())
    parsed = urlparse(url or "")
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    values = []
    for key in UTM_PARAM_KEYS:
        value = params.get(key)
        if value and value not in values:
            values.append(value)
    for key in NESTED_URL_PARAM_KEYS:
        value = params.get(key)
        if not value:
            continue
        decoded = unquote(value)
        if any((utm_key + "=") in decoded for utm_key in UTM_PARAM_KEYS):
            for nested in utm_values(decoded, depth + 1):
                if nested not in values:
                    values.append(nested)
    return values


def utm_check_message(link: str, final: str, expected_utm: str) -> tuple[bool, str]:
    expected_utm = (expected_utm or "").strip()
    if not expected_utm:
        return True, "未设置期望 UTM"
    values = []
    for value in utm_values(link) + utm_values(final):
        if value not in values:
            values.append(value)
    if any(expected_utm.lower() in value.lower() for value in values):
        return True, f"UTM匹配：{expected_utm}"
    found = ", ".join(values) if values else "未识别到UTM"
    return False, f"UTM不匹配：期望 {expected_utm}；实际 {found}"


def mapped_discount_codes(link: str, final: str, discount_map: dict[str, str] | None = None) -> list[str]:
    if not discount_map:
        return []
    codes = []
    for marker in campaign_markers(link) + campaign_markers(final):
        code = discount_map.get(marker)
        if code and code not in codes:
            codes.append(code)
    return codes


def inferred_row_discount_codes(pc: str, link: str, final: str) -> list[str]:
    """Infer AppsFlyer campaign markers in this row map to the Web discount code."""
    web_codes = extract_discount_codes(pc)
    if not web_codes:
        return []
    if not (campaign_markers(link) or campaign_markers(final)):
        return []
    return web_codes


def discount_report(pc: str, link: str, final: str, discount_map: dict[str, str] | None = None) -> dict:
    web_codes = extract_discount_codes(pc)
    tracking_codes = extract_discount_codes(link)
    final_codes = extract_discount_codes(final)
    mapped_codes = mapped_discount_codes(link, final, discount_map)
    inferred_codes = inferred_row_discount_codes(pc, link, final)
    all_tracking_codes = []
    for code in tracking_codes + final_codes + mapped_codes + inferred_codes:
        if code not in all_tracking_codes:
            all_tracking_codes.append(code)
    return {
        "web_codes": web_codes,
        "tracking_codes": tracking_codes,
        "final_codes": final_codes,
        "mapped_codes": mapped_codes,
        "inferred_codes": inferred_codes,
        "all_tracking_codes": all_tracking_codes,
    }


def effective_web_url(url: str) -> str:
    parsed = urlparse(url or "")
    parts = [p for p in unquote(parsed.path or "").split("/") if p]
    if any(part.lower() == "discount" for part in parts):
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        redirect = params.get("redirect") or params.get("redirect_url") or params.get("url")
        if redirect:
            redirect = unquote(redirect)
            if redirect.startswith("http://") or redirect.startswith("https://"):
                return redirect
            scheme = parsed.scheme or "https"
            host = parsed.netloc or "www.patpat.com"
            if not redirect.startswith("/"):
                redirect = "/" + redirect
            return urlunparse((scheme, host, redirect, "", "", ""))
    return url


def is_same_page(pc: str, final: str) -> bool:
    return page_path_key(pc) == page_path_key(extract_candidate(final))


def is_same_page_with_target(pc: str, target: str) -> bool:
    return page_path_key(pc) == page_path_key(target)


def discount_message(pc: str, link: str, final: str, discount_map: dict[str, str] | None = None) -> str:
    report = discount_report(pc, link, final, discount_map)
    web_codes = report["web_codes"]
    tracking_codes = report["all_tracking_codes"]
    if not web_codes and not tracking_codes:
        return "未检测到折扣码"
    if report["mapped_codes"]:
        return f"根据活动映射识别转链折扣码：{', '.join(report['mapped_codes'])}"
    if report["inferred_codes"]:
        markers = campaign_markers(link) + campaign_markers(final)
        markers = list(dict.fromkeys(markers))
        marker_text = f"（活动标记：{', '.join(markers)}）" if markers else ""
        return f"根据本行 Web 链接自动映射转链折扣码：{', '.join(report['inferred_codes'])}{marker_text}"
    if tracking_codes:
        if web_codes:
            same = [code for code in web_codes if code in tracking_codes]
            if same:
                return f"转链携带折扣码：{', '.join(same)}"
            return f"Web折扣码：{', '.join(web_codes)}；转链携带不同折扣码：{', '.join(tracking_codes)}"
        return f"转链携带折扣码：{', '.join(tracking_codes)}"
    return f"Web链接有折扣码：{', '.join(web_codes)}；转链未检测到折扣码"


def discount_state(pc: str, link: str, final: str, discount_map: dict[str, str] | None = None) -> str:
    if extract_discount_codes(pc) or extract_discount_codes(link) or extract_discount_codes(final) or mapped_discount_codes(link, final, discount_map) or inferred_row_discount_codes(pc, link, final):
        return "has_discount"
    return "no_discount"


def fetch_final(url: str, timeout: int) -> tuple[str, int | None, str]:
    if not url:
        return "", None, "空转链"
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return url, 200, "非网页深链，未发起网络请求"
    if not parsed.scheme:
        url = "https://" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Upgrade-Insecure-Requests": "1",
    }
    last_error = ""
    visited = []
    # GET is closer to a real browser visit. Some short-link services return
    # a different redirect chain for HEAD, or use HTML/JS redirects after GET.
    for _ in range(MAX_REDIRECTS):
        recorder = RedirectRecorder()
        opener = build_opener(recorder, HTTPHandler(), HTTPSHandler(context=ssl.create_default_context()))
        req = Request(url, method="GET", headers=headers)
        try:
            with opener.open(req, timeout=timeout) as resp:
                final_url = resp.geturl()
                code = getattr(resp, "status", None) or resp.getcode()
                visited.extend(recorder.chain)
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type.lower():
                    body = resp.read(200000).decode("utf-8", errors="ignore")
                    html_next = find_html_redirect(body, final_url)
                    if html_next and html_next not in visited:
                        visited.append(html_next)
                        url = html_next
                        continue
                return final_url, code, " -> ".join(visited)
        except HTTPError as exc:
            final_url = exc.geturl() or url
            return final_url, exc.code, f"HTTP {exc.code}"
        except (URLError, socket.timeout, TimeoutError, ssl.SSLError) as exc:
            last_error = str(getattr(exc, "reason", exc))
            break
    return url, None, last_error or "请求失败"


def run_browser_checks(rows: list[dict], link_col: str, timeout: int) -> dict:
    items = [{"row": row.get("__rowNumber", ""), "url": (row.get(link_col) or "").strip()} for row in rows]
    payload = json.dumps({"items": items, "timeoutMs": timeout * 1000}, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [NODE_EXE, BROWSER_CHECK_SCRIPT],
            input=payload,
            text=True,
            capture_output=True,
            timeout=max(20, timeout * max(1, len(items)) + 15),
            encoding="utf-8",
        )
        if proc.returncode != 0:
            return {"__error__": proc.stderr or proc.stdout or "浏览器检查进程失败"}
        data = json.loads(proc.stdout or "{}")
        if data.get("error"):
            return {"__error__": data["error"]}
        return {item.get("row"): item for item in data.get("results", [])}
    except Exception as exc:
        return {"__error__": str(exc)}


def check_row(row: dict, pc_col: str, link_col: str, timeout: int, check_discount: bool = True, browser_result: dict | None = None, discount_map: dict[str, str] | None = None, expected_utm: str = "") -> dict:
    pc = (row.get(pc_col) or "").strip()
    link = (row.get(link_col) or "").strip()
    row_no = row.get("__rowNumber", "")
    if not pc or not link:
        return {"status": "空值", "row": row_no, "pc": pc, "link": link, "final": "", "message": "PC链接或转链为空"}
    if browser_result is not None:
        final = browser_result.get("final") or link
        code = browser_result.get("statusCode")
        info = browser_result.get("note") or browser_result.get("error") or "浏览器真实打开"
    else:
        final, code, info = fetch_final(link, timeout)
    discount = discount_message(pc, link, final, discount_map) if check_discount else "未检查折扣码"
    has_discount = check_discount and discount_state(pc, link, final, discount_map) == "has_discount"
    utm_ok, utm_msg = utm_check_message(link, final, expected_utm)
    parsed_link = urlparse(link)
    if parsed_link.scheme and parsed_link.scheme not in ("http", "https"):
        status = "待确认" if not has_discount else "待确认"
        return {
            "status": status,
            "row": row_no,
            "pc": pc,
            "link": link,
            "final": final,
            "discount": discount,
            "message": f"这是 App 深链，不能用网页最终 URL 直接判断；{discount if check_discount else '当前为纯链接检查模式'}；{utm_msg}"
        }
    if code is None:
        return {"status": "错误", "row": row_no, "pc": pc, "link": link, "final": final, "discount": discount, "message": f"{info}；{discount}"}
    if code >= 400:
        return {"status": "错误", "row": row_no, "pc": pc, "link": link, "final": final, "discount": discount, "message": f"转链返回 HTTP {code}；{discount}"}
    target = comparable_target(link, final)
    if not target and is_shortlink(link):
        return {
            "status": "待确认",
            "row": row_no,
            "pc": pc,
            "link": link,
            "final": final,
            "discount": discount,
            "message": f"这是 OneLink/短链，电脑端请求没有拿到可比对的 PatPat 网页落地页，不能判不匹配；{discount if check_discount else '当前为纯链接检查模式，未检查折扣码'}；{utm_msg}"
        }
    if not target:
        target = final
    if is_shortlink(link) and is_site_home(target) and not is_site_home(effective_web_url(pc)):
        return {
            "status": "待确认",
            "row": row_no,
            "pc": pc,
            "link": link,
            "final": final,
            "discount": discount,
            "message": f"这是 OneLink/短链，电脑端访问退回 PatPat 首页，不能据此判不匹配；{discount if check_discount else '当前为纯链接检查模式，未检查折扣码'}；{utm_msg}"
        }
    if is_same_page_with_target(pc, target):
        if not utm_ok:
            return {
                "status": "不匹配",
                "row": row_no,
                "pc": pc,
                "link": link,
                "final": final,
                "discount": discount,
                "message": f"落地页一致，但{utm_msg}"
            }
        detail = f"HTTP {code}，落地页一致"
        detail += f"；已按问号前页面路径比较：{page_path_key(pc)}"
        if has_discount:
            detail += f"；{discount}"
        elif not check_discount:
            detail += "；当前为纯链接检查模式，未检查折扣码"
        else:
            detail += "；未检测到折扣码"
        if expected_utm:
            detail += f"；{utm_msg}"
        return {"status": "匹配", "row": row_no, "pc": pc, "link": link, "final": final, "discount": discount, "message": detail}
    detail = f"Web页面={page_path_key(pc)}；转链页面={page_path_key(target)}"
    if has_discount:
        detail += f"；{discount}"
    elif not check_discount:
        detail += "；当前为纯链接检查模式，未检查折扣码"
    else:
        detail += "；未检测到折扣码"
    if expected_utm:
        detail += f"；{utm_msg}"
    return {
        "status": "不匹配", "row": row_no, "pc": pc, "link": link, "final": final,
        "discount": discount,
        "message": detail
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send(self, code: int, content: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/check":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            rows = payload.get("rows") or []
            pc_col = payload.get("pcColumn") or "PC链接"
            link_col = payload.get("linkColumn") or "转链-1"
            check_discount = bool(payload.get("checkDiscount", True))
            browser_mode = bool(payload.get("browserMode", False))
            discount_map = payload.get("discountMap") or {}
            if not isinstance(discount_map, dict):
                discount_map = {}
            expected_utm = payload.get("expectedUtm") or ""
            timeout = max(3, min(30, int(payload.get("timeout") or 10)))
            if not rows:
                raise ValueError("没有数据行")
            sample = rows[0]
            if pc_col not in sample or link_col not in sample:
                headers = ", ".join(k for k in sample.keys() if not k.startswith("__"))
                raise ValueError(f"找不到列名：{pc_col} / {link_col}。当前表头：{headers}")
            browser_results = {}
            if browser_mode:
                browser_results = run_browser_checks(rows, link_col, timeout)
                if browser_results.get("__error__"):
                    raise ValueError("浏览器真实打开检查不可用：" + browser_results["__error__"])
            results = [
                check_row(row, pc_col, link_col, timeout, check_discount, browser_results.get(row.get("__rowNumber", "")) if browser_mode else None, discount_map, expected_utm)
                for row in rows
            ]
            self._send(200, json.dumps({"results": results}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        except Exception as exc:
            self._send(400, json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    shown_host = "127.0.0.1" if HOST in ("0.0.0.0", "") else HOST
    print(f"飞书物料表链接检查工具已启动：http://{shown_host}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()







