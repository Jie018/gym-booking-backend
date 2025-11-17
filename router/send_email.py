import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()  # 讀取根目錄的 .env 檔案

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")  
EMAIL_FROM = os.getenv("EMAIL_FROM")

def send_email(to_email: str, subject: str, html_content: str):
    try:
        message = Mail(
            from_email=EMAIL_FROM,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent: {response.status_code}")
        return True
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return False

print("API Key:", SENDGRID_API_KEY)
print("From Email:", EMAIL_FROM)

#測試
if __name__ == "__main__":
    test_email = "cynthia381@gmail.com"  # 改成你的收信信箱
    try:
        send_email(
            to_email=test_email,
            subject="測試 Email",
            html_content="<h1>這是測試信件</h1><p>確認 SendGrid 可用</p>"
        )
        print("✅ Email 送出成功")
    except Exception as e:
        print("❌ Email 送出失敗:", e)
