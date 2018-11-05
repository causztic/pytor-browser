"""Generate RSA keys"""

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def main():
    """Main function"""
    for i in range(100):
        key = rsa.generate_private_key(
            backend=default_backend(),
            public_exponent=65537,
            key_size=4096
        )  # used for signing, etc.
        private_bytes = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_bytes = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        private_file = open("privates/privatetest" + str(i) + ".pem", "wb")
        private_file.write(private_bytes)
        public = open("publics/publictest" + str(i) + ".pem", "wb")
        public.write(public_bytes)
        private_file.close()
        public.close()
        privatetest = open("privates/privatetest" + str(i) + ".pem", "rb")
        print(privatetest.read() == private_bytes)
        publictest = open("publics/publictest" + str(i) + ".pem", "rb")
        print(publictest.read() == public_bytes)
        privatetest.close()
        publictest.close()

    for i in range(30):
        with open("privates/privatetest" + str(i) + ".pem", "rb") as key_file:
            _ = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend())
            key_file.close()
        with open("publics/publictest"+str(i)+".pem", "rb") as key_file:
            _ = serialization.load_pem_public_key(
                key_file.read(), backend=default_backend())
            key_file.close()


if __name__ == "__main__":
    main()
