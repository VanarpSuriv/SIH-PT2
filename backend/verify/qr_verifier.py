"""
Local QR Code Decoder and SSRF-Safe Resolver for VERITAS.
Verifies approval letter QR codes locally without external network exposure.
Enforces strict domain whitelisting, scheme validation, credential blocking,
unusual port restrictions, private/loopback/link-local IPv4 and IPv6 checks,
and safe redirect validation to neutralize Server-Side Request Forgery (SSRF).
"""
import ipaddress
import re
import socket
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import cv2
import numpy as np

# Official Indian Technical Education & Regulatory Domain Whitelist
OFFICIAL_DOMAINS = [
    "aicte-india.org",
    "gov.in",
    "nic.in",
]

# Prohibited internal or non-routable top-level / private domain suffixes
RESTRICTED_DOMAIN_SUFFIXES = [
    ".local",
    ".localhost",
    ".internal",
    ".corp",
    ".home",
    ".lan",
    ".onion",
    ".test",
    ".invalid",
    ".example",
]

# Explicit restricted hostnames
RESTRICTED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "instance-data",
    "metadata.internal",
}

# Standard permitted web ports
PERMITTED_WEB_PORTS = {None, 80, 443}


def parse_ip_literal(ip_str: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address]:
    """
    Parse an IP literal from string representation, supporting:
    - Standard dotted-decimal IPv4 (127.0.0.1)
    - Bracketed or plain IPv6 (::1, [::1], fe80::1, fc00::1)
    - IPv4-mapped IPv6 (::ffff:127.0.0.1)
    - Decimal integer IPv4 notation (2130706433 -> 127.0.0.1)
    - Hexadecimal notation (0x7f000001 -> 127.0.0.1)
    - Octal notation (0177.0.0.1 -> 127.0.0.1)
    - Shorthand dotted notation (127.1 -> 127.0.0.1)
    Raises ValueError if ip_str is not an IP literal.
    """
    clean = str(ip_str).strip().strip("[]")
    if not clean:
        raise ValueError("Empty IP string")

    # 1. Standard library parser
    try:
        return ipaddress.ip_address(clean)
    except ValueError:
        pass

    # 2. Test inet_aton for non-standard IPv4 representations (hex, octal, shorthand)
    try:
        # Avoid treating arbitrary non-numeric hostnames as IPs
        if not any(c not in "0123456789abcdefABCDEF.xX" for c in clean):
            packed = socket.inet_aton(clean)
            return ipaddress.IPv4Address(packed)
    except (OSError, ValueError):
        pass

    # 3. Pure integer representation
    if clean.isdigit():
        val = int(clean)
        if 0 <= val <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(val)
        else:
            return ipaddress.IPv6Address(val)

    raise ValueError(f"'{ip_str}' is not an IP literal")


def is_ip_restricted(ip_input: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address]) -> Tuple[bool, str]:
    """
    Check if an IPv4 or IPv6 address belongs to private, loopback, link-local,
    metadata, multicast, carrier-grade NAT, or reserved subnets.
    Handles standard and non-standard IP literals (integer, hex, octal, shorthand).
    Returns (is_restricted: bool, reason: str).
    """
    try:
        if isinstance(ip_input, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            ip_obj = ip_input
        else:
            ip_obj = parse_ip_literal(str(ip_input))
    except ValueError:
        return False, "Not an IP literal"

    # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        v4_mapped = ip_obj.ipv4_mapped
        is_restr, reason = is_ip_restricted(v4_mapped)
        if is_restr:
            return True, f"IPv4-mapped IPv6 ({ip_obj}) points to restricted IPv4: {reason}"

    # Loopback: 127.0.0.0/8 or ::1
    if ip_obj.is_loopback:
        return True, f"Loopback address ({ip_obj})"

    # Private RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) or IPv6 ULA (fc00::/7)
    if ip_obj.is_private:
        return True, f"Private subnet address ({ip_obj})"

    # Link-Local RFC 3927 (169.254.0.0/16) or IPv6 link-local (fe80::/10)
    if ip_obj.is_link_local:
        return True, f"Link-local / Cloud metadata subnet address ({ip_obj})"

    # Multicast or unspecified (0.0.0.0 or ::)
    if ip_obj.is_multicast or ip_obj.is_unspecified:
        return True, f"Multicast or unspecified address ({ip_obj})"

    # Reserved
    if ip_obj.is_reserved:
        return True, f"Reserved address ({ip_obj})"

    # IPv4 specific subnets
    if isinstance(ip_obj, ipaddress.IPv4Address):
        # Current network "this network" RFC 1122 (0.0.0.0/8)
        if ip_obj in ipaddress.ip_network("0.0.0.0/8"):
            return True, f"Current network / zero address block ({ip_obj})"

        # Reserved for future use RFC 1112 (240.0.0.0/4)
        if ip_obj in ipaddress.ip_network("240.0.0.0/4"):
            return True, f"Reserved for future use address ({ip_obj})"

        # Carrier-Grade NAT RFC 6598 (100.64.0.0/10)
        cgnat_net = ipaddress.ip_network("100.64.0.0/10")
        if ip_obj in cgnat_net:
            return True, f"Carrier-Grade NAT address ({ip_obj})"

        # Documentation networks: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24
        for doc_net in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"):
            if ip_obj in ipaddress.ip_network(doc_net):
                return True, f"Documentation subnet address ({ip_obj})"

    return False, "Public routable address"


class QRCodeVerifier:
    """
    Decodes and verifies QR codes found on institutional approval documents,
    ensuring safe offline/sandboxed parsing with comprehensive SSRF protection.
    """

    @staticmethod
    def decode_from_image(image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Decode any 2D QR codes present on the image using OpenCV.
        Executes purely locally on image pixels; performs zero network requests.
        """
        if image_bgr is None or image_bgr.size == 0:
            return []

        try:
            detector = cv2.QRCodeDetector()
            decoded_info, points, _ = detector.detectAndDecode(image_bgr)
            results = []
            if decoded_info and len(decoded_info.strip()) > 0:
                results.append({
                    "payload": decoded_info.strip(),
                    "points": points.tolist() if points is not None else [],
                })
            return results
        except Exception:
            return []

    @staticmethod
    def verify_payload(payload: str, resolve_dns: bool = False) -> Dict[str, Any]:
        """
        Verify QR payload for regulatory authenticity and SSRF safety.
        Inspects URI scheme, credentials, ports, hostname, IP literal, and DNS resolution.
        Returns:
            status: 'VERIFIED_OFFICIAL' | 'EXTERNAL_ADVISORY' | 'SSRF_REJECTED' | 'NON_URL_DATA' | 'DNS_RESOLUTION_FAILED'
            domain: str
            safe: bool
            message: str
        """
        if not payload or not isinstance(payload, str):
            return {
                "status": "NON_URL_DATA",
                "safe": False,
                "message": "Empty or non-string payload.",
            }

        cleaned = payload.strip()

        # 1. Parse URL
        try:
            parsed = urlparse(cleaned)
        except Exception as parse_err:
            return {
                "status": "SSRF_REJECTED",
                "safe": False,
                "message": f"Malformed URL syntax: {parse_err}",
            }

        # 2. Validate Scheme
        if parsed.scheme:
            scheme_lower = parsed.scheme.lower()
            if scheme_lower not in ("http", "https"):
                return {
                    "status": "SSRF_REJECTED",
                    "safe": False,
                    "domain": parsed.netloc or parsed.path,
                    "message": f"Disallowed URI scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.",
                }
        else:
            # Plain text data (e.g., application ID or JSON payload)
            return {
                "status": "NON_URL_DATA",
                "safe": True,
                "domain": None,
                "payload_snippet": cleaned[:80],
                "message": "QR contains non-URL plaintext data.",
            }

        if not parsed.netloc and not parsed.hostname:
            return {
                "status": "NON_URL_DATA",
                "safe": True,
                "domain": None,
                "payload_snippet": cleaned[:80],
                "message": "QR contains non-URL plaintext data.",
            }

        # 3. Reject credentials in URLs (e.g. http://user:pass@host)
        if parsed.username or parsed.password:
            return {
                "status": "SSRF_REJECTED",
                "safe": False,
                "domain": parsed.hostname,
                "message": "Credentials embedded in URL (user:pass@) are disallowed.",
            }

        # 4. Enforce standard ports (block port scanning e.g. :22, :6379, :8000, :8080)
        try:
            port = parsed.port
            if port not in PERMITTED_WEB_PORTS:
                return {
                    "status": "SSRF_REJECTED",
                    "safe": False,
                    "domain": parsed.hostname,
                    "port": port,
                    "message": f"Unusual port {port} is disallowed. Only standard HTTP (80) and HTTPS (443) ports are permitted.",
                }
        except ValueError:
            return {
                "status": "SSRF_REJECTED",
                "safe": False,
                "domain": None,
                "message": "Malformed port specification in URL.",
            }

        hostname = parsed.hostname
        if not hostname:
            return {
                "status": "SSRF_REJECTED",
                "safe": False,
                "domain": None,
                "message": "Missing hostname in URL.",
            }

        lower_host = hostname.lower()

        # 5. Check restricted hostnames and suffixes (localhost, *.internal, etc.)
        if lower_host in RESTRICTED_HOSTNAMES:
            return {
                "status": "SSRF_REJECTED",
                "safe": False,
                "domain": hostname,
                "message": f"SSRF defense: Target hostname '{hostname}' is a restricted local or metadata name.",
            }

        for suff in RESTRICTED_DOMAIN_SUFFIXES:
            if lower_host.endswith(suff):
                return {
                    "status": "SSRF_REJECTED",
                    "safe": False,
                    "domain": hostname,
                    "message": f"SSRF defense: Target domain '{hostname}' has restricted non-routable suffix '{suff}'.",
                }

        # 6. Check if hostname itself is an IP literal (IPv4 or IPv6, including integer/hex/octal/shorthand notations)
        try:
            # Handle brackets if IPv6 literal leaked through
            raw_ip_str = lower_host.strip("[]")
            ip_obj = parse_ip_literal(raw_ip_str)
            is_restr, reason = is_ip_restricted(ip_obj)
            if is_restr:
                return {
                    "status": "SSRF_REJECTED",
                    "safe": False,
                    "domain": hostname,
                    "ip": str(ip_obj),
                    "message": f"SSRF defense: Target IP {hostname} is restricted ({reason}).",
                }
            # Valid public IP literal (e.g. 93.184.216.34)
            return {
                "status": "EXTERNAL_ADVISORY",
                "safe": True,
                "domain": hostname,
                "ip": str(ip_obj),
                "message": f"Advisory: Direct IP literal {hostname} is outside the official AICTE/Government whitelist.",
            }
        except ValueError:
            # Hostname is a domain name, not an IP literal
            pass

        # 7. Check official regulatory domain whitelist
        is_official = False
        for dom in OFFICIAL_DOMAINS:
            if lower_host == dom or lower_host.endswith("." + dom):
                is_official = True
                break

        # 8. Safe DNS Resolution check (detect DNS rebinding or domains mapping to private IPs)
        if resolve_dns:
            try:
                addr_info = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
                resolved_ips = []
                for entry in addr_info:
                    sockaddr = entry[4]
                    ip_str = sockaddr[0]
                    resolved_ips.append(ip_str)
                    is_restr, reason = is_ip_restricted(ip_str)
                    if is_restr:
                        return {
                            "status": "SSRF_REJECTED",
                            "safe": False,
                            "domain": hostname,
                            "resolved_ip": ip_str,
                            "message": f"SSRF defense: Domain '{hostname}' resolves to restricted IP {ip_str} ({reason}).",
                        }
            except socket.gaierror as gai_err:
                # DNS resolution failed
                if is_official:
                    return {
                        "status": "DNS_RESOLUTION_FAILED",
                        "safe": False,
                        "domain": hostname,
                        "message": f"DNS resolution failed for official domain '{hostname}': {gai_err}",
                    }
                else:
                    return {
                        "status": "DNS_RESOLUTION_FAILED",
                        "safe": False,
                        "domain": hostname,
                        "message": f"DNS resolution failed for domain '{hostname}': {gai_err}",
                    }
            except Exception as res_err:
                return {
                    "status": "DNS_RESOLUTION_FAILED",
                    "safe": False,
                    "domain": hostname,
                    "message": f"Resolution error for domain '{hostname}': {res_err}",
                }

        # 9. Return official or external advisory outcome
        if is_official:
            return {
                "status": "VERIFIED_OFFICIAL",
                "safe": True,
                "domain": hostname,
                "message": f"Verified official regulatory domain: {hostname}",
            }

        return {
            "status": "EXTERNAL_ADVISORY",
            "safe": True,
            "domain": hostname,
            "message": f"Advisory: Domain '{hostname}' is outside the official AICTE/Government whitelist.",
        }


class SafeUrlResolver:
    """
    Validates redirect destinations to prevent redirect-based SSRF.
    Ensures that clients cannot be silently redirected to prohibited internal destinations.
    Provides DNS pinning to neutralize Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding attacks.
    """

    @staticmethod
    def validate_redirect_chain(
        initial_url: str,
        redirect_urls: List[str],
        max_redirects: int = 3,
        resolve_dns: bool = False
    ) -> Dict[str, Any]:
        """
        Validate all hops in an HTTP redirect chain.
        Ensures that every intermediate and final redirect destination satisfies strict SSRF checks.
        Supports optional DNS resolution per hop to detect DNS rebinding.
        """
        # Validate initial URL
        init_res = QRCodeVerifier.verify_payload(initial_url, resolve_dns=resolve_dns)
        if not init_res["safe"]:
            return {
                "valid": False,
                "failed_hop": initial_url,
                "reason": f"Initial URL rejected: {init_res.get('message')}"
            }

        if len(redirect_urls) > max_redirects:
            return {
                "valid": False,
                "failed_hop": redirect_urls[-1] if redirect_urls else initial_url,
                "reason": f"Exceeded maximum allowed redirects ({max_redirects})"
            }

        for idx, r_url in enumerate(redirect_urls):
            hop_res = QRCodeVerifier.verify_payload(r_url, resolve_dns=resolve_dns)
            if not hop_res["safe"]:
                return {
                    "valid": False,
                    "failed_hop_index": idx + 1,
                    "failed_hop": r_url,
                    "reason": f"Redirect hop #{idx + 1} rejected: {hop_res.get('message')}"
                }

        return {
            "valid": True,
            "total_hops": len(redirect_urls),
            "final_destination": redirect_urls[-1] if redirect_urls else initial_url
        }

    @staticmethod
    def safe_resolve_and_pin(url: str) -> Dict[str, Any]:
        """
        Validate URL for SSRF safety and resolve its IP address, returning the pinned IP
        to prevent Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding attacks during HTTP connections.
        """
        eval_res = QRCodeVerifier.verify_payload(url, resolve_dns=True)
        if not eval_res.get("safe", False):
            return {
                "safe": False,
                "pinned_ip": None,
                "status": eval_res.get("status"),
                "reason": eval_res.get("message", "URL failed SSRF validation.")
            }

        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return {"safe": False, "pinned_ip": None, "reason": "Missing hostname in URL"}

        # If already an IP literal
        try:
            ip_obj = parse_ip_literal(hostname)
            return {
                "safe": True,
                "pinned_ip": str(ip_obj),
                "hostname": hostname,
                "port": parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                "scheme": parsed.scheme.lower()
            }
        except ValueError:
            pass

        # Resolve hostname and verify all returned addresses
        try:
            addr_info = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            if not addr_info:
                return {"safe": False, "pinned_ip": None, "reason": f"No DNS addresses resolved for '{hostname}'"}

            resolved_ips = []
            for entry in addr_info:
                ip_str = entry[4][0]
                is_restr, reason = is_ip_restricted(ip_str)
                if is_restr:
                    return {
                        "safe": False,
                        "pinned_ip": None,
                        "reason": f"DNS rebinding defense: Resolved IP {ip_str} is restricted ({reason})"
                    }
                resolved_ips.append(ip_str)

            # Pin to the first verified public IP
            return {
                "safe": True,
                "pinned_ip": resolved_ips[0],
                "all_resolved_ips": resolved_ips,
                "hostname": hostname,
                "port": parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                "scheme": parsed.scheme.lower()
            }
        except Exception as e:
            return {"safe": False, "pinned_ip": None, "reason": f"DNS resolution failed: {e}"}
