import multiprocessing
from nostr.relay_manager import RelayManager
from nostr.key import PrivateKey
from nostr.filter import Filter, Filters
from nostr.event import EventKind, EncryptedDirectMessage
import time
from flask import Flask, request
import threading

app = Flask(__name__)

tasks = []


def main_function(private_key_b32: str, message: str):
    if len(private_key_b32) == 63 and private_key_b32[0:4] == "nsec":
        relay_manager = RelayManager()
        relay_manager.add_relay("wss://nos.lol")
        relay_manager.add_relay("wss://relay.damus.io")
        relay_manager.add_relay("wss://nostr-pub.wellorder.net")
        relay_manager.add_relay("wss://relay.snort.social")
        relay_manager.add_relay("wss://relay.nostr.band")
        private_key = PrivateKey().from_nsec(private_key_b32)
        user_pub_key = private_key.public_key.hex()

        filters_pm = Filter(kinds=[EventKind.CONTACTS], pubkey_refs=[user_pub_key])
        subscription = Filters([filters_pm])
        relay_manager.add_subscription_on_all_relays("FollowerNotificationTool", subscription)
        time.sleep(1.25)
        follower_set = set()

        while relay_manager.message_pool.has_events():
            event_msg = relay_manager.message_pool.get_event()
            follower_set.add(event_msg.event.public_key)
            time.sleep(0.3)
            print("follower found:", len(follower_set), ", ", event_msg.event.public_key)

        relay_manager.close_subscription_on_all_relays("FollowerNotificationTool")

        for follower in follower_set:
            dm = EncryptedDirectMessage(
                recipient_pubkey=follower,
                cleartext_content=message
            )
            private_key.sign_event(dm)
            print("sent: ", dm.id, "to: ", follower)
            relay_manager.publish_event(dm)
            time.sleep(1)
        relay_manager.close_all_relay_connections()
        relay_manager = None


html = """<!DOCTYPE html>
<html>
<body>

<h2>Send a direct message to all your followers</h2>

<form method="GET" action="/run-job">
  <label for="private-key">Private Key in nsec format:</label><br>
  <input type="text" id="private-key" name="private-key" value="nsec..."><br>
  <label for="message">Your message:</label><br>
  <input type="text" id="message" name="message" value="Please unfollow this account"><br><br>
  <input type="submit" value="Submit">
</form>

<p>If you click the "Submit" button your private key will be transmitted to a server and all your followers will be 
notified with your message via direct message.</p>

</body>
</html>"""


@app.route("/")
def homepage():
    return html


@app.route('/run-job', methods=['GET'])
def start_service():
    global tasks
    priv_k = request.args.get('private-key')
    message = request.args.get('message')
    tasks.append([str(priv_k), str(message)])
    return "Task in queue, this can take some minutes. Please close the window now."


def worker():
    global tasks
    while True:
        if tasks:
            main_function(tasks[0][0], tasks[0][1])
            tasks.pop(0)
        else:
            time.sleep(1)


t = threading.Thread(target=worker)
t.start()

app.run()

# test user nsec1fn04ps896um27kz3ndrlqfta73syr4pg2z97e9n7y3hq7a0avalss2h4x5
# test user pubkey npub1vm0ajd2m77sc83u2zu8e3htwesku5tsx60hqa62v0n7e0qm9tprsy9k8p8
