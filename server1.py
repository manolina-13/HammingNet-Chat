import socket
import threading
import random
from termcolor import cprint, colored
import colorama
import traceback
import math # For custom_hamming_encode_whole_message calculation

# Initialize colorama
colorama.init(autoreset=True)

# <<< PASTE THE New Custom Hamming Utility Functions HERE >>>
# --- Custom Whole-Message Hamming-like Utilities ---

def _text_to_binary_string(text):
    """Converts a text string to a continuous binary string (8-bit ASCII)."""
    return ''.join(format(ord(char), '08b') for char in text)

def _binary_string_to_text(binary_str):
    """Converts a continuous binary string (ASCII) back to text."""
    text = ""
    if not binary_str: return ""
    effective_length = len(binary_str) - (len(binary_str) % 8)
    for i in range(0, effective_length, 8):
        byte = binary_str[i:i+8]
        try:
            text += chr(int(byte, 2))
        except ValueError:
            text += '?' # Placeholder for unreadable char
    return text

def calculate_required_redundant_bits(k_data_bits):
    """Calculates the number of redundant bits (r) needed for k data bits."""
    if k_data_bits == 0: return 0 # No data, no redundant bits
    r = 0
    while True:
        r += 1
        if (2**r) >= (k_data_bits + r + 1):
            return r

def custom_hamming_encode_whole_message(data_binary_string):
    """
    Encodes an entire data binary string using a custom Hamming-like scheme.
    """
    if not data_binary_string:
        return "", 0 # Return encoded string and k
    
    k = len(data_binary_string)
    r = calculate_required_redundant_bits(k)
    n = k + r

    codeword_array = ['0'] * n 
    data_idx = 0
    
    # Place data bits
    for i in range(n):
        pos = i + 1 
        if not ((pos & (pos - 1)) == 0 and pos != 0): # If not a power of 2
            if data_idx < k:
                codeword_array[i] = data_binary_string[data_idx]
                data_idx += 1
            # Else: position for data bit, but no more data_binary_string (should not happen if k is correct)

    # Calculate and place parity bits
    for i in range(r): # For P1, P2, P4, P8... (r times)
        parity_pos_1_indexed = 2**i
        p_idx_in_array = parity_pos_1_indexed - 1
        
        xor_sum = 0
        for bit_idx_in_array in range(n):
            bit_pos_1_indexed_check = bit_idx_in_array + 1
            if bit_pos_1_indexed_check == parity_pos_1_indexed: # Skip the parity bit itself for its own initial sum
                continue
            if (bit_pos_1_indexed_check & parity_pos_1_indexed) != 0: # If this bit is checked by this parity bit
                xor_sum ^= int(codeword_array[bit_idx_in_array])
        codeword_array[p_idx_in_array] = str(xor_sum)
        
    return "".join(codeword_array), k


def custom_hamming_decode_whole_message(received_codeword_string, original_k_data_bits, correct_errors=True):
    """
    Decodes a received codeword string from the custom Hamming-like scheme.
    Returns the extracted data binary string.
    """
    if not received_codeword_string or original_k_data_bits == 0:
        return ""

    k = original_k_data_bits
    r = calculate_required_redundant_bits(k)
    n = k + r

    if len(received_codeword_string) != n:
        cprint(f"[CUSTOM DECODE WARNING] Expected codeword length {n} (for k={k}), got {len(received_codeword_string)}. Attempting to process.", 'yellow')
        # Adjust received string to expected length n - This is risky but for demo purposes.
        if len(received_codeword_string) > n:
            received_codeword_string = received_codeword_string[:n]
        else: # Too short
            received_codeword_string = received_codeword_string.ljust(n, '0')

    codeword_list = list(received_codeword_string) # Work with a mutable list
    
    syndrome_val = 0
    for i in range(r): # For P1, P2, P4...
        parity_pos_1_indexed = 2**i
        p_idx_in_array = parity_pos_1_indexed -1

        xor_sum = 0
        for bit_idx_in_array in range(n):
            bit_pos_1_indexed_check = bit_idx_in_array + 1
            if (bit_pos_1_indexed_check & parity_pos_1_indexed) != 0: # If this bit is checked by this parity bit
                xor_sum ^= int(codeword_list[bit_idx_in_array])
        
        if xor_sum != 0: # This parity check contributes its position to the syndrome
            syndrome_val += parity_pos_1_indexed
            
    if syndrome_val != 0 and correct_errors:
        error_pos_0_indexed = syndrome_val - 1
        if 0 <= error_pos_0_indexed < n:
            codeword_list[error_pos_0_indexed] = '1' if codeword_list[error_pos_0_indexed] == '0' else '0'
        else:
            cprint(f"[CUSTOM DECODE WARNING] Syndrome {syndrome_val} points outside codeword. Multiple errors likely.", 'yellow')

    data_binary_list = []
    data_bits_extracted_count = 0
    for i in range(n):
        pos = i + 1
        if not ((pos & (pos - 1)) == 0 and pos != 0): # If not a power of 2 (data bit position)
            if data_bits_extracted_count < k:
                 data_binary_list.append(codeword_list[i])
                 data_bits_extracted_count +=1
            if data_bits_extracted_count == k: # Optimization: stop once all k bits are found
                break
                
    return "".join(data_binary_list)

# --- End of Custom Whole-Message Hamming-like Utilities ---


HOST = '0.0.0.0'
PORT = 12345
# ... (rest of server setup: MAX_CLIENTS, BUFFER_SIZE, clients, clients_lock) ...
# (Same as previous version)
MAX_CLIENTS = 10
BUFFER_SIZE = 2048 # Increased buffer for potentially larger encoded strings

clients = {}
clients_lock = threading.Lock()


def flip_one_random_bit(binary_string): # Same as before
    if not binary_string: return "", -1
    s_list = list(binary_string)
    index_to_flip = random.randint(0, len(s_list) - 1)
    s_list[index_to_flip] = '1' if s_list[index_to_flip] == '0' else '0'
    return "".join(s_list), index_to_flip

def broadcast(message_content, sender_conn=None): # Same as before
    with clients_lock:
        for client_conn, username in clients.items():
            if client_conn != sender_conn:
                try: client_conn.sendall(message_content.encode('utf-8'))
                except socket.error: cprint(f"Error sending to {username}.", 'red')

def send_private_message(target_username, message_content_with_k, sender_username): # Modified to expect k
    with clients_lock:
        target_conn = next((conn for conn, uname in clients.items() if uname == target_username), None)
        if target_conn:
            try:
                # message_content_with_k is already "k_val data_string"
                full_message = f"[PM from {sender_username}]: /h {message_content_with_k}"
                target_conn.sendall(full_message.encode('utf-8'))
                return True 
            except socket.error: cprint(f"Error sending PM to {target_username}.", 'red'); return False
        else:
            sender_conn = next((conn for conn, uname in clients.items() if uname == sender_username), None)
            if sender_conn:
                try: sender_conn.sendall(f"[SERVER]: User '{colored(target_username, 'yellow')}' not found.".encode('utf-8'))
                except: pass
            return False

def handle_client(conn, addr):
    cprint(f"[NEW CONNECTION] {addr} connected.", 'cyan')
    username = None
    try:
        # ... (Username handling same as before) ...
        conn.sendall("Welcome! Please enter your username: ".encode('utf-8'))
        username_candidate = conn.recv(BUFFER_SIZE).decode('utf-8').strip()
        with clients_lock:
            while not username_candidate or username_candidate in clients.values():
                prompt_msg = ""
                if not username_candidate: prompt_msg = "Username cannot be empty. Choose another: "
                else: prompt_msg = f"Username '{colored(username_candidate, 'yellow')}' is taken. Choose another: "
                conn.sendall(prompt_msg.encode('utf-8'))
                username_candidate = conn.recv(BUFFER_SIZE).decode('utf-8').strip()
                if not username_candidate: raise ConnectionResetError("Client disconnected during username selection")
            username = username_candidate
            clients[conn] = username

        cprint(f"[USERNAME SET] {addr} is now {colored(username, 'yellow')}.", 'cyan')
        conn.sendall(f"Welcome, {colored(username, 'yellow')}! Messages use whole-message custom Hamming.\nType '/list', '/pm <user> <msg>', or '/quit'.\n".encode('utf-8'))
        broadcast(f"[SERVER] {colored(username, 'yellow')} has joined the chat.", conn)


        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data: break
            message = data.decode('utf-8').strip()
            print(f"[{colored(username, 'yellow')}] raw recv: {colored(message[:150] + ('...' if len(message)>150 else ''), 'light_grey')}")

            if message.lower() == '/quit': break
            elif message.lower() == '/list':
                with clients_lock: user_list = ", ".join([colored(u, 'yellow') for u in clients.values()])
                conn.sendall(f"[SERVER] Connected users: {user_list}\n".encode('utf-8'))
            
            elif message.startswith('/m ') or message.startswith('/pm '): # Client sends: /m k_val encoded_data OR /pm user k_val encoded_data
                is_pm = message.startswith('/pm ')
                
                parts = message.split(' ', 3 if is_pm else 2)
                target_user = ""
                original_k_val_str = ""
                original_encoded_data = ""

                if is_pm:
                    if len(parts) < 4: 
                        conn.sendall("[SERVER] Invalid PM format. Expected /pm <user> <k_val> <data>\n".encode('utf-8')); continue
                    target_user = parts[1]
                    original_k_val_str = parts[2]
                    original_encoded_data = parts[3]
                    if target_user == username: 
                        conn.sendall("[SERVER] You can't PM yourself.\n".encode('utf-8')); continue
                else: # Group message /m
                    if len(parts) < 3:
                         conn.sendall("[SERVER] Invalid group message format. Expected /m <k_val> <data>\n".encode('utf-8')); continue
                    original_k_val_str = parts[1]
                    original_encoded_data = parts[2]
                
                try:
                    original_k_val = int(original_k_val_str)
                except ValueError:
                    conn.sendall("[SERVER] Invalid k_val (original data bit length).\n".encode('utf-8')); continue

                if not original_encoded_data:
                    cprint(f"[{colored(username, 'yellow')}] sent empty encoded message.", 'magenta')
                    conn.sendall("[SERVER] Empty encoded message ignored.\n".encode('utf-8')); continue

                # Server flips one bit in the *encoded_data*
                modified_encoded_data, flipped_idx = flip_one_random_bit(original_encoded_data)
                
                log_prefix = f"PM from {colored(username, 'yellow')} to {colored(target_user, 'yellow')}:" if is_pm else f"Group msg from {colored(username, 'yellow')}:"
                cprint(log_prefix, 'magenta')
                cprint(f"  Received k={original_k_val}, Encoded Len={len(original_encoded_data)}", 'magenta')
                if flipped_idx != -1:
                    cprint(f"  Flipped bit at index {flipped_idx} of the encoded data.", 'yellow')
                    # Slice display for context
                    slice_start = max(0, flipped_idx - 10)
                    slice_end_orig = min(len(original_encoded_data), flipped_idx + 11)
                    slice_end_mod = min(len(modified_encoded_data), flipped_idx + 11)

                    before_display = original_encoded_data[slice_start:flipped_idx] + \
                                     colored(original_encoded_data[flipped_idx], 'yellow', attrs=['underline','bold']) + \
                                     original_encoded_data[flipped_idx+1:slice_end_orig]
                    after_display = modified_encoded_data[slice_start:flipped_idx] + \
                                    colored(modified_encoded_data[flipped_idx], 'red', attrs=['underline','bold']) + \
                                    modified_encoded_data[flipped_idx+1:slice_end_mod]
                    print(f"  Original around flip: ...{before_display}...")
                    print(f"  Flipped  around flip: ...{after_display}...")
                else:
                    print(f"  (No bit flip or empty data)")

                # Server relays: /h k_val modified_encoded_data
                payload_for_transmission = f"{original_k_val} {modified_encoded_data}" # k first, then data

                if is_pm:
                    pm_sent_success = send_private_message(target_user, payload_for_transmission, username)
                    if pm_sent_success:
                        try: conn.sendall(f"[PM to {target_user}]: /h {payload_for_transmission}\n".encode('utf-8'))
                        except: pass
                else: # Group message
                    broadcast_payload = f"[{username}]: /h {payload_for_transmission}"
                    broadcast(broadcast_payload, conn)
            else:
                conn.sendall(f"[SERVER] Unknown command: {message}\n".encode('utf-8'))

    # ... (Error handling and finally block same as before) ...
    except ConnectionResetError: cprint(f"[CONNECTION RESET] {addr} ({colored(username, 'yellow') if username else 'Unknown'}) disconnected.", 'red')
    except socket.error as e: cprint(f"[SOCKET ERROR] {addr} ({colored(username, 'yellow') if username else 'Unknown'}): {e}", 'red')
    except Exception as e:
        cprint(f"[ERROR] Unexpected error with client {addr} ({colored(username, 'yellow') if username else 'Unknown'}): {str(e)}", 'red', attrs=['bold'])
        traceback.print_exc()
    finally:
        with clients_lock:
            if conn in clients: del clients[conn]
        if username:
            broadcast(f"[SERVER] {colored(username, 'yellow')} has left the chat.")
            cprint(f"[DISCONNECTED] {addr} ({colored(username, 'yellow')}) disconnected.", 'cyan')
        else:
            cprint(f"[DISCONNECTED] {addr} (no username) disconnected.", 'cyan')
        conn.close()

def start_server(): # Same as before
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: server_socket.bind((HOST, PORT))
    except socket.error as e: cprint(f"Bind failed: {e}", 'red', attrs=['bold']); return
    server_socket.listen(MAX_CLIENTS)
    cprint(f"[LISTENING] Server on {HOST}:{PORT}", 'green', attrs=['bold'])
    try:
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt: cprint("\n[SHUTTING DOWN]", 'yellow', attrs=['bold'])
    finally:
        cprint("[INFO] Closing client connections...", 'yellow')
        with clients_lock:
            for client_conn in list(clients.keys()):
                try: client_conn.sendall("[SERVER] Server down.".encode('utf-8')); client_conn.close()
                except: pass
        server_socket.close()
        cprint("[SERVER SHUTDOWN COMPLETE]", 'green')

if __name__ == "__main__":
    start_server()