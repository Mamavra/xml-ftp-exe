import json
import os
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import xml.etree.ElementTree as ET
from ftplib import FTP


def nacitaj_konfig(konfig_cesta="config.json"):
    with open(konfig_cesta, "r", encoding="utf-8") as f:
        return json.load(f)


def nahrad_ciarku_bodkou(text):
    if text is None:
        return text
    return text.replace(",", ".")


def zaokruhli_desatinne_cislo(text, pocet_miest):
    if text is None:
        return text

    vycistene = text.strip()
    if vycistene == "":
        return text

    normalizovane = vycistene.replace(",", ".")

    try:
        hodnota = Decimal(normalizovane)
    except InvalidOperation:
        return normalizovane

    kvant = Decimal("1") if int(pocet_miest) == 0 else Decimal("1." + ("0" * int(pocet_miest)))
    zaokruhlene = hodnota.quantize(kvant, rounding=ROUND_HALF_UP)

    if int(pocet_miest) == 0:
        return str(zaokruhlene.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return f"{zaokruhlene:.{int(pocet_miest)}f}"


def najdi_elementy_podla_cesty(koren, casti_cesty):
    aktualne = [koren]

    for cast in casti_cesty:
        dalsie = []
        for uzol in aktualne:
            dalsie.extend(uzol.findall(cast))
        aktualne = dalsie

        if not aktualne:
            break

    return aktualne


def dopln_predvolene_hodnoty_do_prazdnych(koren, predvolene_hodnoty_prazdnych):
    pocet_zmien = 0

    for xml_cesta, predvolena_hodnota in predvolene_hodnoty_prazdnych.items():
        casti = [p for p in xml_cesta.strip("/").split("/") if p]
        zhody = najdi_elementy_podla_cesty(koren, casti)

        for element in zhody:
            if element.text is None or element.text.strip() == "":
                element.text = str(predvolena_hodnota)
                pocet_zmien += 1

    return pocet_zmien


def aplikuj_zaokruhlovanie(koren, pravidla_zaokruhlovania):
    pocet_zmien = 0

    for xml_cesta, pocet_miest in pravidla_zaokruhlovania.items():
        casti = [p for p in xml_cesta.strip("/").split("/") if p]
        zhody = najdi_elementy_podla_cesty(koren, casti)

        for element in zhody:
            povodna_hodnota = element.text
            nova_hodnota = zaokruhli_desatinne_cislo(povodna_hodnota, pocet_miest)

            if nova_hodnota != povodna_hodnota and nova_hodnota is not None:
                element.text = nova_hodnota
                pocet_zmien += 1

    return pocet_zmien


def uprav_xml(vstupny_xml_subor, vystupny_xml_subor, elementy_ciarka_na_bodku, predvolene_hodnoty_prazdnych=None, pravidla_zaokruhlovania=None):
    strom = ET.parse(vstupny_xml_subor)
    koren = strom.getroot()

    pocet_zmien = 0

    for xml_cesta in elementy_ciarka_na_bodku:
        casti = [p for p in xml_cesta.strip("/").split("/") if p]
        zhody = najdi_elementy_podla_cesty(koren, casti)

        for element in zhody:
            povodna_hodnota = element.text
            nova_hodnota = nahrad_ciarku_bodkou(povodna_hodnota)

            if nova_hodnota != povodna_hodnota:
                element.text = nova_hodnota
                pocet_zmien += 1

    if predvolene_hodnoty_prazdnych:
        pocet_zmien += dopln_predvolene_hodnoty_do_prazdnych(koren, predvolene_hodnoty_prazdnych)

    if pravidla_zaokruhlovania:
        pocet_zmien += aplikuj_zaokruhlovanie(koren, pravidla_zaokruhlovania)

    strom.write(
        vystupny_xml_subor,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=False
    )
    return pocet_zmien


def rozdel_ftp_ciel(konfig):
    ftp_priecinok = str(konfig.get("ftp_priecinok", "")).strip()
    ftp_nazov_suboru = str(konfig.get("ftp_nazov_suboru", "")).strip()

    ftp_ciel = str(konfig.get("ftp_ciel", "")).strip()

    if ftp_ciel and (not ftp_priecinok or not ftp_nazov_suboru):
        normalizovane = ftp_ciel.replace("\\", "/").rstrip("/")
        if "/" in normalizovane:
            ftp_priecinok, ftp_nazov_suboru = normalizovane.rsplit("/", 1)
            if not ftp_priecinok:
                ftp_priecinok = "/"
        else:
            ftp_priecinok = "/"
            ftp_nazov_suboru = normalizovane

    if not ftp_priecinok:
        ftp_priecinok = "/"

    if not ftp_nazov_suboru:
        raise ValueError("V konfigurácii chýba ftp_nazov_suboru alebo ftp_ciel.")

    return ftp_priecinok, ftp_nazov_suboru


def nahraj_na_ftp(konfig):
    ftp_server = konfig["ftp_server"]
    ftp_uzivatel = konfig["ftp_uzivatel"]
    ftp_heslo = konfig["ftp_heslo"]
    lokalny_subor = konfig["nazov_vystupneho_suboru"]

    ftp_priecinok, ftp_nazov_suboru = rozdel_ftp_ciel(konfig)

    ftp = FTP(ftp_server, timeout=60)
    ftp.login(ftp_uzivatel, ftp_heslo)

    try:
        ftp.cwd(ftp_priecinok)

        with open(lokalny_subor, "rb") as f:
            ftp.storbinary(f"STOR {ftp_nazov_suboru}", f)

    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def main():
    try:
        konfig_cesta = "config.json"
        if len(sys.argv) > 1:
            konfig_cesta = sys.argv[1]

        konfig = nacitaj_konfig(konfig_cesta)

        vstupny_xml_subor = konfig.get("nazov_vstupneho_suboru")
        vystupny_xml_subor = konfig.get("nazov_vystupneho_suboru")
        elementy_ciarka_na_bodku = konfig.get("elementy_ciarka_na_bodku", [])
        predvolene_hodnoty_prazdnych = konfig.get("predvolene_hodnoty_prazdnych", {})
        pravidla_zaokruhlovania = konfig.get("pravidla_zaokruhlovania", {})

        if not vstupny_xml_subor:
            raise ValueError("Chýba nazov_vstupneho_suboru v configu.")
        if not vystupny_xml_subor:
            raise ValueError("Chýba nazov_vystupneho_suboru v configu.")
        if not isinstance(elementy_ciarka_na_bodku, list) or not elementy_ciarka_na_bodku:
            raise ValueError("Chýba elementy_ciarka_na_bodku v configu alebo je prázdny.")
        if not konfig.get("ftp_server"):
            raise ValueError("Chýba ftp_server v configu.")
        if not konfig.get("ftp_uzivatel"):
            raise ValueError("Chýba ftp_uzivatel v configu.")
        if not konfig.get("ftp_heslo"):
            raise ValueError("Chýba ftp_heslo v configu.")

        if not os.path.exists(vstupny_xml_subor):
            raise FileNotFoundError(f"Vstupný XML súbor neexistuje: {vstupny_xml_subor}")

        pocet_zmien = uprav_xml(
            vstupny_xml_subor,
            vystupny_xml_subor,
            elementy_ciarka_na_bodku,
            predvolene_hodnoty_prazdnych=predvolene_hodnoty_prazdnych,
            pravidla_zaokruhlovania=pravidla_zaokruhlovania
        )
        print(f"XML upravené. Zmenených hodnôt: {pocet_zmien}")
        print(f"Lokálny výstup: {vystupny_xml_subor}")

        nahraj_na_ftp(konfig)
        ftp_priecinok, ftp_nazov_suboru = rozdel_ftp_ciel(konfig)
        print(f"FTP upload hotový: {ftp_priecinok.rstrip('/')}/{ftp_nazov_suboru}")
        print("Súbor na FTP bol prepísaný, ak už existoval.")

        return 0

    except Exception as e:
        print(f"CHYBA: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
