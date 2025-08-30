import os
import time
from dotenv import load_dotenv
from cortex import Cortex

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

class AttentionReader():
    """
    A class to subscribe to the performance metrics (met) data stream
    and read the 'attention' (focus) value.
    """
    def __init__(self, app_client_id, app_client_secret, **kwargs):
        print("AttentionReader initialized")
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=False, **kwargs)
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(new_data_labels=self.on_new_data_labels)
        self.c.bind(new_met_data=self.on_new_met_data)
        self.c.bind(inform_error=self.on_inform_error)
        self.met_labels = []
        self.attention_index = -1

    def start(self, headset_id=''):
        """
        Starts the data subscription process.
        """
        self.streams = ['met']
        if headset_id:
            self.c.set_wanted_headset(headset_id)
        self.c.open()

    def sub(self, streams):
        """
        Subscribes to data streams.
        """
        self.c.sub_request(streams)

    def on_create_session_done(self, *args, **kwargs):
        """
        Callback for when a session is created.
        """
        print("Session created. Subscribing to 'met' stream...")
        self.sub(self.streams)

    def on_new_data_labels(self, *args, **kwargs):
        """
        Handles new data labels and finds the index for 'foc' (attention).
        """
        data = kwargs.get('data')
        if data['streamName'] == 'met':
            self.met_labels = data['labels']
            print(f"Performance metrics labels: {self.met_labels}")
            if 'foc' in self.met_labels:
                self.attention_index = self.met_labels.index('foc')
                print(f"Found 'attention' (foc) at index: {self.attention_index}")
            else:
                print("Warning: 'foc' label not found in 'met' stream.")

    def on_new_met_data(self, *args, **kwargs):
        """
        Handles new performance metrics data and prints the attention value.
        """
        data = kwargs.get('data')
        if self.attention_index != -1 and len(data['met']) > self.attention_index:
            attention_value = data['met'][self.attention_index]
            print(f"Attention value: {attention_value:.4f}")
        else:
            # Print the raw data if the index hasn't been found yet
            print(f"Received performance metrics data: {data}")

    def on_inform_error(self, *args, **kwargs):
        """
        Handles errors reported by Cortex.
        """
        error_data = kwargs.get('error_data')
        print(f"Error received: {error_data}")

def main():
    """
    Main function to run the AttentionReader.
    """
    print("Starting attention reader example...")
    # Use a virtual headset for simulated data
    # To use a real headset, you can pass its ID to start(), e.g., start('EPOCX-XXXXXXX')
    reader = AttentionReader(CLIENT_ID, CLIENT_SECRET)
    reader.start()

    # Keep the script running to receive data
    print("Running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        reader.c.close()

if __name__ == '__main__':
    main()
