import socket
import threading
import sys
from termcolor import cprint, colored
import colorama
import traceback
import math 

# Initialize colorama
colorama.init(autoreset=True)

# --- Custom Whole-Message Hamming-like Utilities --- (Assumed to be your latest version)
def _text_to_binary_string(text):
    return ''.join(format(ord(char), '08b') for char in text)
def _binary_string_to_text(binary_str):
    text = ""
    if not binary_str: return ""
    effective_length = len(binary_str) - (len(binary_str) % 8)
    for i in range(0, effective_length, 8):
        byte = binary_str[i:i+8]
        try:
            text += chr(int(byte, 2))
        except ValueError: text += '?'
    return text
def calculate_required_redundant_bits(k_data_bits):
    if k_data_bits == 0: return 0
    r = 0
    while True:
        r += 1
        if (2**r) >= (k_data_bits + r + 1): return r
def custom_hamming_encode_whole_message(data_binary_string):
    if not data_binary_string: return "", 0 
    k = len(data_binary_string)
    r = calculate_required_redundant_bits(k)
    n = k + r
    codeword_array = ['0'] * n 
    data_idx = 0
    for i in range(n):
        pos = i + 1 
        if not ((pos & (pos - 1)) == 0 and pos != 0): 
            if data_idx < k:
                codeword_array[i] = data_binary_string[data_idx]
                data_idx += 1
    for i in range(r):
        parity_pos_1_indexed = 2**i
        p_idx_in_array = parity_pos_1_indexed - 1
        xor_sum = 0
        for bit_idx_in_array in range(n):
            bit_pos_1_indexed_check = bit_idx_in_array + 1
            if bit_pos_1_indexed_check == parity_pos_1_indexed: continue
            if (bit_pos_1_indexed_check & parity_pos_1_indexed) != 0:
                xor_sum ^= int(codeword_array[bit_idx_in_array])
        codeword_array[p_idx_in_array] = str(xor_sum)
    return "".join(codeword_array), k
def custom_hamming_decode_whole_message(received_codeword_string, original_k_data_bits, correct_errors=True):
    if not received_codeword_string or original_k_data_bits == 0: return ""
    k = original_k_data_bits
    r = calculate_required_redundant_bits(k)
    n = k + r
    if len(received_codeword_string) != n:
        # This cprint is the one you are seeing
        cprint(f"[CUSTOM DECODE WARNING] Client: Expected codeword length {n} (for k={k}), got {len(received_codeword_string)}. Output may be incorrect.", 'yellow')
        if len(received_codeword_string) > n: received_codeword_string = received_codeword_string[:n]
        else: received_codeword_string = received_codeword_string.ljust(n, '0')
    codeword_list = list(received_codeword_string)
    syndrome_val = 0
    for i in range(r):
        parity_pos_1_indexed = 2**i
        xor_sum = 0
        for bit_idx_in_array in range(n):
            bit_pos_1_indexed_check = bit_idx_in_array + 1
            if (bit_pos_1_indexed_check & parity_pos_1_indexed) != 0:
                xor_sum ^= int(codeword_list[bit_idx_in_array])
        if xor_sum != 0: syndrome_val += parity_pos_1_indexed
    if syndrome_val != 0 and correct_errors:
        error_pos_0_indexed = syndrome_val - 1
        if 0 <= error_pos_0_indexed < n:
            codeword_list[error_pos_0_indexed] = '1' if codeword_list[error_pos_0_indexed] == '0' else '0'
        else: cprint(f"[CUSTOM DECODE WARNING] Client: Syndrome {syndrome_val} points outside codeword. Multiple errors likely.", 'yellow')
    data_binary_list = []
    data_bits_extracted_count = 0
    for i in range(n):
        pos = i + 1
        if not ((pos & (pos - 1)) == 0 and pos != 0):
            if data_bits_extracted_count < k:
                 data_binary_list.append(codeword_list[i])
                 data_bits_extracted_count +=1
            if data_bits_extracted_count == k: break
    return "".join(data_binary_list)
# --- End of Custom Whole-Message Hamming-like Utilities ---

HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 2048 
stop_threads = False
PROMPT = colored("You: ", 'blue', attrs=['bold'])

def clear_current_line():
    sys.stdout.write('\r' + ' ' * (int(0.9 * (getattr(sys.stdout, 'columns', 80)))) + '\r')
def reprint_prompt():
    sys.stdout.write(PROMPT); sys.stdout.flush()

def receive_messages(sock):
    global stop_threads
    while not stop_threads:
        try:
            raw_message_from_socket = sock.recv(BUFFER_SIZE).decode('utf-8') 
            if not raw_message_from_socket:
                clear_current_line(); cprint("[CONNECTION] Server closed.", 'yellow'); stop_threads = True; break
            
            message = raw_message_from_socket.strip() # Strip the *entire message first*

            clear_current_line()
            display_message = ""

            if message.startswith("[SERVER]"):
                display_message = colored(message, 'cyan')
            elif ": /h " in message:
                prefix_and_body = message.split(": /h ", 1)
                sender_prefix_raw = prefix_and_body[0]
                
                if len(prefix_and_body) < 2: 
                    display_message = f"{colored(sender_prefix_raw, 'blue')}: {colored('[Error: Malformed /h (empty content)]', 'red')}"
                else:
                    content_after_h = prefix_and_body[1] # Already stripped because 'message' was stripped
                    parts_after_h = content_after_h.split(' ', 1)
                    
                    if len(parts_after_h) < 2:
                        display_message = f"{colored(sender_prefix_raw, 'blue')}: {colored('[Error: Incomplete Hamming data (missing k or data after /h)]', 'red')}"
                    else:
                        k_val_str, modified_encoded_data = parts_after_h
                        
                        # >>>>> CRUCIAL DEBUG PRINT <<<<<
                        print(f"\nCLIENT RECV DECODE INPUT: original_k='{k_val_str}', data_len={len(modified_encoded_data)}, data_repr='{repr(modified_encoded_data)}'")

                        try:
                            original_k = int(k_val_str)
                        except ValueError:
                            display_message = f"{colored(sender_prefix_raw, 'blue')}: {colored('[Error: Invalid k_val from server]', 'red')}"
                        else:
                            sender_display_name = "" 
                            if sender_prefix_raw.startswith("[") and sender_prefix_raw.endswith("]"):
                                actual_username = sender_prefix_raw[1:-1]
                                sender_display_name = f"[{colored(actual_username, 'blue', attrs=['bold'])}]:"
                            else: sender_display_name = colored(sender_prefix_raw, 'blue') + ":"
                            if sender_prefix_raw.startswith("[PM from "):
                                pm_sender_name = sender_prefix_raw[len("[PM from "):-1]
                                sender_display_name = f"[{colored('PM from', 'magenta')} {colored(pm_sender_name, 'yellow', attrs=['bold'])}]:"
                            elif sender_prefix_raw.startswith("[PM to "):
                                target_user_name = sender_prefix_raw[len("[PM to "):-1]
                                sender_display_name = f"[{colored('PM to', 'light_magenta')} {colored(target_user_name, 'yellow')}]:"

                            if not modified_encoded_data:
                                display_message = f"{sender_display_name} {colored('[Error: Empty Encoded Data]', 'red')}"
                            else:
                                try:
                                    corrupted_binary = custom_hamming_decode_whole_message(modified_encoded_data, original_k, correct_errors=False)
                                    corrected_binary = custom_hamming_decode_whole_message(modified_encoded_data, original_k, correct_errors=True)
                                    corrupted_text = _binary_string_to_text(corrupted_binary)
                                    corrected_text = _binary_string_to_text(corrected_binary)
                                    display_message = f"{sender_display_name} {colored('['+corrupted_text+']', 'light_red')} -> {colored('['+corrected_text+']', 'light_green')}"
                                except Exception as e_decode:
                                    display_message = f"{sender_display_name} {colored(f'[Decode Error: {e_decode}]', 'red')}"
            else:
                display_message = message 

            sys.stdout.write(display_message + "\n")
            reprint_prompt()

        except ConnectionResetError: clear_current_line(); cprint("[CONNECTION] Lost.", 'red'); stop_threads = True; break
        except socket.error as e:
            if not stop_threads: clear_current_line(); cprint(f"[ERROR] Recv socket: {e}", 'red')
            stop_threads = True; break
        except Exception as e:
            if not stop_threads:
                clear_current_line(); cprint(f"[ERROR] Recv general: {str(e)}", 'red', attrs=['bold'])
                traceback.print_exc()
            stop_threads = True; break

def send_messages(sock):
    global stop_threads
    while not stop_threads:
        try:
            user_typed_message = input(PROMPT)
            if stop_threads: break
            
            final_message_to_server = ""
            if not user_typed_message.strip(): continue

            if user_typed_message.lower() == '/quit':
                final_message_to_server = user_typed_message.lower()
            elif user_typed_message.lower() == '/list':
                final_message_to_server = user_typed_message.lower()
            else: 
                text_to_encode = ""
                target_user_for_pm = None
                if user_typed_message.startswith('/pm '):
                    parts = user_typed_message.split(' ', 2)
                    if len(parts) < 3 or not parts[2].strip():
                        clear_current_line(); cprint("[INFO] Usage: /pm <user> <message>", 'yellow'); reprint_prompt(); continue
                    target_user_for_pm = parts[1]
                    text_to_encode = parts[2]
                else: text_to_encode = user_typed_message
                original_data_binary = _text_to_binary_string(text_to_encode)
                if not original_data_binary:
                    clear_current_line(); cprint("[INFO] Cannot send empty message (no binary data).", 'yellow'); reprint_prompt(); continue
                
                encoded_string, original_k = custom_hamming_encode_whole_message(original_data_binary)
                
                # >>>>> SENDER CLIENT DEBUG PRINT <<<<<
                print(f"\nCLIENT SENDING: original_k={original_k}, encoded_len={len(encoded_string)}, encoded_repr='{repr(encoded_string)}'")

                if not encoded_string:
                    clear_current_line(); cprint("[INFO] Encoding resulted in empty string.", 'yellow'); reprint_prompt(); continue
                if target_user_for_pm:
                    final_message_to_server = f"/pm {target_user_for_pm} {original_k} {encoded_string}"
                else: final_message_to_server = f"/m {original_k} {encoded_string}"
            
            if final_message_to_server:
                sock.sendall(final_message_to_server.encode('utf-8'))
                if final_message_to_server.lower() == '/quit': stop_threads = True
        
        except EOFError: 
            cprint("\n[INFO] Input closed. Quitting...", 'yellow')
            if not stop_threads: 
                try: sock.sendall("/quit".encode('utf-8'))
                except (socket.error, OSError): pass
            stop_threads = True; break
        except KeyboardInterrupt:
            cprint("\n[INFO] Interrupt. Quitting...", 'yellow')
            if not stop_threads: 
                try: sock.sendall("/quit".encode('utf-8'))
                except (socket.error, OSError): pass
            stop_threads = True; break
        except socket.error as e:
            if not stop_threads: clear_current_line(); cprint(f"[ERROR] Send socket: {e}", 'red')
            stop_threads = True; break
        except Exception as e:
            if not stop_threads:
                clear_current_line(); cprint(f"[ERROR] Send general: {str(e)}", 'red', attrs=['bold'])
                traceback.print_exc()
            stop_threads = True; break

def main(): 
    global stop_threads
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receive_thread = None 
    try:
        client_socket.connect((HOST, PORT))
        cprint(f"[CONNECTION] Connected to {HOST}:{PORT}", 'green')
        while True:
            server_prompt = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            sys.stdout.write(server_prompt); sys.stdout.flush()
            username_input = input()
            client_socket.sendall(username_input.encode('utf-8'))
            response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            clear_current_line(); sys.stdout.write(response); sys.stdout.flush()
            if "Welcome," in response or "You are connected" in response: break
            if not ("taken" in response or "empty" in response or "Choose another" in response):
                cprint("Unexpected server response. Exiting.", 'red'); stop_threads = True; break
        if stop_threads: client_socket.close(); return
        
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
        receive_thread.start()
        send_messages(client_socket)
    except socket.error as e: cprint(f"[CONNECTION ERROR] {e}", 'red', attrs=['bold'])
    except Exception as e:
        cprint(f"[ERROR] Main client: {str(e)}", 'red', attrs=['bold']); traceback.print_exc()
    finally:
        stop_threads = True
        if receive_thread and receive_thread.is_alive(): 
            try: client_socket.shutdown(socket.SHUT_RDWR) 
            except (socket.error, OSError): pass 
            receive_thread.join(timeout=0.5)
        try: client_socket.close() 
        except (socket.error, OSError): pass 

if __name__ == "__main__":
    main()