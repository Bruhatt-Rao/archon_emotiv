import os
import time
import threading
from flask import Flask, jsonify
from dotenv import load_dotenv
from cortex import Cortex

# --- Global State & Threading Lock ---
# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Store the latest metric values
latest_metrics = {}
# Lock for thread-safe access to the latest_metrics
metrics_lock = threading.Lock()

# --- Cortex API Client in a Background Thread ---
class CortexClient(threading.Thread):
    """
    A class to run the Cortex client in a separate thread,
    continuously updating the attention value.
    """
    def __init__(self, app_client_id, app_client_secret, **kwargs):
        super().__init__()
        self.name = 'CortexClientThread'
        self.daemon = True  # Allows main thread to exit even if this thread is running
        print("CortexClient thread initialized")
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=False, **kwargs)
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(new_data_labels=self.on_new_data_labels)
        self.c.bind(new_met_data=self.on_new_met_data)
        self.c.bind(inform_error=self.on_inform_error)
        self.metric_indices = {}

    def run(self):
        """
        The main loop for the background thread.
        """
        print("Starting Cortex client WebSocket connection...")
        self.c.open()
        print("Cortex WebSocket opened. Thread is now waiting for messages.")
        # The websocket client runs in its own thread, so we just need to keep this one alive.
        while True:
            time.sleep(10)

    def on_create_session_done(self, *args, **kwargs):
        print("Session created successfully. Subscribing to 'met' stream...")
        self.c.sub_request(['met'])

    def on_new_data_labels(self, *args, **kwargs):
        data = kwargs.get('data')
        if data['streamName'] == 'met':
            labels = data['labels']
            # Filter out any labels containing 'isActive'
            self.metric_indices = {label: i for i, label in enumerate(labels) if 'isActive' not in label}
            print(f"Metrics labels received and filtered: {list(self.metric_indices.keys())}")

    def on_new_met_data(self, *args, **kwargs):
        global latest_metrics
        data = kwargs.get('data')
        # Ensure we have the labels before processing data
        if not self.metric_indices:
            return

        new_metrics = {}
        for label, index in self.metric_indices.items():
            if len(data['met']) > index:
                new_metrics[label] = data['met'][index]
        
        if new_metrics:
            with metrics_lock:
                latest_metrics.update(new_metrics)
            print(f"Updated metrics: {new_metrics}")

    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get('error_data')
        print(f"Cortex error received: {error_data}")

# --- Flask Application ---
app = Flask(__name__)

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Endpoint to get the latest performance metrics.
    """
    with metrics_lock:
        response = latest_metrics.copy()
    return jsonify(response)

@app.route('/', methods=['GET'])
def index():
    """
    A simple index route to show the server is running.
    """
    return "<h2>Metrics Server is Running</h2><p>Access the performance metrics at the <a href='/metrics'>/metrics</a> endpoint.</p>"

def flow_score(stress, engagement, interest, excitement, attention, relaxation):
    """
    Computes a normalized flow state score (0–1) based on six input metrics.

    Parameters:
    - stress (float): Stress level (0–1)
    - engagement (float): Engagement level (0–1)
    - interest (float): Interest level (0–1)
    - excitement (float): Excitement level (0–1)
    - attention (float): Attention level (0–1)
    - relaxation (float): Relaxation level (0–1)

    Returns:
    - float: Normalized flow state score (0–1)
    """
    def inverted_u_curve(x):
        """Inverted-U curve centered at 0.5."""
        return -4 * (x - 0.5) ** 2 + 1

    # Normalize inputs to [0, 1]
    stress = max(0, min(1, stress))
    engagement = max(0, min(1, engagement))
    interest = max(0, min(1, interest))
    excitement = max(0, min(1, excitement))
    attention = max(0, min(1, attention))
    relaxation = max(0, min(1, relaxation))

    # Compute individual contributions
    stress_score = inverted_u_curve(stress) * 0.15
    excitement_score = inverted_u_curve(excitement) * 0.15
    engagement_score = engagement * 0.20
    interest_score = interest * 0.15
    attention_score = attention * 0.25
    relaxation_score = inverted_u_curve(relaxation) * 0.10

    # Compute total score and clamp to [0, 1]
    total_score = stress_score + excitement_score + engagement_score + interest_score + attention_score + relaxation_score
    return max(0, min(1, total_score))

# Example calls

# print("Flow-like state:", flow_score(0.5, 0.9, 0.8, 0.5, 0.95, 0.4))  # Expected: High score (~0.9)
# print("Bored state:", flow_score(0.2, 0.3, 0.2, 0.2, 0.3, 0.8))        # Expected: Low score (~0.3)
# print("Overstressed state:", flow_score(0.9, 0.7, 0.6, 0.9, 0.8, 0.2)) # Expected: Moderate score (~0.6)

def main():
    """
    Main function to start the Cortex client and the Flask server.
    """
    print("Starting application...")
    
    # Start the Cortex client in the background
    cortex_client = CortexClient(CLIENT_ID, CLIENT_SECRET)
    cortex_client.start()
    
    # Give the Cortex client a moment to initialize
    time.sleep(5) 
    
    # Run the Flask app
    # Use host='0.0.0.0' to make it accessible on your local network
    app.run(host='0.0.0.0', port=5001)

if __name__ == '__main__':
    main()
