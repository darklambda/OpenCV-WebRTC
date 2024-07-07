#!/usr/bin/env python

import asyncio
import json
import signal
import logging
from websockets import server, WebSocketServerProtocol, ConnectionClosedOK
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay

from VideoTransform.transform import VideoTransformTrack

connections: list[WebSocketServerProtocol] = list()

MAX_CONNECTIONS = 3

relay = MediaRelay()
logger = logging.getLogger("pc")

peerCreated = False

async def create_peer(request: dict, websocket: WebSocketServerProtocol):
    global peerCreated
    peerCreated = True

    offer = RTCSessionDescription(sdp=request["sdp"], type=request["type"])

    pc = RTCPeerConnection()

    def log_info(msg, *args):
        logger.info(msg, *args)

    # Change to websocket ipadress
    log_info("Created for %s", websocket.remote_address[0])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        global peerCreated
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            peerCreated = False
        elif pc.connectionState == "closed":
            peerCreated = False

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)

        if track.kind == "video":
            pc.addTrack(
                VideoTransformTrack(
                    relay.subscribe(track), transform=request["video_transform"]
                )
            )

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await websocket.send(json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ))
    await websocket.close()


async def connection_handler(websocket: WebSocketServerProtocol):
    global peerCreated
    if len(connections) >= MAX_CONNECTIONS:
        await websocket.close(reason='Maximum Websocket Connection Reached')
    connections.append(websocket)
    try:
        while True:
            index = connections.index(websocket)
            if (index == 0) and (not peerCreated):
                await websocket.send("1-")
                rqs = await websocket.recv()
                rqs = json.loads(rqs)
                await create_peer(rqs, websocket)
            else:
                await websocket.send("2-" + str(index))
                await asyncio.sleep(1)
    except ConnectionClosedOK:
        connections.remove(websocket)

async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    async with server.serve(connection_handler, "localhost", 8764, close_timeout=1.0):
        print("Starting Websocket Server on port 8765")
        await stop


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Server Closed")