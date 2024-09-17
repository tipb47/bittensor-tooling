import argparse
from curses import meta
import os
from re import I
import subprocess
import time
import json
import requests
import bittensor as bt
import threading

# Colors
pure_red = "\033[0;31m"
dark_green = "\033[0;32m"
orange = "\033[0;33m"
dark_blue = "\033[0;34m"
bright_purple = "\033[0;35m"
dark_cyan = "\033[0;36m"
dull_white = "\033[0;37m"
pure_black = "\033[0;30m"
bright_red = "\033[0;91m"
light_green = "\033[0;92m"
yellow = "\033[0;93m"
bright_blue = "\033[0;94m"
magenta = "\033[0;95m"
light_cyan = "\033[0;96m"
bright_black = "\033[0;90m"
bright_white = "\033[0;97m"
cyan_back = "\033[0;46m"
purple_back = "\033[0;45m"
white_back = "\033[0;47m"
blue_back = "\033[0;44m"
orange_back = "\033[0;43m"
green_back = "\033[0;42m"
pink_back = "\033[0;41m"
grey_back = "\033[0;40m"
grey = '\033[38;4;236m'
bold = "\033[1m"
underline = "\033[4m"
italic = "\033[3m"
darken = "\033[2m"
invisible = '\033[08m'
reverse_colour = '\033[07m'
reset_colour = '\033[0m'
grey = "\x1b[90m"

# Function to send notifications to a Discord webhook
def send_discord_notification(webhook_url, wallet_name, regs_array):

    description = f"WALLET NAME: **{wallet_name}**\n\n"

    for reg in regs_array: #loop and get regs
        subnet = reg[0]
        cost = reg[1]

        description += f"SUBNET ID: **{subnet}** @ PRICE: **{cost}**\n\n"

    embed = {
        "title": "CHEAP REGS",
        "color": 5814701,
        "description": description,
        "footer": {"text": "CHEAP REGS BOT XD"}
    }
    data = {"embeds": [embed]}
    response = requests.post(webhook_url, json=data)
    return response.status_code


# Function to get wallet configuration
def get_wallet_config(wallet_name, wallet_hotkey):
    print(reset_colour + italic + f"Getting wallet config for {wallet_name}")
    parser = argparse.ArgumentParser()
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    config = bt.config(parser)
    config.wallet.name = wallet_name
    config.wallet.hotkey = wallet_hotkey
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    wallet_config ={
        'wallet': wallet,
        'subtensor': subtensor,
        'successful_subnets': []
    }
    return wallet_config

# Function to check wallet registration status
def check_wallet_registration_status(wallet_config, metagraph):
    axons = metagraph.axons
    for axon in axons:
        if axon.hotkey == wallet_config['wallet'].get_hotkey().ss58_address:
            return True
    return False

# Register given subnet, threshold, try to register on subnet
def register_wallet(wallet_config, registration_threshold_price, wallet_name, subnet, metagraph):
    try:
        subtensor = wallet_config['subtensor']

        register_cost = subtensor.burn(subnet).tao

        if register_cost < registration_threshold_price:

            print(orange + f"{wallet_name} || Attempting registration on SN {subnet} at price: {register_cost}τ")

            registration_attempt = subtensor.burned_register(
                wallet=wallet_config['wallet'],
                netuid=subnet,
                wait_for_finalization=True
            )

            if registration_attempt:
                wallet_config['successful_subnets'].append([subnet, register_cost])
                return True # Registration successful
            
            else: #too many regs in interval
                print(pure_red + f"{wallet_name} FAILURE || Too many registrations this interval.")
                wallet_config['too_many_regs_interval_status'] = True
                return False
            
        else: #Too expensive
            print(pure_red + f"{wallet_name} || SN {subnet} too expensive: {register_cost}τ")
            return False

    except Exception as e: #Registration failed but can retry
        print(pure_red + f"{wallet_name} || Error during registration: {e}")
        return False

# Main function
if __name__ == "__main__":
    webhook_url = "https://discord.com/api/webhooks/1197404476076728370/Ht13N7sFDQsVxMgb-xUI2eMWbyzqYVKUuReeSd47qibnfwwtHQ1v_JCwIt4Nmk8nJevm"

    wallets = input(reset_colour + italic + "Input Wallets (NO DUPES) || wallet1, wallet2, wallet3...\n>>> ").replace(" ","").split(',')
    registration_threshold = input("Config || Registration_Threshold\n>>> ").replace(" ","")

    #specific subnets check
    specific_subnets = input("Any specific subnets? (Enter to skip)\n>>> ").replace(" ","").split(',')

    #casting to correct types
    registration_threshold = float(registration_threshold)

    if specific_subnets == ['']:
        specific_subnets = "All"
    
    print()
    print(bright_white + "CONFIG                                                ")
    print(bright_white + '======================================================')
    print(bright_white + f"Wallet(s): {wallets}")
    print(bright_white + f"    Registration Threshold: {registration_threshold}")
    print(bright_white + f"    Subnet(s): {specific_subnets}")
    print(bright_white + '======================================================')
    print(reset_colour + italic + "")
    input(reset_colour + italic + f"Click enter to run :D || {len(wallets)} will be looped || CTRL + Z to quit")

    def run_sniper(wallet_name, registration_threshold):
        
        while True:
            try:
                wallet_config = get_wallet_config(wallet_name, wallet_name)
                break
            except:
                print("error connecting, retrying...")
                time.sleep(10)
        if specific_subnets != "All": #specific ones to register
            for subnet in specific_subnets:
                subnet = int(subnet) #cast to int
            
                metagraph = wallet_config['subtensor'].metagraph(subnet)

                is_registered = check_wallet_registration_status(wallet_config, metagraph)

                if not is_registered:

                    registration_status = register_wallet(wallet_config, registration_threshold, wallet_name, subnet, metagraph)

                    if registration_status:
                        print(light_green + f"{wallet_name} || Wallet {wallet_name} successfully registered (SN {subnet})")

                else:
                    print(pure_red + f"{wallet_name} || Wallet is already registered (SN {subnet})")

        else: #not specific ones to register
            for i in range(1,33):
                # i == subnet id, try each one (1-32)

                metagraph = wallet_config['subtensor'].metagraph(i)

                is_registered = check_wallet_registration_status(wallet_config, metagraph)

                if not is_registered:

                    registration_status = register_wallet(wallet_config, registration_threshold, wallet_name, i, metagraph)

                    if registration_status:
                        print(light_green + f"{wallet_name} || Wallet {wallet_name} successfully registered (SN {i})")

                else:
                    print(pure_red + f"{wallet_name} || Wallet is already registered (SN {i})")

        if wallet_config['successful_subnets']: #successful regs, lets send them.
            print(light_green + f"{wallet_name} DONE || Sending registration webhook...")
            send_discord_notification(webhook_url, wallet_name, wallet_config['successful_subnets'])


    while True:
        for wallet in wallets:
            run_sniper(wallet, registration_threshold)
