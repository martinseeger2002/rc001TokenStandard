import os
import configparser
import sqlite3
import random
import datetime
import base64
from flask import Blueprint, jsonify, make_response, request
from collections import OrderedDict

# Create a new Blueprint for rc001
rc001_bp = Blueprint('rc001', __name__)

@rc001_bp.route('/api/v1/rc001/collections', methods=['GET'])
def list_collections():
    """
    List all .conf files in the ../rc001 directory and return their contents as key-value pairs.
    """
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../rc001'))
    try:
        # Verify the directory exists
        if not os.path.isdir(conf_dir):
            return jsonify({
                "status": "error",
                "message": f"Directory not found: {conf_dir}"
            }), 404

        # List all files in the directory
        files = os.listdir(conf_dir)
        # Filter for .conf files
        conf_files = [f for f in files if f.endswith('.conf')]
        
        if not conf_files:
            return jsonify({
                "status": "success",
                "collections": {},
                "message": "No configuration files found."
            })

        # Create a dictionary to hold the contents of each .conf file
        collections = {}
        for conf_file in conf_files:
            file_path = os.path.join(conf_dir, conf_file)
            config = configparser.ConfigParser()
            config.read(file_path)
            
            # Assuming all keys are under the 'DEFAULT' section
            collection_data = {key: value for key, value in config['DEFAULT'].items()}
            
            # Calculate max_supply based on sn_index ranges
            max_supply = 1
            for key, value in collection_data.items():
                if key.startswith('sn_index_'):
                    try:
                        start, end = map(int, value.split('-'))
                        max_supply *= (end - start + 1)
                    except ValueError:
                        return jsonify({
                            "status": "error",
                            "message": f"Invalid range format in {conf_file} for key {key}: '{value}'"
                        }), 400
            
            # Connect to the SQLite database to count inscription_id entries
            db_file = os.path.join(conf_dir, conf_file.replace('.conf', '.db'))
            minted = 0
            if os.path.exists(db_file):
                try:
                    with sqlite3.connect(db_file) as conn:
                        cursor = conn.cursor()
                        # Corrected table name from 'inscriptions' to 'items'
                        cursor.execute("SELECT COUNT(*) FROM items WHERE inscription_id IS NOT NULL")
                        result = cursor.fetchone()
                        if result:
                            minted = result[0]
                except sqlite3.Error as e:
                    # Log the error and continue with minted = 0
                    print(f"SQLite error in file {db_file}: {e}")
                    minted = 0
            else:
                # Log the missing database file
                print(f"Database file not found: {db_file}")
                # Optionally, you can decide to skip this collection or handle it differently
                # For now, we'll proceed with minted = 0
            
            # Calculate left_to_mint and percent_minted
            left_to_mint = max_supply - minted
            percent_minted = round((minted / max_supply) * 100, 2) if max_supply > 0 else 0
            
            # Create an OrderedDict to maintain the desired order
            ordered_collection_data = OrderedDict([
                ('mint_address', collection_data.get('mint_address')),
                ('deploy_address', collection_data.get('deploy_address')),
                ('mint_price', collection_data.get('mint_price')),
                ('parent_inscription_id', collection_data.get('parent_inscription_id')),
                ('emblem_inscription_id', collection_data.get('emblem_inscription_id')),
                ('website', collection_data.get('website')),
                ('deploy_txid', collection_data.get('deploy_txid')),
                ('max_supply', max_supply),
                ('minted', minted),
                ('left_to_mint', left_to_mint),
                ('percent_minted', percent_minted),
            ])
            
            # Add sn_index entries in order
            sn_keys = sorted([k for k in collection_data.keys() if k.startswith('sn_index_')])
            for key in sn_keys:
                ordered_collection_data[key] = collection_data[key]
            
            # Use the filename without the .conf extension as the key
            collections[conf_file.replace('.conf', '')] = ordered_collection_data
        
        return jsonify({
            "status": "success",
            "collections": collections
        })
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": "Directory not found"
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def generate_unique_sn(db_file, sn_ranges):
    """Generate a unique SN that is not already minted or older than 24 hours."""
    if not os.path.exists(db_file):
        raise FileNotFoundError(f"Database file not found: {db_file}")

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        # Get all SNs that are minted or older than 24 hours
        cursor.execute("""
            SELECT sn FROM items 
            WHERE inscription_id IS NOT NULL 
            OR (inscription_status IS NOT NULL AND inscription_status < ?)
        """, (datetime.datetime.now() - datetime.timedelta(hours=24),))
        existing_sns = {row[0] for row in cursor.fetchall()}

        # Generate a random SN within the specified ranges
        while True:
            sn_parts = []
            for start, end in sn_ranges:
                sn_part = f"{random.randint(start, end):02}"
                sn_parts.append(sn_part)
            sn = ''.join(sn_parts)
            if sn not in existing_sns:
                return sn

@rc001_bp.route('/api/v1/rc001/mint/<collection_name>', methods=['GET'])
def generate_html(collection_name):
    """
    Generate an HTML page with a unique SN and update the database for a specific collection.
    """
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../rc001'))
    conf_file = f"{collection_name}.conf"
    db_file = os.path.join(conf_dir, conf_file.replace('.conf', '.db'))

    try:
        # Read the configuration file
        file_path = os.path.join(conf_dir, conf_file)
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": f"Configuration file not found: {conf_file}"
            }), 404

        config = configparser.ConfigParser()
        config.read(file_path)
        collection_data = {key: value for key, value in config['DEFAULT'].items()}

        # Parse SN ranges from the configuration file
        sn_ranges = []
        for key, value in collection_data.items():
            if key.startswith('sn_index_'):
                start, end = map(int, value.split('-'))
                sn_ranges.append((start, end))

        # Check if the database file exists
        if not os.path.exists(db_file):
            # Generate a random SN without checking the database
            sn_parts = [f"{random.randint(start, end):02}" for start, end in sn_ranges]
            sn = ''.join(sn_parts)

            # Initialize the database
            with sqlite3.connect(db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sn TEXT NOT NULL,
                        inscription_status TIMESTAMP
                    )
                """)
                conn.commit()
        else:
            # Generate a unique SN
            sn = generate_unique_sn(db_file, sn_ranges)

        # Construct the HTML response
        html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="p" content="rc001"><meta name="op" content="mint"><meta name="sn" content="{sn}"><title>{collection_name}</title></head><body><script src="/content/{collection_data.get('parent_inscription_id')}"></script></body></html>"""
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response

    except FileNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@rc001_bp.route('/api/v1/rc001/inscriptions/<collection_name>/<address>', methods=['GET'])
def list_inscriptions_by_collection_and_address(collection_name, address):
    """
    List all inscription_ids associated with a given address in a specific collection.
    """
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../rc001/{collection_name}.db'))

    if not os.path.exists(db_path):
        return jsonify({
            "status": "error",
            "message": f"Collection '{collection_name}' not found."
        }), 404

    inscriptions = []

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT inscription_id FROM items WHERE inscription_address=? AND inscription_id IS NOT NULL', (address,))
            results = cursor.fetchall()
            inscriptions.extend([row[0] for row in results])

        return jsonify({
            "status": "success",
            "inscriptions": inscriptions
        })
    except sqlite3.Error as e:
        return jsonify({
            "status": "error",
            "message": f"SQLite error: {e}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@rc001_bp.route('/api/v1/rc001/collection/<collection_name>', methods=['GET'])
def list_collection_as_json(collection_name):
    """
    List all entries in the specified collection database as JSON.
    """
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../rc001/{collection_name}.db'))

    if not os.path.exists(db_path):
        return jsonify({
            "status": "error",
            "message": f"Collection '{collection_name}' not found."
        }), 404

    collection_data = []

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM items')
            columns = [column[0] for column in cursor.description]
            results = cursor.fetchall()
            for row in results:
                collection_data.append(dict(zip(columns, row)))

        return jsonify({
            "status": "success",
            "collection": collection_data
        })
    except sqlite3.Error as e:
        return jsonify({
            "status": "error",
            "message": f"SQLite error: {e}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@rc001_bp.route('/api/v1/rc001/validate/<inscription_id>', methods=['GET'])
def validate_inscription(inscription_id):
    """
    Validate an inscription_id across all collections and return its index, deploy_address, inscription_address, and collection name.
    """
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../rc001'))
    conf_files = [f for f in os.listdir(conf_dir) if f.endswith('.conf')]

    try:
        for conf_file in conf_files:
            collection_name = conf_file.replace('.conf', '')
            db_file = os.path.join(conf_dir, f"{collection_name}.db")

            if not os.path.exists(db_file):
                continue

            # Read the configuration file to get the deploy_address, deploy_txid, and parent_inscription_id
            config = configparser.ConfigParser()
            config.read(os.path.join(conf_dir, conf_file))
            deploy_address = config['DEFAULT'].get('deploy_address')
            deploy_txid = config['DEFAULT'].get('deploy_txid')
            parent_inscription_id = config['DEFAULT'].get('parent_inscription_id')

            with sqlite3.connect(db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT inscription_id, inscription_address FROM items ORDER BY rowid')
                results = cursor.fetchall()

                for index, (db_inscription_id, inscription_address) in enumerate(results, start=1):
                    if db_inscription_id == inscription_id:
                        return jsonify({
                            "status": "success",
                            "collection_name": collection_name,
                            "number": index,
                            "deploy_address": deploy_address,
                            "deploy_txid": deploy_txid,
                            "parent_inscription_id": parent_inscription_id,
                            "inscription_address": inscription_address
                        })

        return jsonify({
            "status": "error",
            "message": f"Inscription ID '{inscription_id}' not found in any collection."
        }), 404

    except sqlite3.Error as e:
        return jsonify({
            "status": "error",
            "message": f"SQLite error: {e}"
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@rc001_bp.route('/api/v1/rc001/mint_hex/<collection_name>', methods=['GET'])
def generate_hex(collection_name):
    """
    Generate a hex representation of an HTML page with a unique SN for a specific collection.
    """
    conf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../rc001'))
    conf_file = f"{collection_name}.conf"
    db_file = os.path.join(conf_dir, conf_file.replace('.conf', '.db'))

    try:
        # Read the configuration file
        file_path = os.path.join(conf_dir, conf_file)
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": f"Configuration file not found: {conf_file}"
            }), 404

        config = configparser.ConfigParser()
        config.read(file_path)
        collection_data = {key: value for key, value in config['DEFAULT'].items()}

        # Parse SN ranges from the configuration file
        sn_ranges = []
        for key, value in collection_data.items():
            if key.startswith('sn_index_'):
                start, end = map(int, value.split('-'))
                sn_ranges.append((start, end))

        # Generate a random SN without checking the database
        sn_parts = [f"{random.randint(start, end):02}" for start, end in sn_ranges]
        sn = ''.join(sn_parts)

        # Initialize the database if it doesn't exist
        if not os.path.exists(db_file):
            with sqlite3.connect(db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sn TEXT NOT NULL,
                        inscription_status TIMESTAMP
                    )
                """)
                conn.commit()

        # Construct the HTML content
        html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="p" content="rc001"><meta name="op" content="mint"><meta name="sn" content="{sn}"><title>{collection_name}</title></head><body><script src="/content/{collection_data.get('parent_inscription_id')}"></script></body></html>"""

        # Convert HTML content directly to hex
        hex_content = html_content.encode('utf-8').hex()

        return jsonify({
            "status": "success",
            "hex": hex_content
        })

    except FileNotFoundError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
