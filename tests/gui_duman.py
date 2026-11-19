import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tkinter import messagebox

mesajlar = []
for ad in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, ad, lambda t, m, _a=ad, **k: mesajlar.append((_a, t, m)))
messagebox.askyesno = lambda *a, **k: True

import gui
from servisler import Servisler
from veritabani import VeriTabani

db = VeriTabani(":memory:")
app = gui.Uygulama(Servisler(db))
app.geometry("1020x860+40+20")
app.update()


def doldur(sayfa, **d):
    for k, v in d.items():
        sayfa.degiskenler[k].set(v)


def son():
    return mesajlar[-1] if mesajlar else None


S = app.sayfalar
# 1) iki aynı isimli müşteri
doldur(S["Müşteriler"], ad_soyad="Ali Veli", telefon="555", eposta="a@x.com"); S["Müşteriler"].ekle()
doldur(S["Müşteriler"], ad_soyad="Ali Veli", telefon="", eposta=""); S["Müşteriler"].ekle()
doldur(S["Müşteriler"], ad_soyad="İsmail Işık", telefon="", eposta=""); S["Müşteriler"].ekle()
assert len(db.musteri_listele()) == 3, "3 müşteri olmalı"

# arama: Türkçe karakter duyarsız
S["Müşteriler"].arama_var.set("ismail"); app.update()
assert len(S["Müşteriler"].agac.get_children()) == 1, "arama 'ismail' -> İsmail Işık"
S["Müşteriler"].arama_var.set(""); app.update()

# 2) cihaz sekmesi: aynı isimli müşteriler ayırt edilebilir
app.sekmeler.set("Cihazlar"); app._sekme_degisti(); app.update()
etiketler = list(S["Cihazlar"].secenek_haritasi["musteri_id"])
assert len(set(etiketler)) == 3, etiketler
print("müşteri etiketleri:", etiketler)
doldur(S["Cihazlar"], musteri_id=etiketler[1], tur="Laptop", marka="Lenovo", model="", seri_no="S1"); S["Cihazlar"].ekle()
assert db.cihaz_listele()[0]["musteri_id"] == 2, "ikinci Ali Veli seçilmeli"
doldur(S["Cihazlar"], musteri_id="", tur="Laptop", marka="x", model="y", seri_no=""); S["Cihazlar"].ekle()
assert son()[0] == "showwarning" and "Müşteri" in son()[2], son()

# 3) parça + geçersiz girişler
doldur(S["Parça Stoğu"], ad="RAM 8GB", birim_fiyat="450,50", stok="5"); S["Parça Stoğu"].ekle()
assert db.parca_getir(1)["birim_fiyat"] == 450.5
doldur(S["Parça Stoğu"], ad="SSD", birim_fiyat="abc", stok="1"); S["Parça Stoğu"].ekle()
assert son()[0] == "showwarning" and "Birim fiyat" in son()[2], son()
doldur(S["Parça Stoğu"], ad="SSD", birim_fiyat="-5", stok="1"); S["Parça Stoğu"].ekle()
assert son()[0] == "showerror" and "aralığın dışında" in son()[2], son()
doldur(S["Parça Stoğu"], ad="Pil", birim_fiyat="1.250,00", stok="2"); S["Parça Stoğu"].ekle()
assert db.parca_getir(2)["birim_fiyat"] == 1250.0
assert S["Parça Stoğu"].agac.tag_has("az"), "stok 2 -> 'az' etiketi"

# 4) iş emri + kalemler
app.sekmeler.set("İş Emirleri"); app._sekme_degisti(); app.update()
ie = S["İş Emirleri"]
cihaz_et = list(ie.secenek_haritasi["cihaz_id"])[0]
print("cihaz etiketi:", cihaz_et)
doldur(ie, cihaz_id=cihaz_et, durum="Bekliyor", aciklama="Açılmıyor", iscilik_ucreti="200"); ie.ekle()
assert db.is_emri_getir(1)["iscilik_ucreti"] == 200.0
ie.agac.selection_set("1"); app.update()
assert ie.secili_id == 1
ie.parca_var.set("#1 RAM 8GB (stok: 5)"); ie.adet_var.set("2"); ie.parca_ekle()
ie.adet_var.set("3"); ie.parca_ekle()
assert db.is_emri_parca_getir(1, 1)["adet"] == 5, "adet artmalı"
ie.parca_agac.selection_set("1"); app.update()
assert ie.adet_var.get() == "5"
ie.adet_var.set("2"); ie.adet_ayarla()
assert db.is_emri_parca_getir(1, 1)["adet"] == 2
ie.adet_var.set("0"); ie.adet_ayarla()
assert son()[0] == "showerror" and "aralığın dışında" in son()[2], son()
ie.durum_ilerlet()
assert son()[0] == "showinfo", son()
ie.parca_agac.selection_set("1"); app.update(); ie.parca_cikar()
assert db.is_emri_parca_getir(1, 1) is None
# durum filtresi
ie.durum_filtre_var.set("İşlemde"); ie._listeyi_doldur(); app.update()
assert len(ie.agac.get_children()) == 0
ie.durum_filtre_var.set("Tümü"); ie._listeyi_doldur(); app.update()
assert len(ie.agac.get_children()) == 1

# 5) silme kısıtı
app.sekmeler.set("Müşteriler"); app._sekme_degisti(); app.update()
m = S["Müşteriler"]
m.agac.selection_set("2"); app.update(); m.sil()
assert son()[0] == "showerror" and "ilişkili" in son()[2], son()

# 6) sıralama
m.agac.selection_remove(m.agac.selection()); m._sirala("ad_soyad"); app.update()
m._sirala("ad_soyad"); app.update()

print("durum çubuğu:", app.durum_cubugu.cget("text"))
print("TÜM DUMAN TESTLERİ GEÇTİ; kayıtlı mesajlar:", len(mesajlar))

app.destroy()
