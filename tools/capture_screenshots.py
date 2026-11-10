# -*- coding: utf-8 -*-
"""
capture_screenshots.py  —  答辩截图一键采集

功能：
  1. 自举 playwright（若 venv 中未安装则 pip install + 下载 chromium）
  2. 调用 /api/user/login 拿到 SESSION cookie，注入浏览器上下文
  3. 按 docs/演示脚本.md 的 12 项清单，逐页访问并以 1920x1080 截图
  4. 输出到 docs/screenshots/

前置：后端与引擎已启动（8000 / 8100），MySQL / Redis 运行。
用法：
  .venv\\Scripts\\python.exe tools\\capture_screenshots.py
  # 或指定账号/地址：
  .venv\\Scripts\\python.exe tools\\capture_screenshots.py --base http://127.0.0.1:8000 --user admin --password 123456
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import http.cookiejar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
VIEWPORT = {"width": 1920, "height": 1080}
CHROME_ARGS = ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]


def ensure_playwright():
    """确认 playwright 与 chromium 可用，否则自动安装。"""
    try:
        from playwright.sync_api import sync_playwright  # noqa
        return
    except ImportError:
        print("[setup] 未检测到 playwright，正在安装 ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    # 下载 chromium
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def login_session(base, user, password):
    """通过 API 登录，返回 cookie 字典列表（playwright 上下文 add_cookies 格式）。"""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = json.dumps({"userName": user, "password": password}).encode()
    req = urllib.request.Request(
        base + "/api/user/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=15) as r:
        data = json.loads(r.read())
    if data.get("code") != 1:
        raise RuntimeError(f"登录失败: {data}")
    host = urllib.request.urlparse(base).hostname
    cookies = []
    for c in cj:
        cookies.append({
            "name": c.name, "value": c.value, "domain": host,
            "path": "/", "httpOnly": c.has_nonstandard_attr("HttpOnly") or False,
        })
    print(f"[login] code=1, cookie={list(cj)[0].name if list(cj) else '?'}")
    return cookies


def shot(page, name, route=None, pre=None, wait=1200):
    """访问路由并截图。pre(page) 可在截图前执行交互。"""
    url = base + "/admin/index.html" + (f"#{route}" if route else "")
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(wait)
    if pre:
        pre(page)
        page.wait_for_timeout(600)
    out = OUT / name
    page.screenshot(path=str(out), full_page=False)
    print(f"[shot] {out.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="123456")
    args = ap.parse_args()
    global base
    base = args.base

    ensure_playwright()
    OUT.mkdir(parents=True, exist_ok=True)

    cookies = login_session(base, args.user, args.password)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=CHROME_ARGS)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = ctx.new_page()

        # 1. 登录页截图 + 表单登录（让 Vuex 用户态正常显示，而非仅注入 cookie）
        page.goto(base + "/admin/index.html#/login", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "01_login.png"))
        print("[shot] 01_login.png")

        # 表单登录
        try:
            page.locator("input[placeholder*='用户']").fill(args.user)
            page.locator("input[type=password]").fill(args.password)
            # 点击登录按钮（class=login-btn，文本"登 录"含空格）
            btn = page.locator(".login-btn")
            if btn.count() == 0:
                btn = page.locator("button.el-button--primary")
            btn.click()
            page.wait_for_url("**/dashboard", timeout=15000)
            page.wait_for_timeout(1000)
            print("[login] 表单登录成功 -> dashboard")
        except Exception as e:
            # 兜底：注入 API 登录拿到的 cookie，然后刷新
            print(f"[login] 表单登录失败({e})，改用 cookie 注入")
            ctx.add_cookies(cookies)
            page.goto(base + "/admin/index.html#/dashboard", wait_until="networkidle")

        # 2. 关于页
        shot(page, "02_about.png", "/about/index", wait=1500)

        # 3. 数据管理页
        shot(page, "03_data.png", "/data/index", wait=1800)

        # 4. EDA 交互洞察
        shot(page, "04_eda.png", "/analysis/eda", wait=2000)

        # 5. 预测页（决策卡 + 区间）
        def predict_pre(pg):
            try:
                pg.locator("input[type=number]").first.fill("50000")
            except Exception:
                pass
            try:
                pg.get_by_text("预测", exact=True).first.click(timeout=2000)
                pg.wait_for_timeout(1500)
            except Exception:
                pass
        shot(page, "05_predict.png", "/predict/index", pre=predict_pre, wait=1500)

        # 6. 归因页解释报告
        shot(page, "06_attribution.png", "/attribution/index", wait=2000)

        # 7. 实验中心
        shot(page, "07_evaluation.png", "/evaluation/index", wait=1800)

        # 8. 模型治理页
        shot(page, "08_model.png", "/model/index", wait=1800)

        # 9. 报告中心
        shot(page, "09_report.png", "/report/index", wait=1800)

        # 10. 大屏（standalone，全屏四幕）
        shot(page, "10_screen.png", "/screen/index", wait=2500)

        # 11. 命令面板（Ctrl/Cmd+K）
        def cmd_pre(pg):
            pg.keyboard.press("Control+k")
            pg.wait_for_timeout(600)
        shot(page, "11_command_palette.png", "/dashboard", pre=cmd_pre, wait=800)

        # 12. 演示导览（点击问号图标）
        def tour_pre(pg):
            try:
                # 顶栏问号图标（svg-icon icon-class=question）
                pg.locator("[class*='hover-effect']").last.click(timeout=2000)
                pg.wait_for_timeout(600)
            except Exception:
                print("    [skip] tour trigger not found (可能为旧构建)")
        shot(page, "12_tour.png", "/dashboard", pre=tour_pre, wait=800)

        browser.close()

    print(f"\n完成：{len(list(OUT.glob('*.png')))} 张截图 -> {OUT}")


if __name__ == "__main__":
    main()
