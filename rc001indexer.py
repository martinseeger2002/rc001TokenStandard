import json
import base64
import binascii
import sqlite3
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bs4 import BeautifulSoup
import time
import configparser
import os
import re
from decimal import Decimal

# Connect to Bitcoin RPC
rpc_user = "1234"
rpc_password = "pass"
rpc_host = "localhost"
rpc_port = "22555"  # Default port for Dogecoin
rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"

# Function to establish a connection to the Bitcoin RPC server
def connect_to_rpc():
    try:
        return AuthServiceProxy(rpc_url, timeout=60)
    except Exception as e:
        print(f"Error connecting to RPC server: {e}")
        return None

# Load last scanned block height
def load_last_block_height():
    try:
        with open('./last_block_scaned.json', 'r') as f:
            return json.load(f).get('last_block_height', 0)
    except FileNotFoundError:
        return 0

# Function to update last scanned block height
def update_last_block_height(block_height):
    with open('./last_block_scaned.json', 'w') as f:
        json.dump({'last_block_height': block_height}, f)

# Function to decode hex to base64
def hex_to_base64(hex_str):
    try:
        if len(hex_str) % 2 != 0:
            print("Odd-length hex string detected. Skipping transaction.")
            return None
        return base64.b64encode(binascii.unhexlify(hex_str)).decode('utf-8')
    except binascii.Error as e:
        print(f"Error decoding hex to base64: {e}")
        return None

# Function to decode base64 to text
def base64_to_text(base64_str):
    try:
        return base64.b64decode(base64_str).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError) as e:
        print(f"Error decoding base64 to text: {e}")
        return None

# Function to convert hex to ASCII
def hex_to_ascii(hex_string):
    try:
        if len(hex_string) % 2 != 0:
            print("Odd-length hex string detected. Skipping transaction.")
            return None
        return binascii.unhexlify(hex_string).decode('ascii')
    except Exception as e:
        print(f"Error converting hex to ASCII: {e}")
        return None

# Function to check if sn is valid
def is_valid_sn(sn, collection_name):
    # Load the configuration file
    config = configparser.ConfigParser()
    config_path = f'./collections/{collection_name}.conf'
    if not os.path.exists(config_path):
        print(f"Configuration file {config_path} does not exist.")
        return False
    config.read(config_path)
    
    # Check if the entire sn is within a single range
    if 'sn_range' in config['DEFAULT']:
        valid_range = config['DEFAULT']['sn_range'].split('-')
        if len(valid_range[0]) > 2 and len(valid_range[1]) > 2:
            if valid_range[0] <= sn.zfill(len(valid_range[1])) <= valid_range[1]:
                print(f"Serial number {sn} is within the single range {valid_range}.")
                return True
            else:
                print(f"Serial number {sn} is not within the single range {valid_range}.")
                return False

    # Check if there is only one sn_index key
    sn_index_keys = [key for key in config['DEFAULT'] if key.startswith('sn_index_')]
    if len(sn_index_keys) == 1:
        valid_range = config['DEFAULT'][sn_index_keys[0]].split('-')
        if valid_range[0] <= sn.zfill(len(valid_range[1])) <= valid_range[1]:
            print(f"Serial number {sn} is within the single range {valid_range}.")
            return True
        else:
            print(f"Serial number {sn} is not within the single range {valid_range}.")
            return False

    # Check segmented ranges
    segments = [sn[i:i+2] for i in range(0, len(sn), 2)]
    for i, segment in enumerate(segments):
        range_key = f'sn_index_{i}'
        if range_key in config['DEFAULT']:
            valid_range = config['DEFAULT'][range_key].split('-')
            padded_segment = segment.zfill(len(valid_range[1]))
            if valid_range[0] <= padded_segment <= valid_range[1]:
                print(f"Segment {padded_segment} of serial number {sn} is within range {valid_range}.")
            else:
                print(f"Segment {padded_segment} of serial number {sn} is not within range {valid_range}.")
                return False
        else:
            print(f"Range key {range_key} not found in configuration.")
            return False
    return True

# Function to sanitize the collection name
def sanitize_filename(name):
    # Remove any character that is not alphanumeric, underscore, or hyphen
    return re.sub(r'[^\w\-]', '', name)

# Function to process transactions
def process_transaction(tx, rpc_connection):
    txid = tx['txid']

    # Check if there is at least one vin
    if not tx.get('vin'):
        return

    vin = tx['vin'][0]

    # Check if 'scriptSig' and 'asm' are present in vin[0]
    if 'scriptSig' in vin and 'asm' in vin['scriptSig']:
        asm_data = vin['scriptSig']['asm'].split()
        # Check if '6582895' is the first opcode
        if asm_data and asm_data[0] == '6582895':
            # Proceed to extract inscription data
            data_string, mime_type = extract_inscription_data(asm_data)
            if not data_string or not mime_type or 'text/html' not in mime_type.lower():
                return  # Skip if no data or MIME type does not contain 'text/html'

            # Decode and process the HTML data
            html_data_base64 = hex_to_base64(data_string)
            if not html_data_base64:
                return
            html_data_text = base64_to_text(html_data_base64)
            if not html_data_text or '<meta name="p" content="rc001">' not in html_data_text:
                return  # Skip if protocol identifier not found

            # Use BeautifulSoup to parse the HTML content
            soup = BeautifulSoup(html_data_text, 'html.parser')

            # Extract the operation type
            op_meta = soup.find('meta', attrs={'name': 'op'})
            if op_meta and op_meta.get('content') == 'deploy':
                handle_deploy_operation(soup, txid, tx)
            elif op_meta and op_meta.get('content') == 'mint':
                handle_mint_operation(soup, txid, tx)
            else:
                return  # Operation not 'deploy' or 'mint', skip
    else:
        return  # 'scriptSig' or 'asm' not in vin[0], skip transaction

def extract_inscription_data(asm_data):
    data_string = ""
    mime_type = None
    index = 1  # Start after '6582895'

    if index >= len(asm_data):
        return None, None

    # Process genesis transaction
    num_chunks = asm_data[index]
    if not num_chunks.lstrip('-').isdigit():
        return None, None
    index += 1

    if index >= len(asm_data):
        return None, None

    mime_type_hex = asm_data[index]
    mime_type = hex_to_ascii(mime_type_hex)
    index += 1

    while index < len(asm_data):
        part = asm_data[index]
        if part.lstrip('-').isdigit():
            # Number of chunks
            index += 1
            if index >= len(asm_data):
                return None, None
            data_chunk = asm_data[index]
            data_string += data_chunk
            index += 1
        else:
            break

    return data_string, mime_type

def handle_deploy_operation(soup, txid, tx):
    # Extract title
    title_tag = soup.find('title')
    title = title_tag.string if title_tag else 'Untitled'
    sanitized_title = sanitize_filename(title)
    config_path = f'./collections/{sanitized_title}.conf'

    if os.path.exists(config_path):
        print(f"Configuration file {config_path} already exists. Skipping deploy transaction.")
        return

    # Extract JSON data
    json_script = soup.find('script', attrs={'type': 'application/json', 'id': 'json-data'})
    if json_script and json_script.string:
        json_string = json_script.string.strip().replace('\xa0', ' ')
        try:
            json_data = json.loads(json_string)
            sn_ranges = json_data.get('sn', [])
            mint_address = json_data.get('mint_address', 'Unknown')
            mint_price = json_data.get('mint_price', 'Unknown')
            parent_inscription_id = json_data.get('parent_inscription_id', 'Unknown')

            # Get inscription address from vout[0]
            inscription_address = None
            if tx['vout']:
                vout0 = tx['vout'][0]
                if 'scriptPubKey' in vout0 and 'addresses' in vout0['scriptPubKey']:
                    inscription_address = vout0['scriptPubKey']['addresses'][0]

            # Create configuration file
            with open(config_path, 'w') as config_file:
                config_file.write('[DEFAULT]\n')
                config_file.write(f'mint_address: {mint_address}\n')
                config_file.write(f'mint_price: {mint_price}\n')
                config_file.write(f'parent_inscription_id: {parent_inscription_id}\n')
                config_file.write(f'emblem_inscription_id: {json_data.get("emblem_inscription_id", "Unknown")}\n')
                config_file.write(f'website: {json_data.get("website", "Unknown")}\n')
                config_file.write(f'deploy_txid: {txid}\n')
                config_file.write(f'deploy_address: {inscription_address}\n')
                for i, sn in enumerate(sn_ranges):
                    config_file.write(f'sn_index_{i}: {sn["range"]}\n')

            print(f"Configuration file created at {config_path}")

            # Initialize the database for the collection
            db_path = f'./collections/{sanitized_title}.db'
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS items (
                            item_no INTEGER PRIMARY KEY AUTOINCREMENT,
                            inscription_id TEXT UNIQUE,
                            sn TEXT UNIQUE,
                            inscription_status TEXT,
                            inscription_address TEXT)''')
            conn.commit()
            conn.close()
            print(f"Database initialized at {db_path}")

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return
    else:
        print("No valid JSON data found in deploy operation.")
        return

def handle_mint_operation(soup, txid, tx):
    # Extract title
    title_tag = soup.find('title')
    title = title_tag.string if title_tag else 'Untitled'
    sanitized_title = sanitize_filename(title)
    config_path = f'./collections/{sanitized_title}.conf'

    if not os.path.exists(config_path):
        print(f"Configuration file {config_path} does not exist. Skipping mint transaction.")
        return

    # Extract serial number (sn)
    sn_meta = soup.find('meta', attrs={'name': 'sn'})
    sn = sn_meta['content'] if sn_meta else 'Unknown'

    if not is_valid_sn(sn, sanitized_title):
        print(f"Invalid serial number: {sn}")
        return

    # Extract parent_inscription_id from config and compare with script src
    config = configparser.ConfigParser()
    config.read(config_path)
    parent_inscription_id = config['DEFAULT'].get('parent_inscription_id', 'Unknown')

    script_tag = soup.find('script', src=True)
    if script_tag:
        script_src = script_tag['src']
        parent_inscription_id_from_script = script_src.split('/')[-1]
        if parent_inscription_id_from_script != parent_inscription_id:
            print(f"Parent inscription ID mismatch. Skipping mint transaction.")
            return
    else:
        print("No script tag found in mint operation. Skipping transaction.")
        return

    # Validate the mint payment
    mint_price_sats = float(config['DEFAULT'].get('mint_price', '0'))
    mint_price_btc = Decimal(mint_price_sats) / Decimal(100000000)  # Convert satoshis to bitcoins
    mint_address = config['DEFAULT'].get('mint_address', 'Unknown')

    # Modify here to skip payment validation if mint_price_btc is zero
    if mint_price_btc > 0:
        valid_payment = False
        for vout in tx['vout']:
            if 'value' in vout and 'scriptPubKey' in vout and 'addresses' in vout['scriptPubKey']:
                if Decimal(vout['value']) == mint_price_btc and mint_address in vout['scriptPubKey']['addresses']:
                    valid_payment = True
                    break
        if not valid_payment:
            print(f"Transaction does not pay the mint price of {mint_price_btc} BTC to {mint_address}. Skipping transaction.")
            return

    # Create or connect to SQLite database
    db_path = f'./collections/{sanitized_title}.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items (
                    item_no INTEGER PRIMARY KEY AUTOINCREMENT,
                    inscription_id TEXT UNIQUE,
                    sn TEXT UNIQUE,
                    inscription_status TEXT,
                    inscription_address TEXT)''')

    # Check if sn already exists
    c.execute('SELECT * FROM items WHERE sn=?', (sn,))
    existing_entry = c.fetchone()

    if existing_entry:
        print(f"Serial number {sn} already exists. Skipping transaction.")
        conn.close()
        return
    else:
        # Insert new entry
        inscription_id = f"{txid}i0"
        # Get inscription address from vout[0]
        inscription_address = None
        if tx['vout']:
            vout0 = tx['vout'][0]
            if 'scriptPubKey' in vout0 and 'addresses' in vout0['scriptPubKey']:
                inscription_address = vout0['scriptPubKey']['addresses'][0]

        c.execute('INSERT INTO items (inscription_id, sn, inscription_status, inscription_address) VALUES (?, ?, ?, ?)',
                  (inscription_id, sn, 'minted', inscription_address))
        conn.commit()
        conn.close()
        print(f"Minted item with SN {sn} added to database.")

# Main loop to continuously scan for new blocks
def main():
    last_block_height = load_last_block_height()
    while True:
        rpc_connection = connect_to_rpc()
        if rpc_connection is None:
            time.sleep(60)  # Wait before retrying
            continue

        try:
            current_block_height = rpc_connection.getblockcount()
            start_block_height = last_block_height + 1

            # Process any new blocks
            for block_height in range(start_block_height, current_block_height + 1):
                block_hash = rpc_connection.getblockhash(block_height)
                # Fetch block with transactions decoded
                block = rpc_connection.getblock(block_hash, 2)
                transactions = block['tx']
                for tx in transactions:
                    process_transaction(tx, rpc_connection)
                update_last_block_height(block_height)
                last_block_height = block_height

            # Wait for 30 sec before checking for new blocks
            time.sleep(30)
        except (BrokenPipeError, JSONRPCException) as e:
            print(f"RPC error: {e}")
            time.sleep(1)  # Wait before retrying
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(1)  # Wait before retrying

if __name__ == "__main__":
    main()
