import requests
import sys
import time
import multiprocessing
from json import loads
from multiprocessing import Queue, Lock, Process, current_process, Event
from argparse import ArgumentParser
from queue import Empty


def info(message):
    print(f"\033[94m[*]\033[0m {message}")

def success(message):
    print(f"\033[92m[+]\033[0m {message}")

def warning(message):
    print(f"\033[93m[!]\033[0m {message}")

def error(message):
    print(f"\033[91m[-]\033[0m {message}")

def parse_arguments():
    parser = ArgumentParser(description="A simple JSON bruteforce tool for penetration testers or hobbyists based on https://github.com/Jake-Ruston/JSONBrute")

    parser.add_argument("--url", type=str, required=True, help="The URL to post the data to.")
    parser.add_argument("--wordlist", type=str, required=True, help="The wordlist to use to fuzz with.")
    parser.add_argument("--data", type=str, required=True, help="The JSON data to post.")
    parser.add_argument("--processes", type=int, nargs="?", required=False, help="Number of processes to spawn (default 1)")
    parser.add_argument("--verbose", nargs="?", const="false", help="Print every request.")
    parser.add_argument("--code", type=int, nargs="?", const="401", help="The response code for an unsuccessful request")

    return parser.parse_args()

def parse_wordlist(file):
    with open(file, mode="r", encoding="iso-8859-1") as data:
        wordlist = data.read().splitlines()
        
        return wordlist


def parse_json(data):
    json = data.split(",")
    json = [pair.strip().split("=") for pair in json]
    json = {key: value for [key, value] in json}

    return json

def parse_fuzzed_parameter(json):
    fuzzed = list(json.keys())[list(json.values()).index("FUZZ")]

    return fuzzed
    

def do_job(queue, event, args):  
    while True:
        try:
            entry = queue.get_nowait()
        except Empty:
            warning("Queue empty!")
            warning(f"\"{fuzzed}\" not found")
            event.set()
            break
        else:
            try:

                headers = {
                    "Content-Type": "application/json"
                }
                json = parse_json(args.data)
                fuzzed = parse_fuzzed_parameter(json)    
                json = str(json)
                json = json.replace("FUZZ", entry)
                json = json.replace("'", "\"")
                json = loads(json)
            
                request = requests.post(args.url, headers=headers, json=json)

                if not args.code:
                    args.code = 401
            
                if request.status_code != args.code:
                    success(f"Found \"{fuzzed}\": {json[fuzzed]}")
                    event.set()
                    break
                else:
                    if args.verbose:
                        warning(f"Incorrect \"{fuzzed}\": {json[fuzzed]} ")
            except requests.ConnectionError:
                error(f"Failed to connect to {args.url}")
                SystemExit()
                       

def find(args, wordlist):

    event = Event()
    number_of_processes = args.processes
    
    if not number_of_processes:
        number_of_processes = 1   
       
    if number_of_processes > multiprocessing.cpu_count():
        number_of_processes = multiprocessing.cpu_count()
        info(f"Number of requested processes exceeds number of available CPU cores")
        
    if args.processes < 1:
        number_of_processes = 1
        info(f"Number of requested processes makes no sense")
              
    if number_of_processes == 1:
        info(f"Spawning 1 process")
    else:
        info(f"Spawning {number_of_processes} processes")
              
    
    processes = []
    
    queue = Queue()
    for entry in wordlist:
        queue.put(entry)      
        
    for w in range(number_of_processes):
        p = Process(target=do_job, args=(queue, event, args))
        processes.append(p)
        p.start()
        
    while True:
        try:
            if event.is_set():
                for p in processes:
                    p.terminate()
                sys.exit(1)
            time.sleep(2)
        except KeyboardInterrupt:
            for p in processes:
                p.terminate()
            sys.exit(1)
            time.sleep(2)
        

if __name__ == '__main__':
        args = parse_arguments()
        wordlist = parse_wordlist(args.wordlist)
        info(f"Starting JSONBrute on {args.url}")
        find(args, wordlist)

