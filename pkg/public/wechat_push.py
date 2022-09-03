import http.client
import json
from enum import Enum

class PrefixEnums(Enum):
    default = "九方-李琦玉专属报警"


class WechatPush:
    def __init__(self):
        self.port: int = 443
        self.token: str = "d9a1f589f46a495a6a3857d8f208f1137b43a0ae"
        self.server: str ="push.ggt1024.com"

    def notify(self,  prefix=PrefixEnums.default.value,msg="test"):
        try:
            prefix_pre=f"『{prefix}』\n"
            conn = http.client.HTTPSConnection(host=self.server, port=self.port)
            rqbody = json.dumps(dict(token=self.token, msg=prefix_pre+msg))
            conn.request(method="POST", url="/to/", body=rqbody)
            resp = conn.getresponse()
            rs = json.loads(resp.read().decode("utf8"))
            print(rs)
            assert int(rs["code"] / 100) == 2, rs
        except Exception as e:
            print(f"push error = {e}")

if __name__ == '__main__':
    notify_user = WechatPush()
    notify_user.notify()