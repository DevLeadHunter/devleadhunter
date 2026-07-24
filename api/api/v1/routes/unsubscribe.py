"""
Unsubscribe routes for RGPD compliance.

Every unsubscribe link is signed with a per-email HMAC token (see
``unsubscribe_service.generate_unsubscribe_link``). The routes below verify that
token before acting, which prevents a stranger from unsubscribing arbitrary
prospects by guessing the URL (unsubscribe-bombing). The e-mail is HTML-escaped
before being rendered, closing the reflected-XSS hole.
"""

from html import escape

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.database import get_db
from services.unsubscribe_service import unsubscribe_service

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


def _page(title: str, icon: str, body_html: str) -> str:
    """Wrap a confirmation/error message in the shared unsubscribe HTML shell.

    Args:
        title: Page ``<title>`` and heading (already trusted, no user input).
        icon: Emoji shown above the heading.
        body_html: Inner HTML — the caller MUST have escaped any user input.

    Returns:
        A full HTML document string.
    """
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 500px;
            text-align: center;
        }}
        .icon {{ font-size: 64px; margin-bottom: 20px; }}
        h1 {{ color: #2d3748; margin: 0 0 16px 0; font-size: 28px; }}
        p {{ color: #718096; line-height: 1.6; margin: 0 0 12px 0; }}
        .email {{
            background: #f7fafc;
            padding: 12px 20px;
            border-radius: 6px;
            margin: 20px 0;
            font-weight: 500;
            color: #2d3748;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            font-size: 14px;
            color: #a0aec0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{icon}</div>
        {body_html}
        <div class="footer">
            <p>DevLeadHunter - Outil de prospection pour développeurs freelance</p>
        </div>
    </div>
</body>
</html>
"""


def _invalid_link_page() -> str:
    """HTML page shown when the signature is missing or wrong (no action taken)."""
    return _page(
        title="Lien invalide",
        icon="⚠️",
        body_html=(
            "<h1>Lien invalide</h1>"
            "<p>Ce lien de désabonnement est invalide ou incomplet.</p>"
            "<p>Si vous souhaitez ne plus recevoir nos emails, répondez simplement "
            "à l'un d'eux ou contactez-nous.</p>"
        ),
    )


@router.get("", response_class=HTMLResponse, summary="Unsubscribe from emails")
async def unsubscribe_get(
    email: str = Query(..., description="Email address to unsubscribe"),
    token: str = Query("", description="Per-email signature that authorizes the request"),
    prospect_id: int = Query(None, description="Prospect ID (optional)"),
    reason: str = Query(None, description="Reason for unsubscribing (optional)"),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe an email address from all future emails.

    The request is honoured only when ``token`` is a valid signature for ``email``
    (RGPD compliant, but not forgeable for an arbitrary address).
    """
    if not unsubscribe_service.verify_token(email, token):
        return HTMLResponse(content=_invalid_link_page(), status_code=400)

    unsubscribe_service.unsubscribe(db=db, email=email, prospect_id=prospect_id, reason=reason)

    safe_email = escape(email)
    body_html = (
        "<h1>Désabonnement confirmé</h1>"
        "<p>Vous avez été retiré de notre liste d'emails.</p>"
        f'<div class="email">{safe_email}</div>'
        "<p>Vous ne recevrez plus d'emails de prospection de notre part.</p>"
        "<p>Si vous pensez qu'il s'agit d'une erreur, vous pouvez nous contacter.</p>"
    )
    return HTMLResponse(content=_page(title="Désabonnement confirmé", icon="✅", body_html=body_html))


@router.post("", summary="Unsubscribe from emails (POST)")
async def unsubscribe_post(
    email: str = Query(..., description="Email address to unsubscribe"),
    token: str = Query("", description="Per-email signature that authorizes the request"),
    prospect_id: int = Query(None, description="Prospect ID (optional)"),
    reason: str = Query(None, description="Reason for unsubscribing (optional)"),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe an email address from all future emails (POST — RFC 8058 one-click).

    Same signature check as the GET route: a valid ``token`` for ``email`` is required.
    """
    if not unsubscribe_service.verify_token(email, token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing unsubscribe token",
        )

    unsubscribe_record = unsubscribe_service.unsubscribe(db=db, email=email, prospect_id=prospect_id, reason=reason)

    return {
        "success": True,
        "message": f"Email {email} has been unsubscribed",
        "unsubscribed_at": unsubscribe_record.created_at.isoformat(),
    }
