[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# HammingNet-Chat: Multi-threaded Reliable Chat System

A Python-based chat application implementing a Client-Server architecture over TCP sockets. This project incorporates a custom Whole-Message Hamming Code layer to provide Forward Error Correction (FEC), ensuring message integrity even in high-noise network environments.

## Overview
While standard chat applications rely on TCP's built-in error detection at the transport layer, this project implements a layer of resilience at the application level. The server is designed to simulate network interference by intentionally flipping bits in the encoded bitstream. The client-side decoder identifies the syndrome, locates the error, and performs a bit-flip correction before displaying the message to the user.

## Features
- **Real-time Forward Error Correction:** Repairs single-bit corrupted data using Hamming (n, k) logic.
- **Full-Duplex Messaging:** Utilizes the Python `threading` module for concurrent message handling.
- **Bit-Level Debugging:** Displays raw received bitstreams, original data length (k), and encoded length (n).
- **Syndrome Analysis:** Visualizes the exact index where an error was detected and corrected.
- **Protocol Support:** Includes broadcast (/m) and private messaging (/pm) capabilities.
- **Dynamic UI:** Rich terminal interface using colorama and termcolor to distinguish between system logs, outgoing, and incoming messages.

## Technical Demonstration

![Chat Application Demonstration](screenshot.png)

### Screenshot Analysis
1. **Decoder Logic:** The top-left terminal shows the server-side log where bits are flipped (e.g., Index 7). It displays the bit transition from 0 to 1.
2. **Real-time Correction:** In the client terminals, corrupted strings are corrected automatically. For example, the corrupted reception `[-y]` is successfully restored to its intended value `[my]`.
3. **Data Transparency:** The logs show the $k$ (data bits) and $n$ (total bits) values, allowing for the verification of the redundancy calculation.

## Technical Architecture

### 1. Hamming Code Implementation
The system calculates the necessary redundancy bits ($r$) for any input message length ($k$) based on the parity bit theorem:
`2^r >= k + r + 1`

- **Parity Insertion:** Redundancy bits are calculated and inserted at positions that are powers of two ($1, 2, 4, 8 \dots$).
- **Syndrome Calculation:** Upon reception, the client re-evaluates the parity bits. If the resulting syndrome is non-zero, the value represents the exact 1-based index of the error.

### 2. Messaging Protocol
Data is encapsulated in a custom string format to assist the decoder:
`[Sender]: /h <original_k_length> <encoded_bitstream>`

## Installation and Usage

### Prerequisites
The following Python libraries are required for the terminal UI:
```bash
pip install colorama termcolor
```

### Execution
1. **Start the Server:**
   ```bash
   python server1.py
   ```
2. **Start Clients (Run in separate terminal windows):**
   ```bash
   python client1.py
   ```

## Command Reference

| Command | Description |
| :--- | :--- |
| `/list` | Displays a list of all currently connected users. |
| `/m <message>` | Broadcasts an error-corrected message to all users. |
| `/pm <user> <message>` | Sends a private error-corrected message to a specific user. |
| `/quit` | Terminates the connection and closes the socket. |

## License

This project is distributed under the MIT License. See `LICENSE` for more information.

## Contact

Manolina Das - [GitHub Profile](https://github.com/manolina-13)
