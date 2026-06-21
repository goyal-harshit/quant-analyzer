"""Alerts Router — Price/fundamental alert management"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db, User, Alert
from models.schemas import AlertCreate, AlertOut
from services.data_service import data_service
from services.auth_service import get_current_user

router = APIRouter()


@router.post("", response_model=dict)
async def create_alert(payload: AlertCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new alert."""
    user_id = current_user.id
    alert = Alert(
        user_id=user_id,
        ticker=payload.ticker.upper(),
        condition_type=payload.condition_type,
        threshold=payload.threshold,
        status="active",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return {"id": alert.id, "ticker": alert.ticker, "condition_type": alert.condition_type, "threshold": alert.threshold}


@router.get("", response_model=list[AlertOut])
async def list_alerts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all alerts for the demo user."""
    user_id = current_user.id
    res = await db.execute(select(Alert).where(Alert.user_id == user_id))
    alerts = res.scalars().all()
    return [
        AlertOut(
            id=a.id,
            ticker=a.ticker,
            condition_type=a.condition_type,
            threshold=a.threshold,
            status=a.status,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an alert (only the owner's own alerts)."""
    # Scope the lookup to the current user — prevents IDOR (deleting others' alerts).
    res = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.delete(alert)
    await db.commit()
    return {"deleted": True}


@router.get("/evaluate")
async def evaluate_alerts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Evaluate all active alerts against current market data."""
    user_id = current_user.id
    res = await db.execute(select(Alert).where(Alert.user_id == user_id, Alert.status == "active"))
    alerts = res.scalars().all()

    triggered = []
    for alert in alerts:
        quote = await data_service.get_quote(alert.ticker)
        if not quote or not quote.get("price"):
            continue

        price = quote.get("price", 0)
        threshold = alert.threshold
        triggered_flag = False

        if alert.condition_type == "price_above" and price > threshold:
            triggered_flag = True
        elif alert.condition_type == "price_below" and price < threshold:
            triggered_flag = True
        elif alert.condition_type == "pct_change_above" and quote.get("change_pct", 0) > threshold:
            triggered_flag = True
        elif alert.condition_type == "pct_change_below" and quote.get("change_pct", 0) < threshold:
            triggered_flag = True

        if triggered_flag:
            triggered.append({
                "alert_id": alert.id,
                "ticker": alert.ticker,
                "condition": alert.condition_type,
                "threshold": threshold,
                "current_price": price,
                "message": f"{alert.ticker} {alert.condition_type.replace('_', ' ')} {threshold} — current: {price}",
            })

    return {"triggered": triggered, "total_active": len(alerts)}
