import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PySide6.QtWidgets import QApplication

import gui
from servisler import Servisler
from veritabani import VeriTabani


@pytest.fixture
def uyg(monkeypatch, tmp_path):
    mesajlar = []
    for ad in ("bilgi", "uyari", "hata"):
        monkeypatch.setattr(gui, ad, lambda b, m, _a=ad: mesajlar.append((_a, b, m)))
    monkeypatch.setattr(gui, "onay", lambda b, m: True)
    monkeypatch.setattr(gui, "AYAR_DOSYASI", tmp_path / "ayar.json")
    gui.uygulama_olustur([])
    db = VeriTabani(":memory:")
    pencere = gui.Uygulama(Servisler(db))
    yield pencere, db, mesajlar
    pencere.close()
    db.kapat()


def doldur(sayfa, **alanlar):
    for anahtar, deger in alanlar.items():
        sayfa.form_yaz(anahtar, deger)


def secenekler(sayfa, anahtar):
    kutu = sayfa.araclar[anahtar]
    return [kutu.itemText(i) for i in range(kutu.count())]


def musteri_ekle(uyg, ad):
    pencere, _, _ = uyg
    sayfa = pencere.sayfalar["Müşteriler"]
    doldur(sayfa, ad_soyad=ad, telefon="", eposta="")
    sayfa.ekle()
    return sayfa


def test_ayni_isimli_musteriler_ayirt_edilir(uyg):
    pencere, db, mesajlar = uyg
    for ad in ("Ali Veli", "Ali Veli", "İsmail Işık"):
        musteri_ekle(uyg, ad)
    pencere.modul_ac("Cihazlar")
    cihaz = pencere.sayfalar["Cihazlar"]
    etiketler = secenekler(cihaz, "musteri_id")
    assert len(set(etiketler)) == 3
    doldur(cihaz, musteri_id=etiketler[1], tur="Laptop", marka="Lenovo",
           model="", seri_no="S1")
    cihaz.ekle()
    assert db.cihaz_listele()[0]["musteri_id"] == 2
    doldur(cihaz, musteri_id="", tur="Laptop", marka="x", model="y", seri_no="")
    cihaz.ekle()
    assert mesajlar[-1][0] == "uyari" and "Müşteri" in mesajlar[-1][2]


def test_arama_turkce_karakterden_bagimsiz(uyg):
    for ad in ("Ali Veli", "İsmail Işık"):
        sayfa = musteri_ekle(uyg, ad)
    sayfa.arama.setText("ismail")
    assert len(sayfa.liste.cocuklar()) == 1
    sayfa.arama.setText("")
    assert len(sayfa.liste.cocuklar()) == 2


def test_parca_girisleri_ve_stok_vurgusu(uyg):
    pencere, db, mesajlar = uyg
    sayfa = pencere.sayfalar["Parça Stoğu"]
    doldur(sayfa, ad="RAM 8GB", birim_fiyat="450,50", stok="5")
    sayfa.ekle()
    assert db.parca_getir(1)["birim_fiyat"] == 450.5
    doldur(sayfa, ad="SSD", birim_fiyat="abc", stok="1")
    sayfa.ekle()
    assert mesajlar[-1][0] == "uyari" and "Birim fiyat" in mesajlar[-1][2]
    doldur(sayfa, ad="SSD", birim_fiyat="-5", stok="1")
    sayfa.ekle()
    assert mesajlar[-1][0] == "hata" and "aralığın dışında" in mesajlar[-1][2]
    doldur(sayfa, ad="Pil", birim_fiyat="1.250,00", stok="2")
    sayfa.ekle()
    assert db.parca_getir(2)["birim_fiyat"] == 1250.0
    assert sayfa.liste.etiketli("az")


def test_is_emri_kalemleri_durum_ve_filtre(uyg):
    pencere, db, mesajlar = uyg
    musteri = db.musteri_ekle("Ayşe Yılmaz", "", "")
    db.cihaz_ekle(musteri, "Laptop", "Lenovo", "T14", "")
    db.parca_ekle("RAM 8GB", 450.5, 8)
    pencere.modul_ac("İş Emirleri")
    ie = pencere.sayfalar["İş Emirleri"]
    doldur(ie, cihaz_id=secenekler(ie, "cihaz_id")[0], durum="Bekliyor",
           aciklama="Açılmıyor", iscilik_ucreti="200")
    ie.ekle()
    assert db.is_emri_getir(1)["iscilik_ucreti"] == 200.0

    ie.liste.sec("1")
    assert ie.secili_id == 1
    ie.parca_kutu.setCurrentIndex(0)
    ie.adet_girisi.setText("2")
    ie.parca_ekle()
    ie.adet_girisi.setText("3")
    ie.parca_ekle()
    assert db.is_emri_parca_getir(1, 1)["adet"] == 5

    ie.kalem_sec(1)
    assert ie.adet_girisi.text() == "5"
    ie.adet_girisi.setText("2")
    ie.adet_ayarla()
    assert db.is_emri_parca_getir(1, 1)["adet"] == 2
    ie.adet_girisi.setText("0")
    ie.adet_ayarla()
    assert mesajlar[-1][0] == "hata" and "aralığın dışında" in mesajlar[-1][2]

    ie.durum_ilerlet()
    assert mesajlar[-1][0] == "bilgi"
    assert ie.maliyet_etiketi.text() == "—"

    ie.kalem_sec(1)
    ie.parca_cikar()
    assert db.is_emri_parca_getir(1, 1) is None

    ie.durum_filtre.setCurrentText("İşlemde")
    assert len(ie.liste.cocuklar()) == 0
    ie.durum_filtre.setCurrentText("Tümü")
    assert len(ie.liste.cocuklar()) == 1


def test_baglantili_kayit_silinemez(uyg):
    pencere, db, mesajlar = uyg
    musteri = db.musteri_ekle("Ayşe Yılmaz", "", "")
    db.cihaz_ekle(musteri, "Laptop", "Lenovo", "T14", "")
    pencere.modul_ac("Müşteriler")
    sayfa = pencere.sayfalar["Müşteriler"]
    sayfa.liste.sec("1")
    sayfa.sil()
    assert mesajlar[-1][0] == "hata" and "ilişkili" in mesajlar[-1][2]
    assert db.musteri_getir(1) is not None


def test_koyu_mod_degisir_ve_kaydedilir(uyg):
    pencere, _, _ = uyg
    pencere.koyu_kutusu.setChecked(True)
    assert pencere.koyu and gui.ayar_oku()
    assert gui.palet(True)["zemin"] in QApplication.instance().styleSheet()
    pencere.koyu_kutusu.setChecked(False)
    assert not pencere.koyu and not gui.ayar_oku()
    assert gui.palet(False)["metin"] in QApplication.instance().styleSheet()
