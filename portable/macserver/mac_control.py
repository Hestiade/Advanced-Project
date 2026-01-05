#!/usr/bin/env python3
"""
MBP Control Panel - Battery & Ollama Monitor
Run this on your MacBook Pro to expose system status to the mail agent dashboard.
"""

import subprocess
import json
import re
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# Configuration
API_PORT = 11435  # Different from Ollama's 11434
OLLAMA_PORT = 11434


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP handler for status API."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/status' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            status = get_system_status()
            self.wfile.write(json.dumps(status).encode())
        
        elif self.path == '/battery':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            battery = get_battery_status()
            self.wfile.write(json.dumps(battery).encode())
        
        elif self.path == '/ollama':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            ollama = get_ollama_status()
            self.wfile.write(json.dumps(ollama).encode())
        
        elif self.path == '/temperature':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            temp = get_temperature()
            self.wfile.write(json.dumps(temp).encode())
        
        elif self.path == '/memory':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            memory = get_memory_usage()
            self.wfile.write(json.dumps(memory).encode())
        
        else:
            self.send_response(404)
            self.end_headers()


def get_battery_status() -> dict:
    """Get MacBook battery status using pmset."""
    try:
        result = subprocess.run(
            ['pmset', '-g', 'batt'],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout
        
        # Parse battery percentage
        match = re.search(r'(\d+)%', output)
        percentage = int(match.group(1)) if match else None
        
        # Parse charging status
        if 'AC Power' in output:
            charging = 'charging' if 'charging' in output.lower() else 'plugged_in'
        else:
            charging = 'discharging'
        
        # Parse time remaining
        time_match = re.search(r'(\d+:\d+) remaining', output)
        time_remaining = time_match.group(1) if time_match else None
        
        return {
            'percentage': percentage,
            'status': charging,
            'time_remaining': time_remaining,
            'raw': output.strip()
        }
    except Exception as e:
        return {'error': str(e)}


def get_temperature() -> dict:
    """Get Mac CPU/GPU temperature using powermetrics or osx-cpu-temp."""
    try:
        # Try osx-cpu-temp first (if installed via brew)
        result = subprocess.run(
            ['osx-cpu-temp'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse output like "55.0°C"
            temp_str = result.stdout.strip()
            match = re.search(r'([\d.]+)', temp_str)
            if match:
                return {
                    'cpu_temp': float(match.group(1)),
                    'unit': 'C',
                    'source': 'osx-cpu-temp'
                }
    except FileNotFoundError:
        pass
    except Exception:
        pass
    
    try:
        # Fallback: use powermetrics (requires sudo)
        # This reads thermal sensor data
        result = subprocess.run(
            ['sudo', 'powermetrics', '-n', '1', '-i', '100', '--samplers', 'smc'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse CPU die temperature
            match = re.search(r'CPU die temperature:\s*([\d.]+)', result.stdout)
            if match:
                return {
                    'cpu_temp': float(match.group(1)),
                    'unit': 'C',
                    'source': 'powermetrics'
                }
    except Exception:
        pass
    
    return {'error': 'Could not read temperature. Try: brew install osx-cpu-temp'}


def get_memory_usage() -> dict:
    """Get Mac RAM usage using vm_stat."""
    try:
        result = subprocess.run(
            ['vm_stat'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse vm_stat output
            stats = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    # Remove periods and convert to int
                    val = val.strip().rstrip('.')
                    try:
                        stats[key.strip()] = int(val)
                    except ValueError:
                        pass
            
            # Page size is typically 16384 bytes on Apple Silicon, 4096 on Intel
            page_size = 16384  # Default for Apple Silicon
            
            # Calculate memory in GB
            pages_free = stats.get('Pages free', 0)
            pages_active = stats.get('Pages active', 0)
            pages_inactive = stats.get('Pages inactive', 0)
            pages_wired = stats.get('Pages wired down', 0)
            pages_compressed = stats.get('Pages occupied by compressor', 0)
            
            used_pages = pages_active + pages_wired + pages_compressed
            total_pages = used_pages + pages_free + pages_inactive
            
            used_gb = (used_pages * page_size) / (1024**3)
            total_gb = (total_pages * page_size) / (1024**3)
            
            # Get actual total from sysctl
            try:
                mem_result = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True, timeout=2)
                if mem_result.returncode == 0:
                    total_gb = int(mem_result.stdout.strip()) / (1024**3)
            except:
                pass
            
            return {
                'used_gb': round(used_gb, 1),
                'total_gb': round(total_gb, 1),
                'percent': round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0
            }
    except Exception as e:
        pass
    
    return {'error': 'Could not read memory usage'}


def get_ollama_status() -> dict:
    """Check if Ollama is running and get loaded models."""
    try:
        # Check if Ollama process is running
        result = subprocess.run(
            ['pgrep', '-x', 'ollama'],
            capture_output=True,
            text=True
        )
        running = result.returncode == 0
        
        if not running:
            return {'running': False, 'models': []}
        
        # Try to get models from API
        import urllib.request
        try:
            with urllib.request.urlopen(f'http://localhost:{OLLAMA_PORT}/api/tags', timeout=2) as response:
                data = json.loads(response.read().decode())
                models = [m['name'] for m in data.get('models', [])]
                return {'running': True, 'models': models}
        except:
            return {'running': True, 'models': []}
            
    except Exception as e:
        return {'error': str(e)}


def get_system_status() -> dict:
    """Get combined system status."""
    return {
        'hostname': os.uname().nodename,
        'battery': get_battery_status(),
        'ollama': get_ollama_status(),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }


def start_api_server():
    """Start the status API server in background."""
    server = HTTPServer(('0.0.0.0', API_PORT), StatusHandler)
    print(f"  API server running on http://0.0.0.0:{API_PORT}")
    print(f"  Endpoints: /status, /battery, /ollama")
    server.serve_forever()


def start_ollama():
    """Start Ollama serve."""
    print("Starting Ollama...")
    subprocess.Popen(
        ['ollama', 'serve'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    if get_ollama_status().get('running'):
        print("✓ Ollama started")
    else:
        print("✗ Failed to start Ollama")


def stop_ollama():
    """Stop Ollama."""
    print("Stopping Ollama...")
    subprocess.run(['pkill', '-x', 'ollama'], capture_output=True)
    time.sleep(1)
    print("✓ Ollama stopped")


def get_ssh_info() -> tuple:
    """Get SSH connection info (user, hostname, IP)."""
    import socket
    user = os.environ.get('USER', 'unknown')
    hostname = socket.gethostname()
    try:
        # Get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = "unknown"
    return user, hostname, ip


def show_menu():
    """Display interactive menu."""
    os.system('clear')
    
    # Get SSH info
    ssh_user, ssh_host, ssh_ip = get_ssh_info()
    
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          MBP Control Panel - Ollama & Battery           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  SSH: {ssh_user}@{ssh_host} ({ssh_ip})")
    print()
    
    # Show current status
    battery = get_battery_status()
    ollama = get_ollama_status()
    
    print("━━━ Current Status ━━━")
    if battery.get('percentage') is not None:
        icon = "🔋" if battery['status'] == 'discharging' else "⚡"
        print(f"  {icon} Battery: {battery['percentage']}% ({battery['status']})")
        if battery.get('time_remaining'):
            print(f"     Time remaining: {battery['time_remaining']}")
    
    if ollama.get('running'):
        models = ", ".join(ollama.get('models', [])) or "none loaded"
        print(f"  🟢 Ollama: Running (Models: {models})")
    else:
        print(f"  🔴 Ollama: Stopped")
    
    print()
    print("━━━ Actions ━━━")
    print("  1) Start Ollama")
    print("  2) Stop Ollama")
    print("  3) Restart Ollama")
    print("  4) Start API server (foreground)")
    print("  5) Start API server (background)")
    print("  6) Refresh status")
    print()
    print("  0) Exit")
    print()
    print("══════════════════════════════════════════════════════════")


def main():
    """Main control loop."""
    while True:
        show_menu()
        choice = input("Enter choice [0-6]: ").strip()
        
        if choice == '1':
            start_ollama()
            input("\nPress Enter to continue...")
        elif choice == '2':
            stop_ollama()
            input("\nPress Enter to continue...")
        elif choice == '3':
            stop_ollama()
            time.sleep(1)
            start_ollama()
            input("\nPress Enter to continue...")
        elif choice == '4':
            print("\nStarting API server (Ctrl+C to stop)...")
            try:
                start_api_server()
            except KeyboardInterrupt:
                print("\nAPI server stopped.")
        elif choice == '5':
            print("\nStarting API server in background...")
            thread = threading.Thread(target=start_api_server, daemon=True)
            thread.start()
            print("API server started in background.")
            input("\nPress Enter to continue...")
        elif choice == '6':
            continue  # Just refresh
        elif choice == '0':
            print("Goodbye!")
            break
        else:
            input("Invalid choice. Press Enter to continue...")


if __name__ == '__main__':
    # If run with --serve, start API server directly
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--serve':
        print("MBP Status API Server")
        print("=" * 40)
        
        # Start caffeinate to prevent sleep
        caffeinate_proc = subprocess.Popen(
            ['caffeinate', '-dims'],  # -d display, -i idle, -m disk, -s system
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("☕ Caffeinate started (preventing sleep)")
        
        try:
            start_api_server()
        finally:
            caffeinate_proc.terminate()
            print("☕ Caffeinate stopped")
    else:
        main()
