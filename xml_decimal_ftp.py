import json
import os
import sys
import xml.etree.ElementTree as ET
from ftplib import FTP


def load_config(config_path: str = "config.json") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_decimal_text(text):
    if text is None:
        return text
    return text.replace(",", ".")


def find_matching_elements(root, path_parts):
    """
    Nájde elementy podľa cesty typu:
    SHOPITEM/LOGISTIC/WEIGHT
    SHOPITEM/PRICELISTS/PRICELIST/PRICE_VAT
    """
    current = [root]

    for part in path_parts:
        next_nodes = []
        for node in current:
            next_nodes.extend(node.findall(part))
        current = next_nodes

        if not current:
            break

    return current


def modify_xml(input_xml, output_xml, element_paths):
    tree = ET.parse(input_xml)
    root = tree.getroot()

    changed_count = 0

    for raw_path in element_paths:
        path = raw_path.strip().strip("/")
        if not path:
            continue

        parts = [p for p in path.split("/") if p]
        matches = find_matching_elements(root, parts)

        for elem in matches:
            original = elem.text
            updated = normalize_decimal_text(original)

            if updated != original:
                elem.text = updated
                changed_count += 1

    tree.write(
        output_xml,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=False
    )
    return changed_count


def split_remote_destination(config):
    """
    Podpora dvoch možností:
    1. ftp_remote_dir + ftp_remote_filename
    2. destination = /quantity/quantity.xml
    """
    remote_dir = str(config.get("ftp_remote_dir", "")).strip()
    remote_filename = str(config.get("ftp_remote_filename", "")).strip()

    destination = str(config.get("destination", "")).strip()

    if destination and (not remote_dir or not remote_filename):
        normalized = destination.replace("\\", "/").rstrip("/")
        if "/" in normalized:
            remote_dir, remote_filename = normalized.rsplit("/", 1)
            if not remote_dir:
                remote_dir = "/"
        else:
            remote_dir = "/"
            remote_filename = normalized

    if not remote_dir:
        remote_dir = "/"

    if not remote_filename:
        raise ValueError("V konfigurácii chýba ftp_remote_filename alebo destination.")

    return remote_dir, remote_filename


def upload_to_ftp(config):
    ftp_host = config["ftp_host"]
    ftp_user = config.get("ftp_username") or config.get("ftp_user")
    ftp_pass = config.get("ftp_password") or config.get("ftp_pass")
    local_file = config["output_xml"]

    if not ftp_user or not ftp_pass:
        raise ValueError("V konfigurácii chýba ftp_username/ftp_user alebo ftp_password/ftp_pass.")

    remote_dir, remote_filename = split_remote_destination(config)

    ftp = FTP(ftp_host, timeout=60)
    ftp.login(ftp_user, ftp_pass)

    try:
        ftp.cwd(remote_dir)

        with open(local_file, "rb") as f:
            # quantity_modified.xml sa uloží na FTP ako quantity.xml
            ftp.storbinary(f"STOR {remote_filename}", f)

    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def main():
    try:
        config_path = "config.json"
        if len(sys.argv) > 1:
            config_path = sys.argv[1]

        config = load_config(config_path)

        input_xml = config.get("input_xml") or config.get("input name")
        output_xml = config.get("output_xml") or config.get("output name")
        element_paths = config.get("element_paths") or config.get("elements") or []

        if not input_xml:
            raise ValueError("Chýba input_xml (alebo input name) v configu.")
        if not output_xml:
            raise ValueError("Chýba output_xml (alebo output name) v configu.")
        if not isinstance(element_paths, list) or not element_paths:
            raise ValueError("Chýba element_paths v configu alebo je prázdny.")

        if not os.path.exists(input_xml):
            raise FileNotFoundError(f"Vstupný XML súbor neexistuje: {input_xml}")

        changed = modify_xml(input_xml, output_xml, element_paths)
        print(f"XML upravené. Zmenených hodnôt: {changed}")
        print(f"Lokálny výstup: {output_xml}")

        upload_to_ftp(config)
        remote_dir, remote_filename = split_remote_destination(config)
        print(f"FTP upload hotový: {remote_dir.rstrip('/')}/{remote_filename}")
        print("Súbor na FTP bol prepísaný, ak už existoval.")

        return 0

    except Exception as e:
        print(f"CHYBA: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
