"""Construit igaging-caliper.nvda-addon (dans le dossier du projet) à partir
de nvda/piedCoulisse/. À relancer après toute retouche de l'extension, puis
ouvrir le fichier .nvda-addon pour la réinstaller dans NVDA.

Les traductions (locale/<langue>/LC_MESSAGES/nvda.po) sont compilées en
nvda.mo au passage ; seul le .mo part dans l'extension."""
import ast
import py_compile
import struct
import zipfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
SRC = ICI / "piedCoulisse"
SORTIE = ICI.parent / "igaging-caliper.nvda-addon"


def lire_po(chemin):
    """Couples msgid → msgstr d'un .po simple (sans pluriels ni contextes)."""
    entrees, champ = {}, None
    courant = {"msgid": "", "msgstr": ""}

    def ranger():
        if courant["msgstr"]:     # non traduit : on garde l'anglais
            entrees[courant["msgid"]] = courant["msgstr"]

    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        if ligne.startswith("msgid "):
            if champ == "msgstr":
                ranger()
            courant = {"msgid": "", "msgstr": ""}
            champ, ligne = "msgid", ligne[6:]
        elif ligne.startswith("msgstr "):
            champ, ligne = "msgstr", ligne[7:]
        courant[champ] += ast.literal_eval(ligne)
    if champ == "msgstr":
        ranger()
    return entrees


def ecrire_mo(entrees, chemin):
    cles = sorted(entrees)
    ids = [k.encode("utf-8") for k in cles]
    strs = [entrees[k].encode("utf-8") for k in cles]
    n = len(cles)
    debut = 7 * 4 + 16 * n
    tables, donnees = [], b""
    for liste in (ids, strs):
        table = []
        for s in liste:
            table.append((len(s), debut + len(donnees)))
            donnees += s + b"\0"
        tables.append(table)
    entete = struct.pack("<7I", 0x950412DE, 0, n, 28, 28 + 8 * n, 0, 0)
    corps = b"".join(struct.pack("<2I", *t) for t in tables[0] + tables[1])
    chemin.write_bytes(entete + corps + donnees)


for module in (SRC / "globalPlugins").glob("*.py"):
    py_compile.compile(str(module), doraise=True)
for po in SRC.glob("locale/*/LC_MESSAGES/*.po"):
    ecrire_mo(lire_po(po), po.with_suffix(".mo"))
with zipfile.ZipFile(SORTIE, "w", zipfile.ZIP_DEFLATED) as z:
    for f in SRC.rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".po":
            z.write(f, f.relative_to(SRC).as_posix())
print(f"{SORTIE.name} : {', '.join(zipfile.ZipFile(SORTIE).namelist())}")
