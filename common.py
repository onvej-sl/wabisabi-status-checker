import math
import random
import requests
import time
import logging
import lzma


class RequestException(Exception):
    pass


def exponential_distribution(mean):
    # lambda = 1 / mean
    return math.log(1 - random.random()) / (-1.0 / mean)


def get_tor_proxy(tor_server_address="127.0.0.1", tor_server_port="9050"):
    # TOR uses different circuit for each pair of user and password
    tor_server_username = "user"
    tor_server_password = random.randrange(1024)
    tor_server_url = f"socks5://{tor_server_username}:{tor_server_password}@{tor_server_address}:{tor_server_port}"
    return dict(https=tor_server_url, http=tor_server_url)


def get_status():
    url = "https://wasabiwallet.io/WabiSabi/status"
    request_json = {"roundCheckpoints": []}

    proxies = get_tor_proxy()

    logging.info("Status request")
    try:
        response = requests.post(url, proxies=proxies, json=request_json)
        response.raise_for_status()
    except:
        raise RequestException()
    logging.info("Status response")

    return response.json()


class CompressedFile:
    def __init__(self, filename):
        self.file = open(filename, "xb", buffering=0)
        self.compressor = lzma.LZMACompressor()

    def write(self, data):
        self.file.write(self.compressor.compress(data.encode("utf8")))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.file.write(self.compressor.flush())
        self.file.close()


def wabisabi_status_checker(output_filename):
    # This is interval after which ended rounds are removed from status
    round_expiry_timeout_in_seconds = 5 * 60
    mean_sleep_time_in_seconds = 30
    maximum_sleep_time_in_seconds = round_expiry_timeout_in_seconds // 2
    mean_retry_time_in_seconds = 10

    with open(output_filename, "a") as file:
        logged_round_ids = []
        while True:
            try:
                status = get_status()

                # Get only rounds that are in phase "ended"
                ended_round_states = [
                    round_state for round_state in status["roundStates"] if round_state["phase"] == 4]

                # Log round states that have not been logged yed
                for round_state in ended_round_states:
                    if round_state["id"] not in logged_round_ids:
                        logging.info(f"Round {round_state['id']} found")
                        file.write(str(round_state) + "\n")

                # Update the list of logged round states
                logged_round_ids = [round_state["id"]
                                    for round_state in ended_round_states]

                # Sleep for random time
                sleep_time_in_seconds = min(exponential_distribution(
                    mean_sleep_time_in_seconds), maximum_sleep_time_in_seconds)
                logging.info(f"Sleeping for {sleep_time_in_seconds:.0f} seconds")
                time.sleep(sleep_time_in_seconds)

            except RequestException:
                logging.error("Status request failed")
                sleep_time_in_seconds = min(exponential_distribution(
                    mean_retry_time_in_seconds), maximum_sleep_time_in_seconds)
                logging.info(f"Sleeping for {sleep_time_in_seconds:.0f} seconds")
                time.sleep(sleep_time_in_seconds)
