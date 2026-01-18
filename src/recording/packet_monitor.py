"""
Packet Monitor for Drawback Chess Engine

Monitors network traffic to capture the critical end-of-game drawback reveal packet.
"""

import json
import time
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime

# Try to import packet monitoring libraries
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Some monitoring features disabled.")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not available. HTTP monitoring disabled.")


class PacketMonitor:
    """Monitors for drawback reveal packets in network traffic."""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.capture_callback: Optional[Callable] = None
        self.captured_packets = []
        
        # Known packet patterns to look for
        self.reveal_keywords = [
            'drawback',
            'game_over',
            'result',
            'reveal',
            'opponent',
            'white_drawback',
            'black_drawback'
        ]
        
        # Server endpoints that might send reveal data
        self.reveal_endpoints = [
            '/game/end',
            '/game/result',
            '/game/reveal',
            '/api/game/complete',
            '/match/finish'
        ]
    
    def set_capture_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback function for captured packets."""
        self.capture_callback = callback
    
    def start_monitoring(self):
        """Start monitoring for reveal packets."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print("Packet monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring for packets."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        print("Packet monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Try different monitoring methods
                self._monitor_http_traffic()
                self._monitor_process_activity()
                
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
            except Exception as e:
                print(f"Monitor loop error: {e}")
                time.sleep(1.0)
    
    def _monitor_http_traffic(self):
        """Monitor HTTP traffic for reveal packets."""
        if not REQUESTS_AVAILABLE:
            return
        
        # This is a placeholder - real implementation would use
        # packet capture libraries like scapy or mitmproxy
        pass
    
    def _monitor_process_activity(self):
        """Monitor process activity for game-related network calls."""
        if not PSUTIL_AVAILABLE:
            return
        
        # Look for browser or game client processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if self._is_game_client_process(proc):
                    # Monitor network connections for this process
                    self._monitor_process_connections(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    def _is_game_client_process(self, proc) -> bool:
        """Check if a process is likely the game client."""
        name = proc.info['name'].lower()
        cmdline = ' '.join(proc.info['cmdline'] or []).lower()
        
        game_indicators = [
            'chrome', 'firefox', 'edge', 'safari',  # Browsers
            'chess', 'drawback', 'lila', 'lichess'  # Chess clients
        ]
        
        return any(indicator in name or indicator in cmdline for indicator in game_indicators)
    
    def _monitor_process_connections(self, proc):
        """Monitor network connections for a specific process."""
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    # Check if this might be a game server connection
                    self._analyze_connection(conn)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    
    def _analyze_connection(self, connection):
        """Analyze a network connection for potential reveal packets."""
        # This is a placeholder - real implementation would
        # inspect the actual packet data
        pass
    
    def add_packet(self, packet_data: Dict[str, Any]):
        """Manually add a packet for analysis."""
        self.captured_packets.append({
            'timestamp': datetime.utcnow().isoformat(),
            'data': packet_data
        })
        
        # Check if this looks like a reveal packet
        if self._is_reveal_packet(packet_data):
            print(f"Potential reveal packet detected: {packet_data}")
            
            if self.capture_callback:
                self.capture_callback(packet_data)
    
    def _is_reveal_packet(self, packet_data: Dict[str, Any]) -> bool:
        """Check if packet data looks like a drawback reveal."""
        packet_str = json.dumps(packet_data).lower()
        
        # Check for reveal keywords
        keyword_matches = sum(1 for keyword in self.reveal_keywords if keyword in packet_str)
        
        # Check for drawback-related structure
        has_drawback_structure = (
            'drawback' in packet_str or
            any('drawback' in str(value).lower() for value in packet_data.values() if isinstance(value, (str, dict)))
        )
        
        # Check for game over indicators
        has_game_over = (
            'game_over' in packet_data or
            'result' in packet_data or
            'winner' in packet_data
        )
        
        return (keyword_matches >= 2 and has_drawback_structure) or (has_game_over and has_drawback_structure)
    
    def get_captured_packets(self) -> list:
        """Get all captured packets."""
        return self.captured_packets.copy()
    
    def clear_packets(self):
        """Clear captured packets."""
        self.captured_packets.clear()
    
    def export_packets(self, filename: str):
        """Export captured packets to file."""
        with open(filename, 'w') as f:
            json.dump(self.captured_packets, f, indent=2)
        
        print(f"Exported {len(self.captured_packets)} packets to {filename}")


class ManualPacketCapture:
    """Manual packet capture for testing and development."""
    
    @staticmethod
    def simulate_reveal_packet(white_drawback: str, black_drawback: str, 
                              result: str) -> Dict[str, Any]:
        """Simulate a typical reveal packet format."""
        return {
            "game_over": True,
            "result": result,
            "players": {
                "white": {
                    "drawback": white_drawback,
                    "score": 1.0 if result == "white_win" else 0.0
                },
                "black": {
                    "drawback": black_drawback,
                    "score": 1.0 if result == "black_win" else 0.0
                }
            },
            "timestamp": datetime.utcnow().isoformat(),
            "game_id": str(uuid.uuid4())
        }
    
    @staticmethod
    def simulate_alternative_format(white_drawback: str, black_drawback: str) -> Dict[str, Any]:
        """Simulate an alternative packet format."""
        return {
            "match_complete": True,
            "drawbacks": {
                "white": white_drawback,
                "black": black_drawback
            },
            "final_position": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "moves": ["e2e4", "e7e5", "g1f3", "b8c6"]
        }


# Global monitor instance
_monitor: Optional[PacketMonitor] = None


def get_packet_monitor() -> PacketMonitor:
    """Get the global packet monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PacketMonitor()
    return _monitor


def setup_recorder_integration():
    """Set up integration between packet monitor and game recorder."""
    from .game_recorder import get_recorder
    
    monitor = get_packet_monitor()
    recorder = get_recorder()
    
    def on_reveal_packet(packet_data: Dict[str, Any]):
        """Handle captured reveal packet."""
        try:
            recorder.capture_reveal_packet(packet_data)
            print("Reveal packet captured and integrated with game recorder")
        except Exception as e:
            print(f"Error integrating packet with recorder: {e}")
    
    monitor.set_capture_callback(on_reveal_packet)


# Example usage
def test_packet_capture():
    """Test packet capture with simulated data."""
    monitor = get_packet_monitor()
    
    # Simulate different packet formats
    packet1 = ManualPacketCapture.simulate_reveal_packet(
        "No_Castling", "Knight_Immobility", "white_win"
    )
    
    packet2 = ManualPacketCapture.simulate_alternative_format(
        "Queen_Capture_Ban", "Pawn_Immunity"
    )
    
    monitor.add_packet(packet1)
    monitor.add_packet(packet2)
    
    print(f"Captured {len(monitor.get_captured_packets())} packets")
    
    # Export for analysis
    monitor.export_packets("test_packets.json")
