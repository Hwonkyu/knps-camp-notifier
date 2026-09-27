"""
공통 알림 발송 모듈
- 텔레그램(Telegram) 봇
- 디스코드(Discord) 웹훅
- 이메일(SMTP)
순수 파이썬 표준 라이브러리(urllib, json, smtplib, email)로 외부 의존성 없이 동작합니다.
"""

import json
import urllib.request
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any


def create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def send_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    """
    텔레그램 봇으로 메시지를 전송합니다.
    """
    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True
    }
    data = json.dumps(payload).encode("utf-8")
    ctx = create_ssl_context()

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Notifier Error] Telegram 전송 실패: {e}")
        return False


def send_discord_payload(
    webhook_url: str,
    payload: Dict[str, Any],
    user_agent: str = "KNPSNotifier/1.0"
) -> bool:
    """
    디스코드 웹훅으로 JSON Payload를 전송합니다.
    """
    if not webhook_url:
        return False

    data = json.dumps(payload).encode("utf-8")
    ctx = create_ssl_context()

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": user_agent},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Notifier Error] Discord 전송 실패: {e}")
        return False


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    to_email: str,
    subject: str,
    body: str,
    use_tls: bool = True
) -> bool:
    """
    이메일(SMTP)로 알림을 전송합니다.
    """
    if not smtp_host or not smtp_user or not smtp_pass or not to_email:
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if use_tls:
                server.starttls()

        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"[Notifier Error] 이메일 전송 실패: {e}")
        return False
