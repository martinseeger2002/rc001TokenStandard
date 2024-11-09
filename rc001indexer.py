import json
import base64
import binascii
import sqlite3
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bs4 import BeautifulSoup
import time
import configparser

# Connect to Bitcoin RPC
rpc_user = "1234"
rpc_password = "pass"
rpc_host = "localhost"
rpc_port = "22555"
rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"

# Function to establish a connection to the Bitcoin RPC server
def connect_to_rpc():
    try:
        return AuthServiceProxy(rpc_url, timeout=60)
    except Exception as e:
        print(f"Error connecting to RPC server: {e}")
        return None

# Load last scanned block height
try:
    with open('./db/last_block_scaned.json', 'r') as f:
        last_block_height = json.load(f).get('last_block_height', 0)
except FileNotFoundError:
    last_block_height = 0

# Function to update last scanned block height
def update_last_block_height(block_height):
    with open('./db/last_block_scaned.json', 'w') as f:
        json.dump({'last_block_height': block_height}, f)

# Function to decode hex to base64
def hex_to_base64(hex_str):
    try:
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
        print(f"Problematic base64 string: {base64_str}")
        return None

# Function to convert hex to ASCII
def hex_to_ascii(hex_string):
    try:
        return binascii.unhexlify(hex_string).decode('ascii')
    except Exception as e:
        print(f"Error converting hex to ASCII: {e}")
        return None

# Function to process the genesis transaction
def process_genesis_tx(asm_data):
    data_string = ""
    num_chunks = int(asm_data[1].lstrip('-'))
    mime_type_hex = asm_data[2]
    mime_type = hex_to_ascii(mime_type_hex)

    index = 3
    while index < len(asm_data):
        if asm_data[index].lstrip('-').isdigit():
            num_chunks = int(asm_data[index].lstrip('-'))
            data_chunk = asm_data[index + 1]
            data_string += data_chunk
            index += 2

            if num_chunks == 0:
                return data_string, mime_type, True
        else:
            break

    return data_string, mime_type, False

# Function to process subsequent transactions
def process_subsequent_tx(asm_data):
    data_string = ""
    index = 0
    while index < len(asm_data):
        if asm_data[index].lstrip('-').isdigit():
            num_chunks = int(asm_data[index].lstrip('-'))
            data_chunk = asm_data[index + 1]
            data_string += data_chunk
            index += 2

            if num_chunks == 0:
                return data_string, True
        else:
            break

    return data_string, False

# Function to check if trait_index is valid
def is_valid_trait_index(trait_index, collection_name):
    # Split the trait_index into two-digit segments
    segments = [trait_index[i:i+2] for i in range(0, len(trait_index), 2)]
    print(f"Segments: {segments}")  # Debugging output
    
    # Load the configuration file
    config = configparser.ConfigParser()
    config_path = f'./conf/{collection_name}.conf'
    config.read(config_path)
    
    # Check each segment against the valid range
    for i, segment in enumerate(segments):
        range_key = f'trait_index_{i}'
        if range_key in config['DEFAULT']:
            valid_range = config['DEFAULT'][range_key].split('-')
            print(f"Checking segment {segment} against range {valid_range}")  # Debugging output
            if not (valid_range[0] <= segment <= valid_range[1]):
                print(f"Segment {segment} is out of range {valid_range}")  # Debugging output
                return False
        else:
            # If no range is specified for a segment, assume it's invalid
            print(f"No range specified for segment {i}")  # Debugging output
            return False
    
    return True

# Function to process transactions
def process_transaction(txid):
    rpc_connection = connect_to_rpc()
    if rpc_connection is None:
        return

    try:
        raw_tx = rpc_connection.getrawtransaction(txid)
        decoded_tx = rpc_connection.decoderawtransaction(raw_tx)
    except Exception as e:
        print(f"Error processing transaction {txid}: {e}")
        return

    is_genesis = True
    data_string = ""
    mime_type = None
    inscription_address = None

    for vin in decoded_tx['vin']:
        if 'scriptSig' in vin and 'asm' in vin['scriptSig']:
            asm_data = vin['scriptSig']['asm'].split()
            if asm_data[0] == '6582895':
                if is_genesis:
                    new_data_string, mime_type, end_of_data = process_genesis_tx(asm_data)
                    data_string += new_data_string
                    is_genesis = False
                else:
                    new_data_string, end_of_data = process_subsequent_tx(asm_data)
                    data_string += new_data_string

                if end_of_data:
                    break

    # Extract the address from the transaction outputs
    for vout in decoded_tx['vout']:
        if 'scriptPubKey' in vout and 'addresses' in vout['scriptPubKey']:
            inscription_address = vout['scriptPubKey']['addresses'][0]
            break

    if data_string:
        html_data_base64 = hex_to_base64(data_string)
        if html_data_base64:
            html_data_text = base64_to_text(html_data_base64)
            if html_data_text and '<meta name="p" content="rc001">' in html_data_text:
                print(f"Decoded HTML text: {html_data_text}")
                
                # Use BeautifulSoup to parse the HTML content
                soup = BeautifulSoup(html_data_text, 'html.parser')
                
                # Extract title
                title_tag = soup.find('title')
                title = title_tag.string if title_tag else 'Untitled'
                
                # Extract trait_index
                trait_index_meta = soup.find('meta', attrs={'name': 'trait_index'})
                trait_index = trait_index_meta['content'] if trait_index_meta else 'Unknown'
                
                # Check if the trait_index is valid
                if not is_valid_trait_index(trait_index, title):
                    print(f"Invalid trait_index: {trait_index}")
                    return
                
                # Create or connect to SQLite database
                db_path = f'./db/{title}.db'
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS items (
                                item_no INTEGER PRIMARY KEY AUTOINCREMENT,
                                inscription_id TEXT UNIQUE,
                                trait_id TEXT,
                                inscription_status TEXT,
                                inscription_address TEXT)''')
                
                # Check if inscription_id or trait_id already exists
                inscription_id = f"{txid}i0"
                c.execute('SELECT * FROM items WHERE inscription_id=? OR trait_id=?', (inscription_id, trait_index))
                if not c.fetchone():
                    # Insert new entry
                    c.execute('INSERT INTO items (inscription_id, trait_id, inscription_status, inscription_address) VALUES (?, ?, ?, ?)',
                              (inscription_id, trait_index, 'minted', inscription_address))
                    conn.commit()
                conn.close()

# Main loop to continuously scan for new blocks
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
            block = rpc_connection.getblock(block_hash)
            for txid in block['tx']:
                process_transaction(txid)
            update_last_block_height(block_height)

        # Update last_block_height to the current block height
        last_block_height = current_block_height

        # Wait for 2 minutes before checking for new blocks
        time.sleep(120)
    except (BrokenPipeError, JSONRPCException) as e:
        print(f"RPC error: {e}")
        time.sleep(60)  # Wait before retrying
    except Exception as e:
        print(f"Unexpected error: {e}")
        break
