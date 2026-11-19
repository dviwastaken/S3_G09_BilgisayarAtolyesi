import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from veritabani import DURUMLAR, CIHAZ_TURLERI

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DUSUK_STOK = 3
DURUM_RENKLERI = {"Bekliyor": "#9aa0a6", "İşlemde": "#e5a823",
                  "Tamamlandı": "#4caf72", "Teslim edildi": "#5b9bd5"}
TUKENDI_RENK, AZ_RENK = "#ff5c5c", "#ff9f43"

_ARAMA_TABLOSU = str.maketrans({
    "İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
    "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c"})


class FormHatasi(ValueError):
    pass


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


def hata_metni(hata):
    metin = str(hata)
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
    except NotImplementedError as hata:
        messagebox.showinfo("Henüz hazır değil", str(hata))
        return False
    except ValueError as hata:
        messagebox.showwarning("Girişi kontrol edin", str(hata))
        return False
    except sqlite3.IntegrityError as hata:
        messagebox.showerror("Veritabanı kısıtı", hata_metni(hata))
        return False
    except sqlite3.Error as hata:
        messagebox.showerror("Veritabanı hatası", str(hata))
        return False
    if basari and durum_yaz:
        durum_yaz(basari)
    return True


def tablo_stilini_ayarla():
    stil = ttk.Style()
    stil.theme_use("clam")
    stil.configure("Treeview", background="#2b2b2b", fieldbackground="#2b2b2b",
                   foreground="#dce4ee", rowheight=28, borderwidth=0,
                   font=("Segoe UI", 10))
    stil.configure("Treeview.Heading", background="#3a3a3a",
                   foreground="#dce4ee", relief="flat",
                   font=("Segoe UI", 10, "bold"))
    stil.map("Treeview", background=[("selected", "#1f6aa5")],
             foreground=[("selected", "#ffffff")])
    stil.map("Treeview.Heading", background=[("active", "#4a4a4a")])


def agac_olustur(ust, kolonlar, yukseklik):
    cerceve = ctk.CTkFrame(ust)
    agac = ttk.Treeview(cerceve, columns=[k[0] for k in kolonlar],
                        show="headings", selectmode="browse",
                        height=yukseklik)
    for anahtar, baslik, genislik, *_ in kolonlar:
        agac.heading(anahtar, text=baslik)
        agac.column(anahtar, width=genislik, anchor="w")
    kaydirma = ctk.CTkScrollbar(cerceve, orientation="vertical",
                                command=agac.yview)
    agac.configure(yscrollcommand=kaydirma.set)
    agac.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
    kaydirma.pack(side="right", fill="y", padx=(0, 4), pady=6)
    return cerceve, agac


class CrudSekmesi(ctk.CTkFrame):
    def __init__(self, master, ad, servis, alanlar, kolonlar, durum_yaz,
                 satir_etiketi=None, tablo_yuksekligi=8):
        super().__init__(master, fg_color="transparent")
        self.ad, self.servis = ad, servis
        self.alanlar, self.kolonlar = alanlar, kolonlar
        self.durum_yaz = durum_yaz
        self.satir_etiketi = satir_etiketi
        self.tablo_yuksekligi = tablo_yuksekligi
        self.satirlar = {}
        self.tum_satirlar = []
        self.degiskenler = {}
        self.araclar = {}
        self.secenek_haritasi = {}
        self.secili_id = None
        self.siralama = (None, False)
        self.arama_var = tk.StringVar()
        self._form_kur()
        self._arac_cubugu_kur()
        self._tablo_kur()
        self._ek_panel_kur()
        self.arama_var.trace_add("write", lambda *_: self._listeyi_doldur())
        self.yenile()

    def _form_kur(self):
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=4, pady=(4, 0))
        ctk.CTkLabel(form, text=f"{self.ad} bilgileri",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 2))
        for i, a in enumerate(self.alanlar):
            satir, sutun = divmod(i, 2)
            satir += 1
            ctk.CTkLabel(form, text=a["etiket"]).grid(
                row=satir, column=sutun * 2, sticky="e", padx=(12, 6), pady=5)
            var = tk.StringVar()
            if a["tur"] in ("secim", "id_secim"):
                w = ctk.CTkComboBox(form, variable=var, state="readonly",
                                    values=[""], width=280)
            else:
                w = ctk.CTkEntry(form, textvariable=var, width=280)
            w.grid(row=satir, column=sutun * 2 + 1, sticky="w", padx=(0, 12),
                   pady=5)
            self.degiskenler[a["anahtar"]] = var
            self.araclar[a["anahtar"]] = w

        self.dugme_cubugu = ctk.CTkFrame(form, fg_color="transparent")
        self.dugme_cubugu.grid(row=(len(self.alanlar) + 1) // 2 + 1, column=0,
                               columnspan=4, pady=(8, 10))
        for metin, komut, renk in (
                ("Ekle", self.ekle, None),
                ("Güncelle", self.guncelle, None),
                ("Sil", self.sil, "#b03a3a"),
                ("Temizle", self.temizle, "gray40")):
            ctk.CTkButton(self.dugme_cubugu, text=metin, command=komut,
                          width=100, fg_color=renk).pack(side="left", padx=5)

    def _arac_cubugu_kur(self):
        cubuk = ctk.CTkFrame(self, fg_color="transparent")
        cubuk.pack(fill="x", padx=4, pady=(10, 0))
        ctk.CTkLabel(cubuk, text="Ara:").pack(side="left", padx=(8, 4))
        ctk.CTkEntry(cubuk, textvariable=self.arama_var, width=220,
                     placeholder_text="ad, telefon, marka...").pack(side="left")
        self.sayac = ctk.CTkLabel(cubuk, text="", text_color="gray60")
        self.sayac.pack(side="right", padx=8)
        self._arac_cubugu_ek(cubuk)

    def _arac_cubugu_ek(self, cerceve):
        pass

    def _tablo_kur(self):
        cerceve, self.agac = agac_olustur(self, self.kolonlar,
                                          self.tablo_yuksekligi)
        cerceve.pack(fill="both", expand=True, padx=4, pady=(4, 4))
        for anahtar, baslik, *_ in self.kolonlar:
            self.agac.heading(anahtar, text=baslik,
                              command=lambda k=anahtar: self._sirala(k))
        self.agac.tag_configure("tukendi", foreground=TUKENDI_RENK)
        self.agac.tag_configure("az", foreground=AZ_RENK)
        for durum, renk in DURUM_RENKLERI.items():
            self.agac.tag_configure(durum, foreground=renk)
        self.agac.bind("<<TreeviewSelect>>", self._secim_degisti)

    def _ek_panel_kur(self):
        pass

    def yenile(self):
        for a in self.alanlar:
            if a["tur"] == "secim":
                self.araclar[a["anahtar"]].configure(
                    values=list(a["secenekler"]))
            elif a["tur"] == "id_secim":
                ciftler = a["secenekler"]()
                self.secenek_haritasi[a["anahtar"]] = {m: i for i, m in ciftler}
                self.araclar[a["anahtar"]].configure(
                    values=[m for _, m in ciftler] or [""])
        self.tum_satirlar = list(self.servis.listele())
        self._listeyi_doldur()

    def _uygun_mu(self, satir):
        aranan = katla(self.arama_var.get().strip())
        if not aranan:
            return True
        return any(aranan in katla(satir[k[0]]) for k in self.kolonlar)

    def _listeyi_doldur(self):
        onceki = self.secili_id
        anahtar, ters = self.siralama
        satirlar = [s for s in self.tum_satirlar if self._uygun_mu(s)]
        if anahtar:
            satirlar.sort(key=lambda s: self._sira_anahtari(s[anahtar]),
                          reverse=ters)
        self.agac.delete(*self.agac.get_children())
        self.satirlar.clear()
        for satir in satirlar:
            iid = str(satir["id"])
            self.satirlar[iid] = satir
            degerler = [self._bicimle(k, satir[k[0]]) for k in self.kolonlar]
            etiket = self.satir_etiketi(satir) if self.satir_etiketi else None
            self.agac.insert("", "end", iid=iid, values=degerler,
                             tags=(etiket,) if etiket else ())
        self.sayac.configure(
            text=f"{len(satirlar)} / {len(self.tum_satirlar)} kayıt")
        if onceki is not None and str(onceki) in self.satirlar:
            self.agac.selection_set(str(onceki))
        else:
            self.secili_id = None

    @staticmethod
    def _sira_anahtari(deger):
        if deger is None:
            return (1, 0)
        if isinstance(deger, (int, float)):
            return (0, deger)
        return (0, katla(deger))

    def _sirala(self, anahtar):
        eski, ters = self.siralama
        self.siralama = (anahtar, (not ters) if eski == anahtar else False)
        self._listeyi_doldur()

    @staticmethod
    def _bicimle(kolon, deger):
        return kolon[3](deger) if len(kolon) > 3 else goster(deger)

    def _secim_degisti(self, _olay=None):
        secilen = self.agac.selection()
        if not secilen:
            return
        satir = self.satirlar[secilen[0]]
        self.secili_id = satir["id"]
        for a in self.alanlar:
            anahtar, deger = a["anahtar"], satir[a["anahtar"]]
            if a["tur"] == "id_secim":
                tersi = {i: m for m, i in self.secenek_haritasi[anahtar].items()}
                self.degiskenler[anahtar].set(tersi.get(deger, ""))
            elif a["tur"] == "ondalik":
                self.degiskenler[anahtar].set(ondalik_goster(deger))
            else:
                self.degiskenler[anahtar].set(goster(deger))
        self.secildi()

    def secildi(self):
        pass

    def temizle(self):
        for var in self.degiskenler.values():
            var.set("")
        self.agac.selection_remove(self.agac.selection())
        self.secili_id = None
        self.secildi()

    def _degerleri_oku(self):
        degerler = {}
        for a in self.alanlar:
            ham = self.degiskenler[a["anahtar"]].get().strip()
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
            messagebox.showinfo("Bilgi", "Önce listeden bir kayıt seçin.")
            return
        if guvenli(lambda: self.servis.guncelle(
                self.secili_id, **self._degerleri_oku()),
                self.durum_yaz, f"{self.ad} güncellendi."):
            self.yenile()

    def sil(self):
        if self.secili_id is None:
            messagebox.showinfo("Bilgi", "Önce listeden bir kayıt seçin.")
            return
        if not messagebox.askyesno(
                "Onay", f"Seçili {self.ad.lower()} kaydı silinsin mi?"):
            return
        if guvenli(lambda: self.servis.sil(self.secili_id),
                   self.durum_yaz, f"{self.ad} silindi."):
            self.temizle()
            self.yenile()


class IsEmriSekmesi(CrudSekmesi):
    def __init__(self, master, parca_servisi, **kwargs):
        self.parca_servisi = parca_servisi
        self.durum_filtre_var = tk.StringVar(value="Tümü")
        self.parca_haritasi = {}
        super().__init__(master, **kwargs)

    def _arac_cubugu_ek(self, cerceve):
        ctk.CTkLabel(cerceve, text="Durum:").pack(side="left", padx=(16, 4))
        ctk.CTkComboBox(cerceve, variable=self.durum_filtre_var,
                        values=["Tümü", *DURUMLAR], state="readonly",
                        width=140,
                        command=lambda _v: self._listeyi_doldur()).pack(
            side="left")
        ctk.CTkButton(self.dugme_cubugu, text="Sonraki duruma geç",
                      width=150, fg_color="#2e7d5b",
                      command=self.durum_ilerlet).pack(side="left", padx=5)

    def _uygun_mu(self, satir):
        filtre = self.durum_filtre_var.get()
        if filtre != "Tümü" and satir["durum"] != filtre:
            return False
        return super()._uygun_mu(satir)

    def _ek_panel_kur(self):
        panel = ctk.CTkFrame(self)
        panel.pack(fill="x", padx=4, pady=(4, 4))
        baslik = ctk.CTkFrame(panel, fg_color="transparent")
        baslik.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(baslik, text="Seçili iş emrinde kullanılan parçalar",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            side="left")
        self.maliyet_etiketi = ctk.CTkLabel(
            baslik, text="Toplam maliyet: —",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#4caf72")
        self.maliyet_etiketi.pack(side="right")

        kolonlar = [("parca_id", "No", 50), ("ad", "Parça", 330),
                    ("adet", "Adet", 80), ("birim_fiyat", "Birim fiyat", 130)]
        cerceve, self.parca_agac = agac_olustur(panel, kolonlar, 4)
        cerceve.pack(fill="x", padx=6)
        self.parca_agac.bind("<<TreeviewSelect>>", self._kalem_secildi)

        satir = ctk.CTkFrame(panel, fg_color="transparent")
        satir.pack(fill="x", padx=12, pady=(6, 10))
        self.parca_var, self.adet_var = tk.StringVar(), tk.StringVar(value="1")
        self.parca_kutu = ctk.CTkComboBox(satir, variable=self.parca_var,
                                          state="readonly", values=[""],
                                          width=300)
        self.parca_kutu.pack(side="left")
        ctk.CTkLabel(satir, text="Adet:").pack(side="left", padx=(12, 4))
        ctk.CTkEntry(satir, textvariable=self.adet_var, width=60).pack(
            side="left")
        for metin, komut, renk, genislik in (
                ("Parça ekle", self.parca_ekle, None, 100),
                ("Adedi ayarla", self.adet_ayarla, "gray40", 110),
                ("Çıkar", self.parca_cikar, "#b03a3a", 80)):
            ctk.CTkButton(satir, text=metin, width=genislik, fg_color=renk,
                          command=komut).pack(side="left", padx=(8, 0))

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
        self.parca_kutu.configure(values=list(self.parca_haritasi) or [""])
        if self.parca_var.get() not in self.parca_haritasi:
            self.parca_var.set("")

    def _kalemleri_listele(self):
        onceki = self.parca_agac.selection()
        self.parca_agac.delete(*self.parca_agac.get_children())
        self.maliyet_etiketi.configure(text="Toplam maliyet: —")
        if self.secili_id is None:
            return
        for p in self.servis.parcalari_listele(self.secili_id):
            self.parca_agac.insert(
                "", "end", iid=str(p["parca_id"]),
                values=(p["parca_id"], p["ad"], p["adet"],
                        tl(p["birim_fiyat"])))
        if onceki and self.parca_agac.exists(onceki[0]):
            self.parca_agac.selection_set(onceki[0])
        try:
            toplam = self.servis.toplam_maliyet(self.secili_id)
        except NotImplementedError:
            return
        self.maliyet_etiketi.configure(text=f"Toplam maliyet: {tl(toplam)}")

    def _kalem_secildi(self, _olay=None):
        secilen = self.parca_agac.selection()
        if not secilen:
            return
        parca_id = int(secilen[0])
        self.parca_var.set(next(
            (e for e, i in self.parca_haritasi.items() if i == parca_id), ""))
        self.adet_var.set(str(self.parca_agac.set(secilen[0], "adet")))

    def _kalem_islemi(self, islem, basari):
        if self.secili_id is None:
            messagebox.showinfo("Bilgi", "Önce bir iş emri seçin.")
            return
        if guvenli(islem, self.durum_yaz, basari):
            self._parca_secenekleri()
            self._kalemleri_listele()

    def parca_ekle(self):
        parca_id = self.parca_haritasi.get(self.parca_var.get())
        if parca_id is None:
            messagebox.showinfo("Bilgi", "Bir parça seçin.")
            return
        self._kalem_islemi(lambda: self.servis.parca_ekle(
            self.secili_id, parca_id,
            tam_sayi_oku(self.adet_var.get(), "Adet")), "Parça eklendi.")

    def adet_ayarla(self):
        secilen = self.parca_agac.selection()
        if not secilen:
            messagebox.showinfo("Bilgi", "Listeden bir parça kalemi seçin.")
            return
        self._kalem_islemi(lambda: self.servis.parca_adet_ayarla(
            self.secili_id, int(secilen[0]),
            tam_sayi_oku(self.adet_var.get(), "Adet")), "Adet ayarlandı.")

    def parca_cikar(self):
        secilen = self.parca_agac.selection()
        if not secilen:
            messagebox.showinfo("Bilgi", "Listeden çıkarılacak parçayı seçin.")
            return
        self._kalem_islemi(lambda: self.servis.parca_cikar(
            self.secili_id, int(secilen[0])), "Parça çıkarıldı.")

    def durum_ilerlet(self):
        if self.secili_id is None:
            messagebox.showinfo("Bilgi", "Önce bir iş emri seçin.")
            return
        if guvenli(lambda: self.servis.durum_ilerlet(self.secili_id),
                   self.durum_yaz, "Durum ilerletildi."):
            self.yenile()


class Uygulama(ctk.CTk):
    SEKME_ADLARI = ("Müşteriler", "Cihazlar", "İş Emirleri", "Parça Stoğu")

    def __init__(self, servisler):
        super().__init__()
        self.servisler = servisler
        self.title("ServisTakip - Bilgisayar Servisi Yönetimi")
        self.geometry("1020x860")
        self.minsize(940, 740)
        tablo_stilini_ayarla()

        self.durum_cubugu = ctk.CTkLabel(self, text="Hazır", anchor="w",
                                         text_color="gray70")
        self.durum_cubugu.pack(side="bottom", fill="x", padx=14, pady=(0, 6))

        self.sekmeler = ctk.CTkTabview(self, command=self._sekme_degisti)
        self.sekmeler.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        yapicilar = (self._musteri_sekmesi, self._cihaz_sekmesi,
                     self._is_emri_sekmesi, self._parca_sekmesi)
        self.sayfalar = {}
        for ad, yap in zip(self.SEKME_ADLARI, yapicilar):
            sayfa = yap(self.sekmeler.add(ad))
            sayfa.pack(fill="both", expand=True)
            self.sayfalar[ad] = sayfa

    def durum_yaz(self, metin):
        self.durum_cubugu.configure(text=metin)

    def _sekme_degisti(self):
        self.sayfalar[self.sekmeler.get()].yenile()

    def _musteri_sekmesi(self, kap):
        return CrudSekmesi(
            kap, "Müşteri", self.servisler.musteri,
            alanlar=[
                {"anahtar": "ad_soyad", "etiket": "Ad Soyad", "tur": "metin"},
                {"anahtar": "telefon", "etiket": "Telefon", "tur": "metin"},
                {"anahtar": "eposta", "etiket": "E-posta", "tur": "metin"}],
            kolonlar=[("id", "No", 50), ("ad_soyad", "Ad Soyad", 250),
                      ("telefon", "Telefon", 170), ("eposta", "E-posta", 270)],
            durum_yaz=self.durum_yaz)

    def _cihaz_sekmesi(self, kap):
        musteriler = self.servisler.musteri
        return CrudSekmesi(
            kap, "Cihaz", self.servisler.cihaz,
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
                {"anahtar": "seri_no", "etiket": "Seri No", "tur": "metin"}],
            kolonlar=[("id", "No", 50), ("musteri", "Müşteri", 200),
                      ("tur", "Tür", 90), ("marka", "Marka", 130),
                      ("model", "Model", 160), ("seri_no", "Seri No", 150)],
            durum_yaz=self.durum_yaz)

    def _is_emri_sekmesi(self, kap):
        cihazlar = self.servisler.cihaz
        return IsEmriSekmesi(
            kap, self.servisler.parca,
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
            kolonlar=[("id", "No", 45), ("musteri", "Müşteri", 150),
                      ("cihaz", "Cihaz", 140), ("aciklama", "Açıklama", 200),
                      ("durum", "Durum", 100),
                      ("iscilik_ucreti", "İşçilik", 90, tl),
                      ("olusturma_tarihi", "Tarih", 95)],
            durum_yaz=self.durum_yaz,
            satir_etiketi=lambda s: s["durum"], tablo_yuksekligi=6)

    def _parca_sekmesi(self, kap):
        def etiket(satir):
            if satir["stok"] <= 0:
                return "tukendi"
            return "az" if satir["stok"] <= DUSUK_STOK else None

        sayfa = CrudSekmesi(
            kap, "Parça", self.servisler.parca,
            alanlar=[
                {"anahtar": "ad", "etiket": "Parça adı", "tur": "metin"},
                {"anahtar": "birim_fiyat", "etiket": "Birim fiyat (TL)",
                 "tur": "ondalik"},
                {"anahtar": "stok", "etiket": "Stok adedi", "tur": "sayi"}],
            kolonlar=[("id", "No", 50), ("ad", "Parça", 340),
                      ("birim_fiyat", "Birim fiyat", 140, tl),
                      ("stok", "Stok", 100)],
            durum_yaz=self.durum_yaz, satir_etiketi=etiket)
        ctk.CTkLabel(sayfa, text=f"Kırmızı: tükendi · Turuncu: {DUSUK_STOK} "
                                 f"ve altı kaldı", text_color="gray60").pack(
            anchor="w", padx=10, pady=(0, 6))
        return sayfa
