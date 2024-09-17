import argparse
import os
import subprocess
import time
import json
import requests
import bittensor as bt

# Function to send notifications to a Discord webhook
def send_discord_notification(webhook_url, wallet_name, uid, subnet_id, cost, wallet_hotkey):
    embed = {
        "title": "Wallet Registration Success",
        "color": 5814783,  # You can change this to any color you prefer
        "fields": [
            {"name": "Wallet Name", "value": wallet_name, "inline": True},
            {"name": "UID", "value": str(uid), "inline": True},
            {"name": "Subnet ID", "value": str(subnet_id), "inline": False},
            {"name": "Registration Cost", "value": f"{cost} TAO", "inline": False},
            {"name": "DEREG FORMAT", "value": f"{wallet_name},{wallet_hotkey},{str(subnet_id)}", "inline": False}
        ],
        "footer": {"text": "Bittensor Wallet Registration"}
    }
    data = {"embeds": [embed]}
    response = requests.post(webhook_url, json=data)
    return response.status_code


# Function to get wallet configuration
def get_wallet_config(wallet_name, wallet_hotkey, subnet_id):
    print(f"Getting wallet config for {wallet_name}")
    parser = argparse.ArgumentParser()
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    config = bt.config(parser)
    config.wallet.name = wallet_name
    config.wallet.hotkey = wallet_hotkey
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(subnet_id)
    wallet_config ={
        'wallet': wallet,
        'subnet_id': subnet_id,
        'subtensor': subtensor,
        'metagraph': metagraph,
        'hotkey': wallet_hotkey
    }
    return wallet_config

# Function to check wallet registration status
def check_wallet_registration_status(wallet_config):
    axons = wallet_config['metagraph'].axons
    for axon in axons:
        if axon.hotkey == wallet_config['wallet'].get_hotkey().ss58_address:
            return True
    return False

# Function to get wallet UID
def get_wallet_uid(wallet_config):
    metagraph = wallet_config['metagraph']
    axons = metagraph.axons
    uid = 0
    for axon in axons:
        if axon.hotkey == wallet_config['wallet'].get_hotkey().ss58_address:
            return uid
        uid += 1
    return None



# Modified register_wallet function to return status
def register_wallet(wallet_config, webhook_url):
    try:
        subtensor = wallet_config['subtensor']
        register_cost = subtensor.burn(wallet_config['subnet_id']).tao

        if register_cost < registration_threshold:
            registration_attempt = subtensor.burned_register(
                wallet=wallet_config['wallet'],
                netuid=wallet_config['subnet_id'],
                wait_for_finalization=True
            )

            if registration_attempt:
                uid = get_wallet_uid(wallet_config)
                send_discord_notification(webhook_url, wallet_config['wallet'].name, uid, wallet_config['subnet_id'], register_cost, wallet_config['wallet'].get_hotkey().ss58_address)
                return True  # Registration successful
            else:
                print("Failed || Too many registrations this interval.")
                return False  # Registration failed but can retry
        else:
            print(f"Failed || Too expensive, {register_cost}τ")
            return False  # Registration failed but can retry

    except Exception as e:
        print(f"Failed || Error during registration: {e}")
        return False  # Registration failed but can retry

# Main function
if __name__ == "__main__":
    webhook_url = "https://discord.com/api/webhooks/webhook"
    wallet_name = input("Wallet name: ")
    subnet_id = input("Subnet to register on: ")
    registration_threshold = float(input("Registration threshold (won't register above this): "))
    delay = float(input("Monitor delay: "))
    wallet_config = get_wallet_config(wallet_name, wallet_name, subnet_id)

    while True:
        is_registered = check_wallet_registration_status(wallet_config)
        
        if not is_registered:

            print(f"SN {subnet_id} || Attempting to register Wallet {wallet_name}...")

            registration_success = register_wallet(wallet_config, webhook_url)

            if registration_success:
                print(f"SUCCESS || Wallet {wallet_name} successfully registered.")
                break  # Exit loop if registration is successful
        else:
            print(f"ERROR || Wallet {wallet_name} is already registered.")
            break  # Exit loop if wallet is already registered
        
        if delay != 0.0:
            time.sleep(delay)  # Wait before retrying

    print("Script finished.")
