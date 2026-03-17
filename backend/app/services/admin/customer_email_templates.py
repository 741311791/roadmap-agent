"""
客户邮件默认模板

提供管理员群发邮件页面的内置模板定义。
"""
from typing import Final


TEMPLATE_CUSTOM: Final[str] = "custom"
TEMPLATE_PRODUCT_UPDATE: Final[str] = "product_update"
TEMPLATE_PROMOTION: Final[str] = "promotion"
DEFAULT_EMAIL_TEMPLATE_SHELL: Final[str] = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{subject}}</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1c1917;">
    <div style="max-width:680px;margin:0 auto;padding:32px 16px;">
      <div style="background:#ffffff;border:1px solid #e3e7e3;border-radius:28px;overflow:hidden;box-shadow:0 18px 60px rgba(28,25,23,0.08);">
        <div style="padding:36px 40px;background:linear-gradient(180deg,#f6f7f6 0%,#eef2ee 100%);border-bottom:1px solid #e3e7e3;">
          <div style="display:inline-block;padding:8px 14px;border-radius:999px;background:#e3e7e3;color:#4c5d4c;font-size:12px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;">
            Fast Learning
          </div>
          <h1 style="margin:18px 0 0;font-size:32px;line-height:1.25;font-weight:700;color:#1c1917;">
            {{subject}}
          </h1>
        </div>

        <div style="padding:36px 40px;">
          {{content}}
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()


DEFAULT_CUSTOMER_EMAIL_TEMPLATES: Final[list[dict[str, str | None]]] = [
    {
        "key": TEMPLATE_PRODUCT_UPDATE,
        "name": "网站功能迭代",
        "description": "用于功能上新、版本更新和体验优化通知。",
        "subject": "New features are now live on Fast Learning",
        "html_content": """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{subject}}</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1c1917;">
    <div style="max-width:680px;margin:0 auto;padding:32px 16px;">
      <div style="background:linear-gradient(180deg,#f6f7f6 0%,#eef2ee 100%);border:1px solid #e3e7e3;border-radius:28px;overflow:hidden;box-shadow:0 18px 60px rgba(28,25,23,0.08);">
        <div style="padding:44px 40px 32px;background:radial-gradient(circle at top right,rgba(96,117,96,0.16),transparent 34%),linear-gradient(135deg,#f6f7f6 0%,#eef2ee 100%);border-bottom:1px solid #e3e7e3;">
          <div style="display:inline-block;padding:8px 14px;border-radius:999px;background:#e3e7e3;color:#4c5d4c;font-size:12px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;">
            Fast Learning
          </div>
          <h1 style="margin:18px 0 0;font-size:36px;line-height:1.2;font-weight:700;color:#1c1917;">
            {{subject}}
          </h1>
        </div>

        <div style="padding:36px 40px;">
          {{content}}
          <div style="text-align:center;margin:10px 0 24px;">
            <a href="{{frontend_url}}" style="display:inline-block;padding:14px 28px;border-radius:999px;background:#4c5d4c;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;box-shadow:0 10px 24px rgba(76,93,76,0.24);">
              Explore the latest updates
            </a>
          </div>

          <p style="margin:0;font-size:14px;line-height:1.9;color:#6b7280;">
            Best regards,<br />The Fast Learning Team
          </p>
        </div>
      </div>
    </div>
  </body>
</html>
        """.strip(),
        "text_content": (
            "Hello,\n\n"
            "We have shipped a new round of product updates to make your learning workflow smoother and more reliable.\n\n"
            "## Highlights\n"
            "- More stable roadmap generation\n"
            "- Clearer task progress feedback\n"
            "- Refined homepage and task experience\n\n"
            "Log in to explore the latest updates."
        ),
    },
    {
        "key": TEMPLATE_PROMOTION,
        "name": "优惠促销",
        "description": "用于活动优惠、限时折扣和促销提醒。",
        "subject": "Limited-time offer for Fast Learning users",
        "html_content": """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{subject}}</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1c1917;">
    <div style="max-width:680px;margin:0 auto;padding:32px 16px;">
      <div style="background:#ffffff;border:1px solid #e3e7e3;border-radius:28px;overflow:hidden;box-shadow:0 18px 60px rgba(28,25,23,0.08);">
        <div style="padding:44px 40px 34px;background:linear-gradient(135deg,#4c5d4c 0%,#607560 100%);color:#ffffff;">
          <div style="display:inline-block;padding:8px 14px;border-radius:999px;background:rgba(255,255,255,0.14);font-size:12px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;">
            Fast Learning Offer
          </div>
          <h1 style="margin:18px 0 0;font-size:36px;line-height:1.2;font-weight:700;color:#ffffff;">
            {{subject}}
          </h1>
        </div>

        <div style="padding:36px 40px;">
          {{content}}
          <div style="text-align:center;margin:10px 0 24px;">
            <a href="{{frontend_url}}" style="display:inline-block;padding:14px 28px;border-radius:999px;background:#1c1917;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;box-shadow:0 10px 24px rgba(28,25,23,0.16);">
              View the offer
            </a>
          </div>

          <p style="margin:0;font-size:14px;line-height:1.9;color:#6b7280;">
            Best regards,<br />The Fast Learning Team
          </p>
        </div>
      </div>
    </div>
  </body>
</html>
        """.strip(),
        "text_content": (
            "Hello,\n\n"
            "We are running a special promotion for Fast Learning users for a limited time.\n\n"
            "## Promotion highlights\n"
            "- Special pricing for a limited time\n"
            "- Better value for deeper learning workflows\n"
            "- A good time to upgrade your current experience\n\n"
            "Please check the latest offer details in the product or contact us if you have any questions."
        ),
    },
]

