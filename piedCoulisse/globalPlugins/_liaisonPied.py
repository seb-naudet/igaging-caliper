# État de la liaison Bluetooth du pied à coulisse, lu dans l'arbre des
# périphériques Windows (ctypes seul : NVDA n'embarque pas de bibliothèque
# Bluetooth). Le nom commence par « _ » pour que NVDA ne le charge pas comme
# une extension globale. Ne dépend pas de NVDA : se teste avec un Python ordinaire.

import ctypes
from ctypes import byref, c_ulong, c_wchar_p, create_unicode_buffer

NOM_PIED = "Bluetooth Keyboard"     # nom donné par les pieds iGaging à l'appairage
FILTRE_ENUMERATEUR = 1              # CM_GETIDLIST_FILTER_ENUMERATOR
NOEUD_FANTOME = 1                   # CM_LOCATE_DEVNODE_PHANTOM
TYPE_BOOLEEN = 0x11                 # DEVPROP_TYPE_BOOLEAN
TYPE_OCTET = 0x03                   # DEVPROP_TYPE_BYTE

cfgmgr = ctypes.WinDLL("cfgmgr32")


class Guid(ctypes.Structure):
    _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16), ("c", ctypes.c_uint16),
                ("d", ctypes.c_ubyte * 8)]


class ClePropriete(ctypes.Structure):
    _fields_ = [("fmtid", Guid), ("pid", c_ulong)]


# DEVPKEY_Device_FriendlyName
CLE_NOM = ClePropriete(
    Guid(0xA45C254E, 0xDF1C, 0x4EFD, (ctypes.c_ubyte * 8)(0x80, 0x20, 0x67, 0xD1, 0x46, 0xA8, 0x50, 0xE0)),
    14)
# « Connecté » d'un nœud BTHLE\DEV_<adresse> (propriété sans nom public).
CLE_CONNECTE = ClePropriete(
    Guid(0x83DA6326, 0x97A6, 0x4088, (ctypes.c_ubyte * 8)(0x94, 0x53, 0xA1, 0x92, 0x3F, 0x57, 0x3B, 0x29)),
    15)
# Niveau de pile suivi par Windows (propriété sans nom public).
GUID_PILE = Guid(0x104EA319, 0x6EE2, 0x4701, (ctypes.c_ubyte * 8)(0xBD, 0x47, 0x8D, 0xDB, 0xF4, 0x25, 0xBB, 0xE5))
CLE_PILE = ClePropriete(GUID_PILE, 2)


def lister(enumerateur):
    """Identifiants des périphériques d'un énumérateur, débranchés compris."""
    taille = c_ulong()
    if cfgmgr.CM_Get_Device_ID_List_SizeW(byref(taille), c_wchar_p(enumerateur), FILTRE_ENUMERATEUR):
        return []
    tampon = create_unicode_buffer(taille.value)
    if cfgmgr.CM_Get_Device_ID_ListW(c_wchar_p(enumerateur), tampon, taille, FILTRE_ENUMERATEUR):
        return []
    return [i for i in tampon[:].split("\0") if i]


def lire(identifiant, cle, tampon):
    """Remplit tampon avec une propriété du périphérique ; renvoie son type, ou None."""
    noeud = c_ulong()
    if cfgmgr.CM_Locate_DevNodeW(byref(noeud), c_wchar_p(identifiant), NOEUD_FANTOME):
        return None
    type_valeur, taille = c_ulong(), c_ulong(ctypes.sizeof(tampon))
    if cfgmgr.CM_Get_DevNode_PropertyW(noeud, byref(cle), byref(type_valeur),
                                       byref(tampon), byref(taille), 0):
        return None
    return type_valeur.value


def nom(identifiant):
    tampon = create_unicode_buffer(256)
    return tampon.value if lire(identifiant, CLE_NOM, tampon) is not None else ""


def est_connecte(identifiant):
    valeur = ctypes.c_ubyte()
    return lire(identifiant, CLE_CONNECTE, valeur) == TYPE_BOOLEEN and valeur.value != 0


def pile():
    """(niveau en %, pied connecté ?), ou None si Windows ne connaît pas le niveau.
    Pied connecté, le niveau est à jour : Windows le suit en direct (vérifié le
    09/11 par une lecture GATT directe). La date que Windows garde à côté (pid 7)
    est celle du dernier CHANGEMENT de niveau, pas d'un relevé : inutile."""
    for i in lister("BTHLE"):
        if nom(i) == NOM_PIED:
            niveau = ctypes.c_ubyte()
            if lire(i, CLE_PILE, niveau) == TYPE_OCTET:
                return niveau.value, est_connecte(i)
    return None


def pied_connecte():
    """Vrai si un appareil Bluetooth LE appairé nommé comme le pied est connecté."""
    return any(est_connecte(i) for i in lister("BTHLE") if nom(i) == NOM_PIED)
