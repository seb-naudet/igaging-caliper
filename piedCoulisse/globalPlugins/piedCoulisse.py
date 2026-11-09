# Extension NVDA « Pied à coulisse parlant » (28/10/2026).
#
# Le pied à coulisse iGaging est un clavier Bluetooth : à chaque envoi il tape
# F24, espace, puis la mesure (« 21.99 »), sans Entrée. Sur F24, cette
# extension capte et avale les touches qui suivent (aucune frappe n'arrive
# dans la fenêtre active, même en mode navigation), puis NVDA annonce la
# mesure et elle est ajoutée au fichier des mesures.
# Les touches sont lues par leur scancode (place sur le clavier) : la
# disposition AZERTY/QWERTY ne change rien.
#
# 30/10 : installable sur n'importe quel PC. Le dossier du fichier, la copie
# dans le presse-papiers et le journal des touches se règlent dans
# NVDA > Paramètres > Pied à coulisse.
# 30/10 (v1.2.0) : bilingue. Textes en anglais dans le code, traduction
# française dans locale/fr/LC_MESSAGES/nvda.po (compilée en .mo par
# construire.py) ; NVDA choisit selon sa propre langue.
# 06/11 (v1.4.0) : annonce la connexion et la déconnexion du pied (état lu par
# _liaisonPied.py dans un fil à part).
# 06/11 (v1.4.1) : le pied est reconnu par son nom Bluetooth, tous modèles.
# 06/11 (v1.5.0) : commande sans geste par défaut pour dire le niveau de pile.
# 09/11 : plus d'âge du relevé (la date de Windows est celle du dernier
# changement de niveau, donc trompeuse) ; pied déconnecté, « dernière valeur connue ».

import os
import re
import threading
import time
from datetime import datetime

import addonHandler
import api
import config
import globalPluginHandler
import gui
import keyboardHandler
import languageHandler
import ui
import wx
from gui import guiHelper
from logHandler import log
from scriptHandler import script

from . import _liaisonPied

addonHandler.initTranslation()

SILENCE_MS = 400        # fin de mesure après ce silence
DUREE_MAX_MS = 2000     # sécurité : la capture ne dure jamais plus
VEILLE_S = 0.5          # lecture de l'état de la liaison Bluetooth
STABLE_S = 2.0          # un changement doit durer ce temps avant d'être annoncé

config.conf.spec["piedCoulisse"] = {
    "enregistrer": "boolean(default=True)",
    "dossier": "string(default='')",
    "copier": "boolean(default=False)",
    "journal": "boolean(default=False)",
    "annoncer": "boolean(default=True)",
}

CHIFFRES = {0x02 + i: c for i, c in enumerate("1234567890")}
TOUCHES = dict(CHIFFRES)
TOUCHES.update({0x10 + i: c for i, c in enumerate("qwertyuiop")})
TOUCHES.update({0x1E + i: c for i, c in enumerate("asdfghjkl")})
TOUCHES.update({0x2C + i: c for i, c in enumerate("zxcvbnm")})
TOUCHES.update({0x0C: "-", 0x28: '"', 0x33: ".", 0x34: ".",
                0x47: "7", 0x48: "8", 0x49: "9", 0x4A: "-", 0x4B: "4", 0x4C: "5",
                0x4D: "6", 0x4F: "1", 0x50: "2", 0x51: "3", 0x52: "0", 0x53: "."})
FIN = {0x1C, 0x0F}      # Entrée, Tab


def reglages():
    return config.conf["piedCoulisse"]


def dossier_mesures():
    choisi = reglages()["dossier"].strip()
    if choisi:
        return choisi
    # Documents de l'utilisateur, même redirigé vers OneDrive
    # Translators: name of the folder created in Documents for the measurements file.
    return os.path.join(wx.StandardPaths.Get().GetDocumentsDir(), _("Caliper measurements"))


def fichier_mesures():
    # Translators: name of the measurements file.
    return os.path.join(dossier_mesures(), _("measurements.txt"))


def nombre_local(nombre):
    """« -0.5 » avec le séparateur décimal de la langue de NVDA."""
    # Translators: decimal separator used to speak and copy measurements.
    return nombre.replace(".", _("."))


def en_mots(texte):
    m = re.search(r"-?\d+(?:[.,]\d+)?", texte)
    if not m:
        return texte, None, None
    nombre = m.group().replace(",", ".")
    pouces = texte[m.end():].strip().lower().startswith(("in", '"'))
    unite = "in" if pouces else "mm"
    valeur = float(nombre)
    if valeur == 0:
        # Translators: spoken when the caliper sends 0.
        return _("zero"), nombre, unite
    # Singulier : en français sous 2 (« 1,5 millimètre »), ailleurs pour 1 seul.
    if languageHandler.getLanguage().startswith("fr"):
        singulier = abs(valeur) < 2
    else:
        singulier = abs(valeur) == 1
    lu = nombre_local(nombre.lstrip("-"))
    if pouces:
        # Translators: a measurement in inches, {n} is the number.
        mots = (_("{n} inch") if singulier else _("{n} inches")).format(n=lu)
    else:
        # Translators: a measurement in millimeters, {n} is the number.
        mots = (_("{n} millimeter") if singulier else _("{n} millimeters")).format(n=lu)
    if valeur < 0:
        # Translators: a negative measurement, {m} is e.g. "0.5 millimeters".
        mots = _("minus {m}").format(m=mots)
    return mots, nombre, unite


def ecrire(chemin, ligne):
    try:
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(ligne + "\n")
        return True
    except Exception:
        log.debugWarning("piedCoulisse : écriture impossible dans %s" % chemin, exc_info=True)
        return False


class PanneauPied(gui.settingsDialogs.SettingsPanel):
    # Translators: title of the settings category, and of the input gestures category.
    title = _("Caliper")

    def makeSettings(self, settingsSizer):
        aide = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        r = reglages()
        self.annoncer = aide.addItem(wx.CheckBox(
            # Translators: checkbox in the settings panel.
            self, label=_("&Announce when the caliper connects or disconnects")))
        self.annoncer.SetValue(r["annoncer"])
        self.enregistrer = aide.addItem(wx.CheckBox(
            # Translators: checkbox in the settings panel.
            self, label=_("&Save measurements to a file")))
        self.enregistrer.SetValue(r["enregistrer"])
        # Translators: label of the folder chooser in the settings panel.
        groupe = wx.StaticBoxSizer(wx.VERTICAL, self, label=_("Measurements file &folder"))
        aideGroupe = aide.addItem(guiHelper.BoxSizerHelper(self, sizer=groupe))
        choix = aideGroupe.addItem(guiHelper.PathSelectionHelper(
            # Translators: browse button, and title of the folder dialog.
            groupe.GetStaticBox(), _("&Browse..."), _("Choose the measurements folder")))
        self.dossier = choix.pathControl
        self.dossier.SetValue(dossier_mesures())
        self.copier = aide.addItem(wx.CheckBox(
            # Translators: checkbox in the settings panel.
            self, label=_("&Copy each measurement to the clipboard")))
        self.copier.SetValue(r["copier"])
        self.journal = aide.addItem(wx.CheckBox(
            # Translators: checkbox in the settings panel.
            self, label=_("&Log received keys (troubleshooting)")))
        self.journal.SetValue(r["journal"])

    def onSave(self):
        r = reglages()
        r["annoncer"] = self.annoncer.GetValue()
        r["enregistrer"] = self.enregistrer.GetValue()
        r["dossier"] = self.dossier.GetValue().strip()
        r["copier"] = self.copier.GetValue()
        r["journal"] = self.journal.GetValue()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = PanneauPied.title

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._capture = False
        self._tampon = ""
        self._touches = []
        self._silence = None
        self._limite = None
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(PanneauPied)
        self._fin_veille = threading.Event()
        # Fil à part : une requête à Windows ne doit jamais pouvoir figer NVDA.
        threading.Thread(target=self._veiller, name="piedCoulisse", daemon=True).start()

    def terminate(self, *args, **kwargs):
        self._fin_veille.set()
        self._arreter()
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(PanneauPied)
        except ValueError:
            pass
        super().terminate(*args, **kwargs)

    def _veiller(self):
        annonce = None      # dernier état annoncé (None : rien annoncé encore)
        vu, depuis = None, time.monotonic()
        while not self._fin_veille.wait(VEILLE_S):
            connecte = _liaisonPied.pied_connecte()
            if connecte != vu:
                vu, depuis = connecte, time.monotonic()
            elif connecte != annonce and time.monotonic() - depuis >= STABLE_S:
                if annonce is not None or connecte:   # au démarrage, on ne dit que « connecté »
                    wx.CallAfter(self._annoncer, connecte)
                annonce = connecte

    def _annoncer(self, connecte):
        if reglages()["annoncer"]:
            # Translators: spoken when the Bluetooth link of the caliper comes up or goes down.
            ui.message(_("Caliper connected") if connecte else _("Caliper disconnected"))

    def getScript(self, gesture):
        if self._capture and isinstance(gesture, keyboardHandler.KeyboardInputGesture):
            return self._script_capture
        return super().getScript(gesture)

    @script(
        # Translators: description of the F24 key in the input gestures dialog.
        description=_("Start of a caliper measurement (F24 key sent by the caliper)"),
        gesture="kb:f24",
    )
    def script_debut(self, gesture):
        self._arreter()
        self._capture = True
        self._tampon = ""
        self._touches = ["F24"]
        self._silence = wx.CallLater(SILENCE_MS, self._fin)
        self._limite = wx.CallLater(DUREE_MAX_MS, self._fin)

    @script(
        # Translators: description of the command in the input gestures dialog.
        description=_("Report the caliper battery level"),
    )
    def script_pile(self, gesture):
        pile = _liaisonPied.pile()
        if pile is None:
            # Translators: spoken when Windows does not know the battery level.
            ui.message(_("Caliper battery level unknown"))
            return
        niveau, connecte = pile
        if connecte:
            # Translators: spoken battery level, {n} is a percentage.
            ui.message(_("Caliper battery {n} percent").format(n=niveau))
        else:
            # Translators: spoken when the caliper is disconnected: the level may be out of date.
            ui.message(_("Caliper disconnected, last known battery level {n} percent").format(n=niveau))

    def _script_capture(self, gesture):
        sc = gesture.scanCode
        etendue = gesture.isExtended
        self._touches.append("%02x%s" % (sc, "e" if etendue else ""))
        if sc in FIN:
            self._fin()
            return
        if not etendue and sc in TOUCHES:
            self._tampon += TOUCHES[sc]
        if self._silence:
            self._silence.Restart(SILENCE_MS)

    def _arreter(self):
        self._capture = False
        for minuterie in (self._silence, self._limite):
            if minuterie:
                minuterie.Stop()
        self._silence = self._limite = None

    def _fin(self):
        if not self._capture:
            return
        self._arreter()
        r = reglages()
        texte = self._tampon.strip()
        maintenant = datetime.now()
        if r["journal"]:
            # Translators: name of the troubleshooting log subfolder.
            ecrire(os.path.join(dossier_mesures(), _("logs"),
                                "pied_nvda_%s.log" % maintenant.strftime("%Y%m%d")),
                   "%s touches %s -> %r" % (maintenant.strftime("%Y-%m-%d %H:%M:%S"),
                                             " ".join(self._touches), texte))
        if not texte:
            return
        mots, nombre, unite = en_mots(texte)
        if nombre is not None:
            if r["copier"]:
                api.copyToClip(nombre_local(nombre))
            # Translators: last column of each line of the measurements file.
            if r["enregistrer"] and not ecrire(fichier_mesures(), "%s\t%s\t%s\t%s" % (
                    maintenant.strftime("%Y-%m-%d %H:%M:%S"), nombre, unite, _("caliper"))):
                # Translators: added after the spoken measurement when the file cannot be written.
                mots = _("{m}, measurements file not writable").format(m=mots)
        ui.message(mots)
