import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from veritabani import SEMA_SURUMU, VeriTabani  # noqa: E402


@pytest.fixture
def db():
    d = VeriTabani(":memory:")
    yield d
    d.kapat()


@pytest.fixture
def dolu(db):
    m = db.musteri_ekle("Ali Veli", "5551112233", "ali@x.com")
    c = db.cihaz_ekle(m, "Laptop", "Lenovo", "T14", "SN1")
    e = db.is_emri_ekle(c, "Açılmıyor", "Bekliyor", 200.0)
    p = db.parca_ekle("RAM 8GB", 450.5, 5)
    return db, m, c, e, p


def indeksler(db):
    return {r["name"] for r in db._sorgula(
        "SELECT name FROM sqlite_master WHERE type = 'index' "
        "AND name LIKE 'idx_%'")}


def test_yeni_veritabani_son_surumde(db):
    assert db.sema_surumu() == SEMA_SURUMU
    assert indeksler(db) == {"idx_cihaz_musteri", "idx_is_emri_cihaz",
                             "idx_is_emri_durum", "idx_is_emri_parca_parca"}


def test_foreign_keys_acik(db):
    assert db._tek("PRAGMA foreign_keys")[0] == 1


def test_eski_surumsuz_dosya_yukseltilir(tmp_path):
    yol = tmp_path / "eski.db"
    ham = sqlite3.connect(yol)
    ham.executescript("""
        CREATE TABLE musteri (id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL, telefon TEXT, eposta TEXT);
        INSERT INTO musteri (ad_soyad) VALUES ('Eski Kayıt');
    """)
    ham.close()
    d = VeriTabani(str(yol))
    assert d.sema_surumu() == SEMA_SURUMU
    assert [m["ad_soyad"] for m in d.musteri_listele()] == ["Eski Kayıt"]
    assert "idx_cihaz_musteri" in indeksler(d)
    d.kapat()
    d2 = VeriTabani(str(yol))  # ikinci açılış zararsız
    assert d2.sema_surumu() == SEMA_SURUMU
    d2.kapat()


def test_daha_yeni_sema_reddedilir(tmp_path):
    yol = tmp_path / "yeni.db"
    ham = sqlite3.connect(yol)
    ham.execute(f"PRAGMA user_version = {SEMA_SURUMU + 1}")
    ham.close()
    with pytest.raises(RuntimeError):
        VeriTabani(str(yol))


def test_musteri_cihazi_varken_silinemez(dolu):
    db, m, *_ = dolu
    with pytest.raises(sqlite3.IntegrityError):
        db.musteri_sil(m)
    assert db.musteri_getir(m) is not None


def test_cihaz_is_emri_varken_silinemez(dolu):
    db, _, c, *_ = dolu
    with pytest.raises(sqlite3.IntegrityError):
        db.cihaz_sil(c)


def test_parca_kullanilirken_silinemez(dolu):
    db, _, _, e, p = dolu
    db.is_emrine_parca_ekle(e, p, 1)
    with pytest.raises(sqlite3.IntegrityError):
        db.parca_sil(p)


def test_is_emri_silinince_kalemler_gider(dolu):
    db, _, _, e, p = dolu
    db.is_emrine_parca_ekle(e, p, 2)
    db.is_emri_sil(e)
    assert db.is_emri_parcalari(e) == []


@pytest.mark.parametrize("sql,param", [
    ("INSERT INTO parca (ad, birim_fiyat, stok) VALUES (?, ?, ?)", ("X", 1, -1)),
    ("INSERT INTO parca (ad, birim_fiyat, stok) VALUES (?, ?, ?)", ("X", -1, 0)),
    ("INSERT INTO parca (ad, birim_fiyat, stok) VALUES (?, ?, ?)", ("  ", 1, 0)),
    ("INSERT INTO musteri (ad_soyad) VALUES (?)", ("   ",)),
])
def test_check_kisitlari(db, sql, param):
    with pytest.raises(sqlite3.IntegrityError):
        db._calistir(sql, param)


def test_gecersiz_tur_durum_adet(dolu):
    db, m, c, e, p = dolu
    with pytest.raises(sqlite3.IntegrityError):
        db.cihaz_ekle(m, "Tablet", "a", "b", "c")
    with pytest.raises(sqlite3.IntegrityError):
        db.is_emri_ekle(c, "x", "Bilinmiyor", 0)
    with pytest.raises(sqlite3.IntegrityError):
        db.is_emri_ekle(c, "x", "Bekliyor", -5)
    with pytest.raises(sqlite3.IntegrityError):
        db.is_emrine_parca_ekle(e, p, 0)


def test_ayni_parca_eklenince_adet_artar_stok_degismez(dolu):
    db, _, _, e, p = dolu
    db.is_emrine_parca_ekle(e, p, 2)
    db.is_emrine_parca_ekle(e, p, 3)
    assert db.is_emri_parca_getir(e, p)["adet"] == 5
    assert db.parca_getir(p)["stok"] == 5


def test_adet_ayarla_ve_cikar(dolu):
    db, _, _, e, p = dolu
    db.is_emrine_parca_ekle(e, p, 4)
    db.is_emri_parca_adet_ayarla(e, p, 1)
    assert db.is_emri_parca_getir(e, p)["adet"] == 1
    with pytest.raises(sqlite3.IntegrityError):  # 0 kalem değil, çıkarma işi
        db.is_emri_parca_adet_ayarla(e, p, 0)
    db.is_emrinden_parca_cikar(e, p)
    assert db.is_emri_parca_getir(e, p) is None


def test_islem_basarili_ise_kaydeder(dolu):
    db, _, _, e, p = dolu
    with db.islem():
        db.parca_stok_degistir(p, -2)
        db.is_emrine_parca_ekle(e, p, 2)
    assert db.parca_getir(p)["stok"] == 3
    assert db.is_emri_parca_getir(e, p)["adet"] == 2


def test_islem_hatada_hepsini_geri_alir(dolu):
    db, _, _, e, p = dolu
    with pytest.raises(sqlite3.IntegrityError):
        with db.islem():
            db.parca_stok_degistir(p, -2)
            db.is_emrine_parca_ekle(e, p, 0)  # CHECK (adet > 0) ihlali
    assert db.parca_getir(p)["stok"] == 5
    assert db.is_emri_parca_getir(e, p) is None
    assert db.baglanti.in_transaction is False


def test_islem_stok_negatife_inerse_geri_alir(dolu):
    db, _, _, e, p = dolu
    with pytest.raises(sqlite3.IntegrityError):
        with db.islem():
            db.is_emrine_parca_ekle(e, p, 9)
            db.parca_stok_degistir(p, -9)  # stok 5, CHECK ihlali
    assert db.is_emri_parca_getir(e, p) is None
    assert db.parca_getir(p)["stok"] == 5


def test_ic_ice_islem_yalniz_kendini_geri_alir(dolu):
    db, _, _, e, p = dolu
    with db.islem():
        db.parca_stok_degistir(p, -1)
        with pytest.raises(sqlite3.IntegrityError):
            with db.islem():
                db.parca_stok_degistir(p, -1)
                db.is_emrine_parca_ekle(e, p, 0)
        db.parca_stok_degistir(p, -1)
    assert db.parca_getir(p)["stok"] == 3  # iç bloktaki -1 geri alındı


def test_islem_disindaki_yazma_hemen_kalicidir(tmp_path):
    yol = str(tmp_path / "k.db")
    d = VeriTabani(yol)
    d.musteri_ekle("Kalıcı", "", "")
    d.kapat()
    d2 = VeriTabani(yol)
    assert [m["ad_soyad"] for m in d2.musteri_listele()] == ["Kalıcı"]
    d2.kapat()


def test_cihaz_adi_bos_marka_model_ile_none_olmaz(db):
    m = db.musteri_ekle("Ayşe", "", "")
    c1 = db.cihaz_ekle(m, "Laptop", None, "X1", "")
    c2 = db.cihaz_ekle(m, "Laptop", "Asus", None, "")
    c3 = db.cihaz_ekle(m, "Diğer", None, None, "")
    ids = {c: db.is_emri_ekle(c, "t", "Bekliyor", 0) for c in (c1, c2, c3)}
    adlar = {r["id"]: r["cihaz"] for r in db.is_emri_listele()}
    assert adlar[ids[c1]] == "X1"
    assert adlar[ids[c2]] == "Asus"
    assert adlar[ids[c3]] == ""


def test_getir_ve_listeler_ayni_alanlari_verir(dolu):
    db, m, c, e, p = dolu
    assert dict(db.is_emri_getir(e)) == dict(db.is_emri_listele()[0])
    assert dict(db.cihaz_getir(c)) == dict(db.cihaz_listele()[0])
    assert db.is_emri_getir(999) is None
    assert set(db.is_emri_listele()[0].keys()) == {
        "id", "cihaz_id", "musteri", "cihaz", "aciklama", "durum",
        "iscilik_ucreti", "olusturma_tarihi"}
