"""
Unsubscribe routes for RGPD compliance.
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.database import get_db
from services.unsubscribe_service import unsubscribe_service


router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Unsubscribe from emails"
)
async def unsubscribe_get(
    email: str = Query(..., description="Email address to unsubscribe"),
    prospect_id: int = Query(None, description="Prospect ID (optional)"),
    reason: str = Query(None, description="Reason for unsubscribing (optional)"),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe an email address from all future emails.
    
    This endpoint is RGPD compliant and allows users to opt-out of emails.
    """
    # Unsubscribe the email
    unsubscribe_service.unsubscribe(
        db=db,
        email=email,
        prospect_id=prospect_id,
        reason=reason
    )
    
    # Return confirmation page
    html_content = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Désabonnement confirmé</title>
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
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #2d3748;
            margin: 0 0 16px 0;
            font-size: 28px;
        }}
        p {{
            color: #718096;
            line-height: 1.6;
            margin: 0 0 12px 0;
        }}
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
        <div class="icon">✅</div>
        <h1>Désabonnement confirmé</h1>
        <p>Vous avez été retiré de notre liste d'emails.</p>
        <div class="email">{email}</div>
        <p>Vous ne recevrez plus d'emails de prospection de notre part.</p>
        <p>Si vous pensez qu'il s'agit d'une erreur, vous pouvez nous contacter.</p>
        <div class="footer">
            <p>DevLeadHunter - Outil de prospection pour développeurs freelance</p>
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


@router.post(
    "",
    summary="Unsubscribe from emails (POST)"
)
async def unsubscribe_post(
    email: str = Query(..., description="Email address to unsubscribe"),
    prospect_id: int = Query(None, description="Prospect ID (optional)"),
    reason: str = Query(None, description="Reason for unsubscribing (optional)"),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe an email address from all future emails (POST method).
    
    This endpoint is RGPD compliant and allows users to opt-out of emails.
    """
    unsubscribe_record = unsubscribe_service.unsubscribe(
        db=db,
        email=email,
        prospect_id=prospect_id,
        reason=reason
    )
    
    return {
        "success": True,
        "message": f"Email {email} has been unsubscribed",
        "unsubscribed_at": unsubscribe_record.created_at.isoformat()
    }

