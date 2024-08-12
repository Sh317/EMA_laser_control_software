from pylablib.devices import M2
M2Error = M2.base.M2Error
import time
import json
import logging

try:
    import websocket
except ImportError:
    websocket=None



class EMASolstis(M2.Solstis):
    def __init__(self, addr, port):
        super().__init__(addr,port)
        self.ref = 0.
        self.before = 0.
    
    def _check_websocket(self):
        if websocket is None:
            msg=(   "operation requires Python websocket-client library. You can install it via PyPi as 'pip install websocket-client'. "
                    "If it is installed, check if it imports correctly by running 'import websocket'")
            raise ImportError(msg)
    
    def on_message(self, ws, message):
        now = time.time()
        tune = {}
        tune.update(json.loads(message))
        if 'cavity_tune' in message:
            # message = tune['cavity_tune']
            print(f"{now - self.before} passed and Received tuner: {tune}")
        else: print(f"{now - self.before} passed without tuner: {tune}")
        self.before = time.time()

    def on_error(self, ws, error):
        print(f"Error occurred: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket closed")

    def on_open(self, ws):
        print("WebSocket connection opened")

    def read_value(self, present_key=None, nmax=20):
        if self.use_websocket:
            self._check_websocket()
            try: 
                self.before = time.time()
                ws = websocket.WebSocketApp("ws://{}:8088/control.htm".format(self.conn[0]),
                                            on_message=self.on_message,
                                            on_error=self.on_error,
                                            on_close=self.on_close)
                ws.run_forever()
            finally:
                ws.close()
        else:
            raise M2Error("websocket is required to communicate this request")
    
    def close_websocket(self, ws):
        ws.recv()
        logging.getLogger("websocket").setLevel(logging.CRITICAL)
        ws.close()
                        
    def _read_web_status(self, ws, present_key, nmax):
        for t in range(5):
            try:
                with self._websocket_lock:
                    return self._wait_for_websocket_status(ws,present_key=present_key,nmax=nmax)
            except (websocket.WebSocketTimeoutException, ConnectionResetError):
                if t==4:
                    raise
                time.sleep(5.)
    
    def get_lock_and_tuner(self):
        """
        Get full websocket status.
        
        Return a large dictionary containing all the information available in the web interface.
        """
        return self._read_websocket_status(present_key="cavity_tune") if self.use_websocket else None
# dict = laser.get_full_web_status()cavity_tune

laser = EMASolstis("192.168.1.222", 39933)
# before = time.time()
# info = laser.get_full_web_status()
# after = time.time()
# for key in info:
#     print(f"It takes {after-before}s, {key}: {info[key]}")
# print(f"It takes {after-before}s, \n {info['cavity_tune']}")
laser.read_value(present_key='cavity_tune')

