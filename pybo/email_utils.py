import smtplib
import os
from email.mime.text import MIMEText
from flask import current_app


def send_verification_email(to_email: str, verify_url: str) -> bool:
    """Send verification email. Returns True if email was sent, False otherwise.

    If mail server settings are not configured, the verify URL is printed to the app logger
    and returned as False so the caller can fall back to developer-friendly behavior.
    """
    app_cfg = current_app.config
    mail_server = app_cfg.get('MAIL_SERVER') or os.environ.get('MAIL_SERVER')
    mail_port = int(app_cfg.get('MAIL_PORT') or os.environ.get('MAIL_PORT') or 0)
    mail_user = app_cfg.get('MAIL_USERNAME') or os.environ.get('MAIL_USERNAME')
    mail_pass = app_cfg.get('MAIL_PASSWORD') or os.environ.get('MAIL_PASSWORD')
    mail_use_tls = bool(app_cfg.get('MAIL_USE_TLS') or os.environ.get('MAIL_USE_TLS'))
    from_addr = app_cfg.get('MAIL_DEFAULT_SENDER') or mail_user or f"no-reply@{os.environ.get('HOSTNAME','localhost')}"

    subject = '계정 인증 안내'
    body = f'안녕하세요. 아래 링크를 클릭하여 이메일 인증을 완료해주세요.\n\n{verify_url}\n\n(이 링크은 24시간 동안 유효합니다.)'

    # If SMTP is not configured, log/print the link and return False
    if not mail_server or not mail_port or not mail_user or not mail_pass:
        current_app.logger.info(f'Email verification link for {to_email}: {verify_url}')
        print(f'Email verification link for {to_email}: {verify_url}')
        return False

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(mail_server, mail_port, timeout=10)
        if mail_use_tls:
            server.starttls()
        server.login(mail_user, mail_pass)
        server.sendmail(from_addr, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send verification email')
        print('Failed to send verification email:', e)
        return False
