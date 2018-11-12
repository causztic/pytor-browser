"""
Suite of commands to run on the console
for various information
"""
import sys
from client import Client

def main():
	"""Main function"""
	results = []
	try:
		if sys.argv[1] == "directory":
			if len(sys.argv) == 4:
				results = Client.get_directory_items((sys.argv[2], sys.argv[3]))
			else:
				results = Client.get_directory_items()
		for datum in results:
			print(datum['ip_addr'], datum['port'])
	except ConnectionRefusedError:
		sys.stderr.write('Directory offline. \n')

if __name__ == "__main__":
	main()