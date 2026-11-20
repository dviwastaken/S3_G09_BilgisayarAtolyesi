import json
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from veritabani import DURUMLAR, CIHAZ_TURLERI

AYAR_DOSYASI = Path(__file__).with_name("ayarlar.json")
DUSUK_STOK = 3

_ARAMA_TABLOSU = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
    "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c"})


class FormHatasi(ValueError):
    pass


def palet(koyu):
    if koyu:
        return {"zemin": "#17181A", "panel": "#1E2022", "cizgi": "#303438",
                "giris": "#4A4F55", "metin": "#E6E7E9", "soluk": "#8B9097",
                "vurgu": "#0F766E", "vurgu_h": "#14958B", "vurgu_yazi": "#2DD4BF",
                "secili": "#1C2B2A", "hover": "#25282B", "tehlike": "#F87171",
                "durum": {"Bekliyor": "#9AA0A6", "İşlemde": "#E0A030",
                          "Tamamlandı": "#6EA8FE", "Teslim edildi": "#4CAF74"},
                "stok": {"tukendi": "#F87171", "az": "#E0A030",
                         "yeterli": "#4CAF74"}}
    return {"zemin": "#FFFFFF", "panel": "#FFFFFF", "cizgi": "#E2E2E2",
            "giris": "#D4D4D4", "metin": "#222222", "soluk": "#777777",
            "vurgu": "#0F766E", "vurgu_h": "#0B5F58", "vurgu_yazi": "#0F766E",
            "secili": "#F0F7F6", "hover": "#F6F6F6", "tehlike": "#B42318",
            "durum": {"Bekliyor": "#6B7280", "İşlemde": "#9A5B00",
                      "Tamamlandı": "#0F5FA8", "Teslim edildi": "#1E7B34"},
            "stok": {"tukendi": "#B42318", "az": "#9A5B00", "yeterli": "#1E7B34"}}


def stil(p):
    return f"""
QMainWindow, QDialog, QMessageBox {{ background: {p['zemin']}; }}
QWidget {{ color: {p['metin']}; }}
QWidget#ust, QWidget#detay {{ background: {p['zemin']}; }}
QWidget#sol {{ background: {p['panel']}; }}
QWidget#satir {{ background: transparent; }}
QLabel {{ background: transparent; }}
QFrame#cizgi {{ background: {p['cizgi']}; border: 0; }}
QLineEdit#arama {{ border: 1px solid {p['giris']}; border-radius: 4px;
    padding: 5px 8px; background: {p['panel']}; }}
QLineEdit#kutu, QComboBox#kutu {{ border: 1px solid {p['giris']};
    border-radius: 4px; padding: 4px 8px; background: {p['panel']}; }}
QLineEdit#alan, QComboBox#alan {{ border: 0; border-bottom: 1px solid {p['giris']};
    padding: 5px 2px; background: transparent; }}
QComboBox QAbstractItemView {{ background: {p['panel']}; color: {p['metin']};
    border: 1px solid {p['cizgi']}; outline: 0;
    selection-background-color: {p['secili']}; selection-color: {p['metin']}; }}
QPushButton {{ background: transparent; border: 1px solid {p['giris']};
    border-radius: 5px; padding: 0 14px; min-height: 30px; }}
QPushButton:hover {{ background: {p['hover']}; }}
QPushButton#birincil {{ background: {p['vurgu']}; color: white; border: 0;
    padding: 0 16px; }}
QPushButton#birincil:hover {{ background: {p['vurgu_h']}; }}
QPushButton#tehlike {{ color: {p['tehlike']}; }}
QPushButton#gezinti {{ border: 0; padding: 4px 10px; min-height: 26px;
    color: {p['soluk']}; background: transparent; }}
QPushButton#gezinti:hover {{ background: {p['hover']}; }}
QPushButton#gezinti[aktif="true"] {{ color: {p['vurgu_yazi']}; font-weight: 700; }}
QListWidget#liste {{ border: 0; background: {p['panel']}; outline: 0; }}
QListWidget#liste::item {{ border-bottom: 1px solid {p['cizgi']};
    border-left: 3px solid transparent; }}
QListWidget#liste::item:selected {{ background: {p['secili']};
    border-left: 3px solid {p['vurgu']}; }}
QTableWidget#kalemler {{ background: {p['zemin']}; border: 0;
    selection-background-color: {p['secili']}; selection-color: {p['metin']}; }}
QTableWidget#kalemler::item {{ padding: 0 8px; border-bottom: 1px solid {p['cizgi']}; }}
QHeaderView {{ background: {p['zemin']}; border: 0; }}
QTableCornerButton::section {{ background: {p['zemin']}; border: 0; }}
QHeaderView::section {{ background: transparent; color: {p['soluk']}; border: 0;
    border-bottom: 1px solid {p['cizgi']}; padding: 5px 8px; font-weight: 400; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p['giris']}; border-radius: 5px;
    min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px;
    border: 1px solid {p['giris']}; background: {p['panel']}; }}
QCheckBox::indicator:checked {{ background: {p['vurgu']}; border: 1px solid {p['vurgu']}; }}
"""


def bilgi(baslik, metin):
    QMessageBox.information(None, baslik, metin)


def uyari(baslik, metin):
    QMessageBox.warning(None, baslik, metin)


def hata(baslik, metin):
    QMessageBox.critical(None, baslik, metin)


def onay(baslik, metin):
    return QMessageBox.question(None, baslik, metin) == QMessageBox.Yes


def goster(deger):
    return "" if deger is None else str(deger)


def tl(deger):
    metin = f"{float(deger):,.2f}".replace(",", "_").replace(".", ",")
    return metin.replace("_", ".") + " TL"


def ondalik_goster(deger):
    return f"{float(deger):.2f}".replace(".", ",")


def ondalik_oku(ham, etiket):
    metin = ham.strip().replace(" ", "")
    if "," in metin:
        metin = metin.replace(".", "").replace(",", ".")
    try:
        return float(metin)
    except ValueError:
        raise FormHatasi(f"“{etiket}” için geçerli bir sayı girin.") from None


def tam_sayi_oku(ham, etiket):
    try:
        return int(ham.strip())
    except ValueError:
        raise FormHatasi(f"“{etiket}” için geçerli bir tam sayı girin.") from None


def katla(metin):
    return goster(metin).translate(_ARAMA_TABLOSU).lower()


def hata_metni(neden):
    metin = str(neden)
    if "FOREIGN KEY" in metin:
        return ("Bu kayıt başka kayıtlarla ilişkili olduğu için işlem "
                "yapılamadı (önce bağlı kayıtları silin/değiştirin).")
    if "NOT NULL" in metin:
        return "Zorunlu bir alan boş bırakılmış."
    if "CHECK" in metin:
        return "Girilen değer izin verilen aralığın dışında."
    if "UNIQUE" in metin:
        return "Bu kayıt zaten var."
    return metin


def guvenli(islem, durum_yaz=None, basari=None):
    try:
        islem()
    except NotImplementedError as neden:
        bilgi("Henüz hazır değil", str(neden))
        return False
    except ValueError as neden:
        uyari("Girişi kontrol edin", str(neden))
        return False
    except sqlite3.IntegrityError as neden:
        hata("Veritabanı kısıtı", hata_metni(neden))
        return False
    except sqlite3.Error as neden:
        hata("Veritabanı hatası", str(neden))
        return False
    if basari and durum_yaz:
        durum_yaz(basari)
    return True


def ayar_oku():
    try:
        return bool(json.loads(AYAR_DOSYASI.read_text(encoding="utf-8")).get("koyu"))
    except (OSError, ValueError):
        return False


def ayar_yaz(koyu):
    try:
        AYAR_DOSYASI.write_text(json.dumps({"koyu": koyu}), encoding="utf-8")
    except OSError:
        pass


def uygulama_olustur(argumanlar):
    uygulama = QApplication.instance() or QApplication(argumanlar)
    uygulama.setStyle("Fusion")
    uygulama.setFont(QFont("Segoe UI", 10))
    return uygulama


def cizgi():
    c = QFrame()
    c.setObjectName("cizgi")
    c.setFixedHeight(1)
    return c


def dikey_cizgi():
    c = QFrame()
    c.setObjectName("cizgi")
    c.setFixedWidth(1)
    return c


def dugme(metin, komut, tur=None):
    d = QPushButton(metin)
    d.setCursor(Qt.PointingHandCursor)
    if tur:
        d.setObjectName(tur)
    d.clicked.connect(lambda _=False: komut())
    return d


def kalin(metin, boyut=None):
    e = QLabel(metin)
    e.setStyleSheet(f"font-weight: 700;{f'font-size: {boyut}px;' if boyut else ''}")
    return e


class Liste(QListWidget):
    def __init__(self, secildi, palet_al):
        super().__init__()
        self.setObjectName("liste")
        self.secildi = secildi
        self.palet_al = palet_al
        self.ogeler = {}
        self._sessiz = False
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.currentItemChanged.connect(self._degisti)

    def cocuklar(self):
        return list(self.ogeler)

    def etiketli(self, etiket):
        return [i for i, (_, e) in self.ogeler.items() if e == etiket]

    def doldur(self, ogeler):
        self._sessiz = True
        self.clear()
        self.ogeler.clear()
        p = self.palet_al()
        for o in ogeler:
            self._ekle(o, p)
        self._sessiz = False

    def _ekle(self, o, p):
        oge = QListWidgetItem()
        oge.setData(Qt.UserRole, o["iid"])
        satir = QWidget()
        satir.setObjectName("satir")
        satir.setAttribute(Qt.WA_TransparentForMouseEvents)
        yerlesim = QVBoxLayout(satir)
        yerlesim.setContentsMargins(12, 8, 12, 8)
        yerlesim.setSpacing(2)
        ust = QHBoxLayout()
        baslik = QLabel(o["baslik"])
        baslik.setStyleSheet("font-weight: 600;")
        sag = QLabel(o["sag"])
        sag.setStyleSheet(f"color: {p['soluk']};")
        ust.addWidget(baslik)
        ust.addStretch(1)
        ust.addWidget(sag)
        yerlesim.addLayout(ust)
        nokta = ""
        if o["renk"]:
            renk = p[o["renk"][0]][o["renk"][1]]
            nokta = f'<span style="color: {renk};">●</span> '
        alt = QLabel(nokta + o["alt"])
        alt.setStyleSheet(f"color: {p['soluk']}; font-size: 12px;")
        yerlesim.addWidget(alt)
        oge.setSizeHint(satir.sizeHint())
        self.addItem(oge)
        self.setItemWidget(oge, satir)
        self.ogeler[o["iid"]] = (oge, o["etiket"])

    def _degisti(self, yeni, _eski):
        if not self._sessiz and yeni is not None:
            self.secildi(yeni.data(Qt.UserRole))

    def sec(self, iid, bildir=True):
        self._sessiz = True
        if iid in self.ogeler:
            self.setCurrentItem(self.ogeler[iid][0])
        else:
            self.clearSelection()
            self.setCurrentRow(-1)
        self._sessiz = False
        if bildir:
            self.secildi(iid if iid in self.ogeler else None)


class CrudSekmesi(QWidget):
    def __init__(self, ad, servis, alanlar, liste_ogesi, durum_yaz, palet_al):
        super().__init__()
        self.ad, self.servis = ad, servis
        self.alanlar, self.liste_ogesi = alanlar, liste_ogesi
        self.durum_yaz, self.palet_al = durum_yaz, palet_al
        self.satirlar = {}
        self.tum_satirlar = []
        self.araclar = {}
        self.secenek_haritasi = {}
        self.secili_id = None
        yerlesim = QHBoxLayout(self)
        yerlesim.setContentsMargins(0, 0, 0, 0)
        yerlesim.setSpacing(0)
        self._detay_kur()
        yerlesim.addWidget(self._liste_kur())
        yerlesim.addWidget(dikey_cizgi())
        yerlesim.addWidget(self.detay, 1)
        self._ek_panel_kur()
        self.arama.textChanged.connect(lambda _: self._listeyi_doldur())
        self.yenile()

    def _liste_kur(self):
        kap = QWidget()
        kap.setObjectName("sol")
        kap.setFixedWidth(330)
        yerlesim = QVBoxLayout(kap)
        yerlesim.setContentsMargins(0, 12, 0, 0)
        yerlesim.setSpacing(6)
        ust = QHBoxLayout()
        ust.setContentsMargins(12, 0, 12, 0)
        self.arama = QLineEdit()
        self.arama.setObjectName("arama")
        self.arama.setPlaceholderText("Ara")
        self.sayac = QLabel("")
        ust.addWidget(self.arama, 1)
        ust.addWidget(self.sayac)
        yerlesim.addLayout(ust)
        self.suzgec = QHBoxLayout()
        self.suzgec.setContentsMargins(12, 0, 12, 0)
        self._arac_cubugu_ek(self.suzgec)
        yerlesim.addLayout(self.suzgec)
        self.liste = Liste(self._secim_degisti, self.palet_al)
        yerlesim.addWidget(self.liste, 1)
        return kap

    def _detay_kur(self):
        self.detay = QWidget()
        self.detay.setObjectName("detay")
        yerlesim = QVBoxLayout(self.detay)
        yerlesim.setContentsMargins(26, 18, 26, 16)
        yerlesim.setSpacing(10)
        baslik = QHBoxLayout()
        self.baslik_etiketi = kalin("", 19)
        self.rozet = QLabel("")
        baslik.addWidget(self.baslik_etiketi)
        baslik.addStretch(1)
        baslik.addWidget(self.rozet)
        yerlesim.addLayout(baslik)
        self.alt_etiketi = QLabel("")
        yerlesim.addWidget(self.alt_etiketi)

        form = QGridLayout()
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(4)
        for i, a in enumerate(self.alanlar):
            satir, sutun = divmod(i, 2)
            etiket = QLabel(a["etiket"])
            etiket.setObjectName("soluk")
            if a["tur"] in ("secim", "id_secim"):
                w = QComboBox()
                w.setCurrentIndex(-1)
            else:
                w = QLineEdit()
            w.setObjectName("alan")
            form.addWidget(etiket, 2 * satir, sutun)
            form.addWidget(w, 2 * satir + 1, sutun)
            form.setRowMinimumHeight(2 * satir + 1, 36)
            self.araclar[a["anahtar"]] = w
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)
        yerlesim.addLayout(form)

        self.dugme_cubugu = QHBoxLayout()
        self.dugme_cubugu.setSpacing(8)
        for metin, komut, tur in (("Ekle", self.ekle, "birincil"),
                                  ("Güncelle", self.guncelle, None),
                                  ("Sil", self.sil, "tehlike"),
                                  ("Temizle", self.temizle, None)):
            self.dugme_cubugu.addWidget(dugme(metin, komut, tur))
        self.dugme_cubugu.addStretch(1)
        yerlesim.addLayout(self.dugme_cubugu)
        self.detay_yerlesim = yerlesim

    def _arac_cubugu_ek(self, yerlesim):
        pass

    def _ek_panel_kur(self):
        self.detay_yerlesim.addStretch(1)

    def form_yaz(self, anahtar, metin):
        w = self.araclar[anahtar]
        if isinstance(w, QComboBox):
            indeks = w.findText(metin) if metin else -1
            w.setCurrentIndex(indeks)
        else:
            w.setText(metin)

    def form_oku(self, anahtar):
        w = self.araclar[anahtar]
        return (w.currentText() if isinstance(w, QComboBox) else w.text()).strip()

    def _baslik_guncelle(self):
        p = self.palet_al()
        satir = self.satirlar.get(str(self.secili_id))
        if satir is None:
            self.baslik_etiketi.setText(f"Yeni {self.ad.lower()}")
            self.alt_etiketi.setText("Bilgileri girip Ekle'ye basın.")
            self.rozet.setText("")
        else:
            oge = self.liste_ogesi(satir)
            self.baslik_etiketi.setText(oge["baslik"])
            self.alt_etiketi.setText(oge["alt"])
            renk = p[oge["renk"][0]][oge["renk"][1]] if oge["renk"] else p["metin"]
            self.rozet.setText(f'<span style="color: {renk};">{oge.get("rozet", "")}</span>')
        self.alt_etiketi.setStyleSheet(f"color: {p['soluk']};")
        for etiket in self.detay.findChildren(QLabel, "soluk"):
            etiket.setStyleSheet(f"color: {p['soluk']}; font-size: 12px;")

    def yenile(self):
        for a in self.alanlar:
            w = self.araclar[a["anahtar"]]
            if a["tur"] not in ("secim", "id_secim"):
                continue
            onceki = w.currentText()
            if a["tur"] == "secim":
                secenekler = list(a["secenekler"])
            else:
                ciftler = a["secenekler"]()
                self.secenek_haritasi[a["anahtar"]] = {m: i for i, m in ciftler}
                secenekler = [m for _, m in ciftler]
            w.blockSignals(True)
            w.clear()
            w.addItems(secenekler)
            w.setCurrentIndex(w.findText(onceki) if onceki else -1)
            w.blockSignals(False)
        self.tum_satirlar = list(self.servis.listele())
        self._listeyi_doldur()

    def _uygun_mu(self, satir):
        aranan = katla(self.arama.text().strip())
        if not aranan:
            return True
        return any(aranan in katla(satir[k]) for k in satir.keys())

    def _listeyi_doldur(self):
        onceki = self.secili_id
        satirlar = [s for s in self.tum_satirlar if self._uygun_mu(s)]
        self.satirlar = {str(s["id"]): s for s in satirlar}
        self.liste.doldur([dict(self.liste_ogesi(s), iid=str(s["id"]))
                           for s in satirlar])
        self.sayac.setText(f"{len(satirlar)} / {len(self.tum_satirlar)}")
        if onceki is not None and str(onceki) in self.satirlar:
            self.liste.sec(str(onceki), bildir=False)
        else:
            self.secili_id = None
        self._baslik_guncelle()

    def _secim_degisti(self, iid):
        if iid is None:
            return
        satir = self.satirlar[iid]
        self.secili_id = satir["id"]
        for a in self.alanlar:
            anahtar, deger = a["anahtar"], satir[a["anahtar"]]
            if a["tur"] == "id_secim":
                tersi = {i: m for m, i in self.secenek_haritasi[anahtar].items()}
                self.form_yaz(anahtar, tersi.get(deger, ""))
            elif a["tur"] == "ondalik":
                self.form_yaz(anahtar, ondalik_goster(deger))
            else:
                self.form_yaz(anahtar, goster(deger))
        self._baslik_guncelle()
        self.secildi()

    def secildi(self):
        pass

    def temizle(self):
        for a in self.alanlar:
            self.form_yaz(a["anahtar"], "")
        self.liste.sec(None, bildir=False)
        self.secili_id = None
        self._baslik_guncelle()
        self.secildi()

    def _degerleri_oku(self):
        degerler = {}
        for a in self.alanlar:
            ham = self.form_oku(a["anahtar"])
            tur, etiket = a["tur"], a["etiket"]
            if tur == "sayi":
                degerler[a["anahtar"]] = tam_sayi_oku(ham, etiket)
            elif tur == "ondalik":
                degerler[a["anahtar"]] = ondalik_oku(ham, etiket)
            elif tur == "id_secim":
                id_ = self.secenek_haritasi[a["anahtar"]].get(ham)
                if id_ is None:
                    raise FormHatasi(f"“{etiket}” seçin.")
                degerler[a["anahtar"]] = id_
            else:
                degerler[a["anahtar"]] = ham
        return degerler

    def ekle(self):
        if guvenli(lambda: self.servis.ekle(**self._degerleri_oku()),
                   self.durum_yaz, f"{self.ad} eklendi."):
            self.temizle()
            self.yenile()

    def guncelle(self):
        if self.secili_id is None:
            bilgi("Bilgi", "Önce listeden bir kayıt seçin.")
            return
        if guvenli(lambda: self.servis.guncelle(
                self.secili_id, **self._degerleri_oku()),
                self.durum_yaz, f"{self.ad} güncellendi."):
            self.yenile()

    def sil(self):
        if self.secili_id is None:
            bilgi("Bilgi", "Önce listeden bir kayıt seçin.")
            return
        if not onay("Onay", f"Seçili {self.ad.lower()} kaydı silinsin mi?"):
            return
        if guvenli(lambda: self.servis.sil(self.secili_id),
                   self.durum_yaz, f"{self.ad} silindi."):
            self.temizle()
            self.yenile()


class IsEmriSekmesi(CrudSekmesi):
    def __init__(self, parca_servisi, **kwargs):
        self.parca_servisi = parca_servisi
        self.parca_haritasi = {}
        super().__init__(**kwargs)

    def _arac_cubugu_ek(self, yerlesim):
        yerlesim.addWidget(QLabel("Durum"))
        self.durum_filtre = QComboBox()
        self.durum_filtre.setObjectName("kutu")
        self.durum_filtre.addItems(["Tümü", *DURUMLAR])
        self.durum_filtre.currentIndexChanged.connect(
            lambda _: self._listeyi_doldur())
        yerlesim.addWidget(self.durum_filtre, 1)

    def _uygun_mu(self, satir):
        filtre = self.durum_filtre.currentText()
        if filtre != "Tümü" and satir["durum"] != filtre:
            return False
        return super()._uygun_mu(satir)

    def _ek_panel_kur(self):
        self.dugme_cubugu.insertWidget(
            self.dugme_cubugu.count() - 1,
            dugme("Sonraki duruma geç", self.durum_ilerlet))
        yerlesim = self.detay_yerlesim
        yerlesim.addWidget(cizgi())
        soluk = QLabel("Kullanılan parçalar")
        soluk.setObjectName("soluk")
        yerlesim.addWidget(soluk)

        self.kalem_tablosu = QTableWidget(0, 4)
        self.kalem_tablosu.setObjectName("kalemler")
        self.kalem_tablosu.setHorizontalHeaderLabels(
            ["No", "Parça", "Adet", "Birim fiyat"])
        self.kalem_tablosu.verticalHeader().hide()
        self.kalem_tablosu.setShowGrid(False)
        self.kalem_tablosu.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.kalem_tablosu.setSelectionMode(QAbstractItemView.SingleSelection)
        self.kalem_tablosu.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.kalem_tablosu.setFocusPolicy(Qt.NoFocus)
        baslik = self.kalem_tablosu.horizontalHeader()
        baslik.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        baslik.setSectionResizeMode(1, QHeaderView.Stretch)
        for sutun, genislik in ((0, 50), (2, 80), (3, 130)):
            self.kalem_tablosu.setColumnWidth(sutun, genislik)
        self.kalem_tablosu.setFixedHeight(130)
        self.kalem_tablosu.itemSelectionChanged.connect(self._kalem_secildi)
        yerlesim.addWidget(self.kalem_tablosu)

        satir = QHBoxLayout()
        satir.setSpacing(8)
        self.parca_kutu = QComboBox()
        self.parca_kutu.setObjectName("kutu")
        self.parca_kutu.setMinimumWidth(260)
        self.adet_girisi = QLineEdit("1")
        self.adet_girisi.setObjectName("kutu")
        self.adet_girisi.setFixedWidth(60)
        satir.addWidget(self.parca_kutu)
        satir.addWidget(self.adet_girisi)
        for metin, komut, tur in (("Ekle", self.parca_ekle, "birincil"),
                                  ("Adedi ayarla", self.adet_ayarla, None),
                                  ("Çıkar", self.parca_cikar, "tehlike")):
            satir.addWidget(dugme(metin, komut, tur))
        satir.addStretch(1)
        yerlesim.addLayout(satir)

        yerlesim.addWidget(cizgi())
        toplam = QHBoxLayout()
        etiket = QLabel("Toplam maliyet")
        etiket.setObjectName("soluk")
        self.maliyet_etiketi = kalin("—", 16)
        toplam.addWidget(etiket)
        toplam.addStretch(1)
        toplam.addWidget(self.maliyet_etiketi)
        yerlesim.addLayout(toplam)
        yerlesim.addStretch(1)

    def yenile(self):
        super().yenile()
        self._parca_secenekleri()
        self._kalemleri_listele()

    def secildi(self):
        self._kalemleri_listele()

    def _parca_secenekleri(self):
        self.parca_haritasi = {
            f"#{p['id']} {p['ad']} (stok: {p['stok']})": p["id"]
            for p in self.parca_servisi.listele()}
        onceki = self.parca_kutu.currentText()
        self.parca_kutu.clear()
        self.parca_kutu.addItems(list(self.parca_haritasi))
        self.parca_kutu.setCurrentIndex(
            self.parca_kutu.findText(onceki) if onceki else -1)

    def _kalemleri_listele(self):
        onceki = self.kalem_secili()
        self.kalem_tablosu.blockSignals(True)
        self.kalem_tablosu.setRowCount(0)
        self.maliyet_etiketi.setText("—")
        if self.secili_id is not None:
            for p in self.servis.parcalari_listele(self.secili_id):
                sira = self.kalem_tablosu.rowCount()
                self.kalem_tablosu.insertRow(sira)
                self.kalem_tablosu.setRowHeight(sira, 30)
                for sutun, deger in enumerate(
                        (p["parca_id"], p["ad"], p["adet"], tl(p["birim_fiyat"]))):
                    oge = QTableWidgetItem(str(deger))
                    if sutun == 3:
                        oge.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.kalem_tablosu.setItem(sira, sutun, oge)
                if p["parca_id"] == onceki:
                    self.kalem_tablosu.selectRow(sira)
        self.kalem_tablosu.blockSignals(False)
        if self.secili_id is None:
            return
        try:
            toplam = self.servis.toplam_maliyet(self.secili_id)
        except NotImplementedError:
            return
        self.maliyet_etiketi.setText(tl(toplam))

    def kalem_secili(self):
        sira = self.kalem_tablosu.currentRow()
        if sira < 0 or not self.kalem_tablosu.selectedItems():
            return None
        return int(self.kalem_tablosu.item(sira, 0).text())

    def kalem_sec(self, parca_id):
        for sira in range(self.kalem_tablosu.rowCount()):
            if int(self.kalem_tablosu.item(sira, 0).text()) == parca_id:
                self.kalem_tablosu.selectRow(sira)
                return

    def _kalem_secildi(self):
        parca_id = self.kalem_secili()
        if parca_id is None:
            return
        etiket = next((e for e, i in self.parca_haritasi.items() if i == parca_id), "")
        self.parca_kutu.setCurrentIndex(self.parca_kutu.findText(etiket))
        sira = self.kalem_tablosu.currentRow()
        self.adet_girisi.setText(self.kalem_tablosu.item(sira, 2).text())

    def _kalem_islemi(self, islem, basari):
        if self.secili_id is None:
            bilgi("Bilgi", "Önce bir iş emri seçin.")
            return
        if guvenli(islem, self.durum_yaz, basari):
            self._parca_secenekleri()
            self._kalemleri_listele()

    def parca_ekle(self):
        parca_id = self.parca_haritasi.get(self.parca_kutu.currentText())
        if parca_id is None:
            bilgi("Bilgi", "Bir parça seçin.")
            return
        self._kalem_islemi(lambda: self.servis.parca_ekle(
            self.secili_id, parca_id,
            tam_sayi_oku(self.adet_girisi.text(), "Adet")), "Parça eklendi.")

    def adet_ayarla(self):
        parca_id = self.kalem_secili()
        if parca_id is None:
            bilgi("Bilgi", "Listeden bir parça kalemi seçin.")
            return
        self._kalem_islemi(lambda: self.servis.parca_adet_ayarla(
            self.secili_id, parca_id,
            tam_sayi_oku(self.adet_girisi.text(), "Adet")), "Adet ayarlandı.")

    def parca_cikar(self):
        parca_id = self.kalem_secili()
        if parca_id is None:
            bilgi("Bilgi", "Listeden çıkarılacak parçayı seçin.")
            return
        self._kalem_islemi(lambda: self.servis.parca_cikar(
            self.secili_id, parca_id), "Parça çıkarıldı.")

    def durum_ilerlet(self):
        if self.secili_id is None:
            bilgi("Bilgi", "Önce bir iş emri seçin.")
            return
        if guvenli(lambda: self.servis.durum_ilerlet(self.secili_id),
                   self.durum_yaz, "Durum ilerletildi."):
            self.yenile()


def musteri_ogesi(satir):
    return {"baslik": f"#{satir['id']} {satir['ad_soyad']}",
            "alt": satir["telefon"] or satir["eposta"] or "İletişim bilgisi yok",
            "sag": "", "renk": None, "etiket": None}


def cihaz_ogesi(satir):
    ad = f"{goster(satir['marka'])} {goster(satir['model'])}".strip()
    return {"baslik": f"#{satir['id']} {ad or satir['tur']}",
            "alt": f"{satir['musteri']} · {satir['tur']}",
            "sag": goster(satir["seri_no"]), "renk": None, "etiket": None}


def is_emri_ogesi(satir):
    durum = satir["durum"]
    return {"baslik": f"#{satir['id']} {satir['musteri']}",
            "alt": f"{durum} · {satir['cihaz']}",
            "sag": tl(satir["iscilik_ucreti"]), "rozet": f"●  {durum}",
            "renk": ("durum", durum), "etiket": durum}


def parca_ogesi(satir):
    stok = satir["stok"]
    if stok <= 0:
        durum, anahtar = "Tükendi", "tukendi"
    elif stok <= DUSUK_STOK:
        durum, anahtar = "Az kaldı", "az"
    else:
        durum, anahtar = "Yeterli", "yeterli"
    return {"baslik": f"#{satir['id']} {satir['ad']}",
            "alt": f"{durum} · stok {stok}", "sag": tl(satir["birim_fiyat"]),
            "renk": ("stok", anahtar), "etiket": anahtar}


class Uygulama(QMainWindow):
    MODULLER = ("İş Emirleri", "Müşteriler", "Cihazlar", "Parça Stoğu")

    def __init__(self, servisler):
        super().__init__()
        self.servisler = servisler
        self.koyu = ayar_oku()
        self.aktif = self.MODULLER[0]
        self.setWindowTitle("ServisTakip - Bilgisayar Servisi Yönetim Sistemi")
        self.resize(1200, 780)
        self.setMinimumSize(1040, 700)

        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QVBoxLayout(merkez)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)
        ana.addWidget(self._ust_cubuk_kur())
        ana.addWidget(cizgi())
        self.yigin = QStackedWidget()
        ana.addWidget(self.yigin, 1)
        ana.addWidget(cizgi())
        self.durum_cubugu = QLabel("Hazır")
        self.durum_cubugu.setContentsMargins(16, 4, 16, 4)
        ana.addWidget(self.durum_cubugu)

        yapicilar = (self._is_emri_sekmesi, self._musteri_sekmesi,
                     self._cihaz_sekmesi, self._parca_sekmesi)
        self.sayfalar = {}
        for ad, yap in zip(self.MODULLER, yapicilar):
            sayfa = yap()
            self.yigin.addWidget(sayfa)
            self.sayfalar[ad] = sayfa
        QShortcut(QKeySequence("F5"), self, activated=self._yenile)
        self._stil_uygula()
        self.modul_ac(self.aktif)

    def palet(self):
        return palet(self.koyu)

    def _ust_cubuk_kur(self):
        cubuk = QWidget()
        cubuk.setObjectName("ust")
        yerlesim = QHBoxLayout(cubuk)
        yerlesim.setContentsMargins(20, 10, 20, 10)
        yerlesim.addWidget(kalin("ServisTakip", 15))
        yerlesim.addSpacing(20)
        self.gezinti = {}
        for ad in self.MODULLER:
            dugmesi = dugme(ad, lambda a=ad: self.modul_ac(a), "gezinti")
            yerlesim.addWidget(dugmesi)
            self.gezinti[ad] = dugmesi
        yerlesim.addStretch(1)
        self.koyu_kutusu = QCheckBox("Koyu mod")
        self.koyu_kutusu.setChecked(self.koyu)
        self.koyu_kutusu.toggled.connect(self._koyu_degisti)
        yerlesim.addWidget(self.koyu_kutusu)
        yerlesim.addSpacing(12)
        yerlesim.addWidget(dugme("Yeni kayıt", self._yeni, "birincil"))
        return cubuk

    def _stil_uygula(self):
        p = self.palet()
        QApplication.instance().setStyleSheet(stil(p))
        self.durum_cubugu.setStyleSheet(f"color: {p['soluk']}; font-size: 12px;")

    def _koyu_degisti(self, koyu):
        self.koyu = bool(koyu)
        ayar_yaz(self.koyu)
        self._stil_uygula()
        self.modul_ac(self.aktif)

    def aktif_sayfa(self):
        return self.sayfalar[self.aktif]

    def modul_ac(self, ad):
        self.aktif = ad
        for modul, dugmesi in self.gezinti.items():
            dugmesi.setProperty("aktif", modul == ad)
            dugmesi.style().unpolish(dugmesi)
            dugmesi.style().polish(dugmesi)
        self.yigin.setCurrentWidget(self.sayfalar[ad])
        self.sayfalar[ad].yenile()

    def _yeni(self):
        self.aktif_sayfa().temizle()

    def _yenile(self):
        self.aktif_sayfa().yenile()
        self.durum_yaz("Liste yenilendi.")

    def durum_yaz(self, metin):
        self.durum_cubugu.setText(metin)

    def _sayfa(self, sinif, **kwargs):
        return sinif(durum_yaz=self.durum_yaz, palet_al=self.palet, **kwargs)

    def _musteri_sekmesi(self):
        return self._sayfa(
            CrudSekmesi, ad="Müşteri", servis=self.servisler.musteri,
            alanlar=[
                {"anahtar": "ad_soyad", "etiket": "Ad soyad", "tur": "metin"},
                {"anahtar": "telefon", "etiket": "Telefon", "tur": "metin"},
                {"anahtar": "eposta", "etiket": "E-posta", "tur": "metin"}],
            liste_ogesi=musteri_ogesi)

    def _cihaz_sekmesi(self):
        musteriler = self.servisler.musteri
        return self._sayfa(
            CrudSekmesi, ad="Cihaz", servis=self.servisler.cihaz,
            alanlar=[
                {"anahtar": "musteri_id", "etiket": "Müşteri",
                 "tur": "id_secim",
                 "secenekler": lambda: [
                     (m["id"], f"#{m['id']} {m['ad_soyad']}")
                     for m in musteriler.listele()]},
                {"anahtar": "tur", "etiket": "Tür", "tur": "secim",
                 "secenekler": CIHAZ_TURLERI},
                {"anahtar": "marka", "etiket": "Marka", "tur": "metin"},
                {"anahtar": "model", "etiket": "Model", "tur": "metin"},
                {"anahtar": "seri_no", "etiket": "Seri no", "tur": "metin"}],
            liste_ogesi=cihaz_ogesi)

    def _is_emri_sekmesi(self):
        cihazlar = self.servisler.cihaz
        return self._sayfa(
            IsEmriSekmesi, parca_servisi=self.servisler.parca,
            ad="İş emri", servis=self.servisler.is_emri,
            alanlar=[
                {"anahtar": "cihaz_id", "etiket": "Cihaz", "tur": "id_secim",
                 "secenekler": lambda: [
                     (c["id"], f"#{c['id']} {c['musteri']} - "
                               f"{goster(c['marka'])} {goster(c['model'])}"
                               .rstrip(" -"))
                     for c in cihazlar.listele()]},
                {"anahtar": "durum", "etiket": "Durum", "tur": "secim",
                 "secenekler": DURUMLAR},
                {"anahtar": "aciklama", "etiket": "Açıklama", "tur": "metin"},
                {"anahtar": "iscilik_ucreti", "etiket": "İşçilik (TL)",
                 "tur": "ondalik"}],
            liste_ogesi=is_emri_ogesi)

    def _parca_sekmesi(self):
        return self._sayfa(
            CrudSekmesi, ad="Parça", servis=self.servisler.parca,
            alanlar=[
                {"anahtar": "ad", "etiket": "Parça adı", "tur": "metin"},
                {"anahtar": "birim_fiyat", "etiket": "Birim fiyat (TL)",
                 "tur": "ondalik"},
                {"anahtar": "stok", "etiket": "Stok adedi", "tur": "sayi"}],
            liste_ogesi=parca_ogesi)
