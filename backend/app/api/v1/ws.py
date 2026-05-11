"""WebSocket endpoint — /api/v1/ws/prices.

Auth: query param `?token=<access_token>` (browser native WS header eklenemez).

NOT (Future Roadmap): Production hardening — WS auth STOMP/CONNECT frame'iyle
değiştirilebilir (URL log riski azaltma).

Message protokolü (CLAUDE.md/build-steps spec'i):
  Client → Server:
    {"action": "subscribe", "symbols": ["BTCUSDT", ...]}
    {"action": "unsubscribe", "symbols": ["BTCUSDT"]}
  Server → Client (subscribe sonrası warmup):
    {"type": "snapshot", "prices": [{...}, ...]}
  Server → Client (real-time):
    {"type": "price", "symbol": "BTCUSDT", "price": 80627.4,
     "change_24h_pct": 2.4, "ts": 1234567890}

Auth fail → close code 4401.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.ws.price_hub import price_hub

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])

# WebSocket close codes (RFC 6455 4000-4999 application range)
WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_INVALID_MESSAGE = 4400


async def _authenticate_token(token: str) -> User | None:
    """Token validate edip aktif kullanıcıyı döner. Hata → None."""
    try:
        payload = decode_token(token)
    except (JWTError, Exception):
        return None
    if payload.get("type") != "access":
        return None
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError):
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


@router.websocket("/ws/prices")
async def ws_prices(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """Multi-symbol fiyat akışı. Token query param ile auth."""
    user = await _authenticate_token(token)
    if user is None:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Geçersiz token")
        return

    await websocket.accept()
    logger.info("ws_prices_connected", user_id=str(user.id))

    try:
        while True:
            try:
                msg = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.warning("ws_invalid_message", error=str(e))
                continue

            action = msg.get("action")
            symbols = msg.get("symbols", [])

            if action == "subscribe":
                if not isinstance(symbols, list):
                    continue
                snapshot = await price_hub.subscribe(websocket, symbols)
                if snapshot:
                    await websocket.send_json(
                        {"type": "snapshot", "prices": snapshot}
                    )
            elif action == "unsubscribe":
                await price_hub.unsubscribe(
                    websocket, symbols if isinstance(symbols, list) else None
                )
            else:
                logger.warning("ws_unknown_action", action=action)

    except WebSocketDisconnect:
        logger.info("ws_prices_disconnected", user_id=str(user.id))
    finally:
        await price_hub.unsubscribe(websocket, None)
