# Controller/ws_controller.py
@router.websocket("/ws/{user_id}")
async def ws_endpoint(ws: WebSocket, user_id: int):
    if not await chat_service.enter(user_id, ws):
        return
    try:
        while True:
            await chat_service.handle_message(user_id, await ws.receive_text())
    except WebSocketDisconnect:
        pass
    finally:
        await chat_service.leave(user_id, ws)