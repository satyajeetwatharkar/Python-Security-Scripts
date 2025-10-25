import argparse

parser = argparse.ArgumentParser(description="Simple CLI demo tool")
parser.add_argument("--name", help="Your name")
parser.add_argument("--count", type=int, default=1,help="How many times to greet")

args=parser.parse_args()

for _ in range(args.count):
    print(f"Hello, {args.name}")