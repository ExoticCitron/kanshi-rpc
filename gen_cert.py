"""
Run this ONCE to generate a trusted localhost SSL certificate.

Preferred method: mkcert (no browser warning needed)
  1. Install mkcert: https://github.com/FiloSottile/mkcert#installation
     Windows:  winget install FiloSottile.mkcert
     macOS:    brew install mkcert
     Linux:    see https://github.com/FiloSottile/mkcert#linux
  2. Run: mkcert -install
  3. Run: mkcert localhost
     -> produces localhost.pem + localhost-key.pem (already trusted by your browser)

Fallback method (this script): self-signed cert — works but requires a one-time
browser trust step (visit https://localhost:8080 and click Advanced > Proceed).
"""
import datetime
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent


def try_mkcert():
    """Try using mkcert to generate a trusted cert."""
    try:
        subprocess.run(["mkcert", "-version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    print("mkcert found! Generating trusted localhost certificate...")
    subprocess.run(["mkcert", "-install"], check=True)
    result = subprocess.run(
        ["mkcert", "localhost"],
        check=True,
        capture_output=True,
        text=True,
        cwd=HERE,
    )
    print(result.stdout or "donee")
    cert = HERE / "localhost.pem"
    key  = HERE / "localhost-key.pem"
    if cert.exists() and key.exists():
        print(f"\nCertificate: {cert}")
        print(f"Private key: {key}")
        print("\nAll done — no browser trust step needed. Run discord_helper.py!")
        return True
    return False


def fallback_selfsigned():
    """Generate a self-signed cert using the cryptography package."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        print("Installing cryptography package...")
        subprocess.run([sys.executable, "-m", "pip", "install", "cryptography", "-q"], check=True)
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

    import datetime

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_path = HERE / "localhost.pem"
    key_path  = HERE / "localhost-key.pem"

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

    print(f"Certificate written to: {cert_path}")
    print(f"Private key written to: {key_path}")
    print()
    print("IMPORTANT — one-time browser trust step required:")
    print("  1. Start discord_helper.py")
    print("  2. Visit https://localhost:8080 in your browser")
    print("  3. Click 'Advanced' → 'Proceed to localhost (unsafe)'")
    print("  4. Close that tab — done! Your browser now trusts the cert.")
    print()
    print("TIP: Install mkcert to skip this step entirely next time.")
    print("  Windows Command Prompt: winget install FiloSottile.mkcert OR `"%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" install FiloSottile.mkcert`")
    print("  macOS:   brew install mkcert")


if __name__ == "__main__":
    print("Kanshi Discord Helper — Certificate Generator")
    print("=" * 50)
    if not try_mkcert():
        print("mkcert not found, falling back to self-signed certificate...\n")
        fallback_selfsigned()
