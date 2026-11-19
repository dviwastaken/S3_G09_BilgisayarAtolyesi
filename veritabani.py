import sqlite3
from contextlib import contextmanager

DURUMLAR = ("Bekliyor", "İşlemde", "Tamamlandı", "Teslim edildi")
CIHAZ_TURLERI = ("Masaüstü", "Laptop", "Diğer")
SEMA_SURUMU = 1


class VeriTabani:
    def __init__(self, yol="servis_takip.db"):
        self.baglanti = sqlite3.connect(yol)
        self.baglanti.row_factory = sqlite3.Row
        self.baglanti.execute("PRAGMA foreign_keys = ON")
        self._islem_derinligi = 0
        self._sema_guncelle()

    def _calistir(self, sql, parametre=()):
        if self._islem_derinligi:
            return self.baglanti.execute(sql, parametre)
        with self.baglanti:
            return self.baglanti.execute(sql, parametre)

    def _sorgula(self, sql, parametre=()):
        return self.baglanti.execute(sql, parametre).fetchall()

    def _tek(self, sql, parametre=()):
        return self.baglanti.execute(sql, parametre).fetchone()

    @contextmanager
    def islem(self):
        if self._islem_derinligi:
            ad = f"sp{self._islem_derinligi}"
            self.baglanti.execute(f"SAVEPOINT {ad}")
            self._islem_derinligi += 1
            try:
                yield self
            except BaseException:
                self.baglanti.execute(f"ROLLBACK TO {ad}")
                self.baglanti.execute(f"RELEASE {ad}")
                raise
            else:
                self.baglanti.execute(f"RELEASE {ad}")
            finally:
                self._islem_derinligi -= 1
            return

        self.baglanti.execute("BEGIN")
        self._islem_derinligi = 1
        try:
            yield self
        except BaseException:
            self.baglanti.rollback()
            raise
        else:
            self.baglanti.commit()
        finally:
            self._islem_derinligi = 0

    def kapat(self):
        self.baglanti.close()

    def sema_surumu(self):
        return self._tek("PRAGMA user_version")[0]

    def _sema_guncelle(self):
        surum = self.sema_surumu()
        if surum > SEMA_SURUMU:
            raise RuntimeError(
                f"Veritabanı şema sürümü ({surum}) bu programdan yeni ({SEMA_SURUMU}).")
        if surum < 1:
            self._surum_1()

    def _surum_1(self):
        durumlar = ", ".join(f"'{d}'" for d in DURUMLAR)
        turler = ", ".join(f"'{t}'" for t in CIHAZ_TURLERI)
        self.baglanti.executescript(f"""
            BEGIN;

            CREATE TABLE IF NOT EXISTS musteri (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad  TEXT NOT NULL CHECK (length(trim(ad_soyad)) > 0),
                telefon   TEXT,
                eposta    TEXT
            );

            CREATE TABLE IF NOT EXISTS cihaz (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                musteri_id  INTEGER NOT NULL
                            REFERENCES musteri(id) ON DELETE RESTRICT,
                tur         TEXT NOT NULL CHECK (tur IN ({turler})),
                marka       TEXT,
                model       TEXT,
                seri_no     TEXT
            );

            CREATE TABLE IF NOT EXISTS is_emri (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                cihaz_id          INTEGER NOT NULL
                                  REFERENCES cihaz(id) ON DELETE RESTRICT,
                aciklama          TEXT,
                durum             TEXT NOT NULL DEFAULT 'Bekliyor'
                                  CHECK (durum IN ({durumlar})),
                iscilik_ucreti    REAL NOT NULL DEFAULT 0
                                  CHECK (iscilik_ucreti >= 0),
                olusturma_tarihi  TEXT NOT NULL
                                  DEFAULT (date('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS parca (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ad           TEXT NOT NULL CHECK (length(trim(ad)) > 0),
                birim_fiyat  REAL NOT NULL CHECK (birim_fiyat >= 0),
                stok         INTEGER NOT NULL DEFAULT 0 CHECK (stok >= 0)
            );

            CREATE TABLE IF NOT EXISTS is_emri_parca (
                is_emri_id  INTEGER NOT NULL
                            REFERENCES is_emri(id) ON DELETE CASCADE,
                parca_id    INTEGER NOT NULL
                            REFERENCES parca(id) ON DELETE RESTRICT,
                adet        INTEGER NOT NULL CHECK (adet > 0),
                PRIMARY KEY (is_emri_id, parca_id)
            );

            CREATE INDEX IF NOT EXISTS idx_cihaz_musteri ON cihaz (musteri_id);
            CREATE INDEX IF NOT EXISTS idx_is_emri_cihaz ON is_emri (cihaz_id);
            CREATE INDEX IF NOT EXISTS idx_is_emri_durum ON is_emri (durum);
            CREATE INDEX IF NOT EXISTS idx_is_emri_parca_parca
                ON is_emri_parca (parca_id);

            PRAGMA user_version = 1;
            COMMIT;
        """)

    # müşteri
    def musteri_ekle(self, ad_soyad, telefon, eposta):
        return self._calistir(
            "INSERT INTO musteri (ad_soyad, telefon, eposta) VALUES (?, ?, ?)",
            (ad_soyad, telefon, eposta)).lastrowid

    def musteri_listele(self):
        return self._sorgula(
            "SELECT id, ad_soyad, telefon, eposta FROM musteri "
            "ORDER BY ad_soyad, id")

    def musteri_getir(self, id_):
        return self._tek(
            "SELECT id, ad_soyad, telefon, eposta FROM musteri WHERE id = ?",
            (id_,))

    def musteri_guncelle(self, id_, ad_soyad, telefon, eposta):
        self._calistir(
            "UPDATE musteri SET ad_soyad = ?, telefon = ?, eposta = ? WHERE id = ?",
            (ad_soyad, telefon, eposta, id_))

    def musteri_sil(self, id_):
        self._calistir("DELETE FROM musteri WHERE id = ?", (id_,))

    # cihaz
    _CIHAZ_SECIM = (
        "SELECT c.id, c.musteri_id, m.ad_soyad AS musteri, c.tur, "
        "       c.marka, c.model, c.seri_no "
        "FROM cihaz c JOIN musteri m ON m.id = c.musteri_id ")

    def cihaz_ekle(self, musteri_id, tur, marka, model, seri_no):
        return self._calistir(
            "INSERT INTO cihaz (musteri_id, tur, marka, model, seri_no) "
            "VALUES (?, ?, ?, ?, ?)",
            (musteri_id, tur, marka, model, seri_no)).lastrowid

    def cihaz_listele(self):
        return self._sorgula(self._CIHAZ_SECIM + "ORDER BY c.id DESC")

    def cihaz_getir(self, id_):
        return self._tek(self._CIHAZ_SECIM + "WHERE c.id = ?", (id_,))

    def cihaz_guncelle(self, id_, musteri_id, tur, marka, model, seri_no):
        self._calistir(
            "UPDATE cihaz SET musteri_id = ?, tur = ?, marka = ?, model = ?, "
            "seri_no = ? WHERE id = ?",
            (musteri_id, tur, marka, model, seri_no, id_))

    def cihaz_sil(self, id_):
        self._calistir("DELETE FROM cihaz WHERE id = ?", (id_,))

    # iş emri
    _IS_EMRI_SECIM = (
        "SELECT e.id, e.cihaz_id, m.ad_soyad AS musteri, "
        "       TRIM(COALESCE(c.marka, '') || ' ' || COALESCE(c.model, '')) "
        "           AS cihaz, "
        "       e.aciklama, e.durum, e.iscilik_ucreti, e.olusturma_tarihi "
        "FROM is_emri e "
        "JOIN cihaz c ON c.id = e.cihaz_id "
        "JOIN musteri m ON m.id = c.musteri_id ")

    def is_emri_ekle(self, cihaz_id, aciklama, durum, iscilik_ucreti):
        return self._calistir(
            "INSERT INTO is_emri (cihaz_id, aciklama, durum, iscilik_ucreti) "
            "VALUES (?, ?, ?, ?)",
            (cihaz_id, aciklama, durum, iscilik_ucreti)).lastrowid

    def is_emri_listele(self):
        return self._sorgula(self._IS_EMRI_SECIM + "ORDER BY e.id DESC")

    def is_emri_getir(self, id_):
        return self._tek(self._IS_EMRI_SECIM + "WHERE e.id = ?", (id_,))

    def is_emri_guncelle(self, id_, cihaz_id, aciklama, durum, iscilik_ucreti):
        self._calistir(
            "UPDATE is_emri SET cihaz_id = ?, aciklama = ?, durum = ?, "
            "iscilik_ucreti = ? WHERE id = ?",
            (cihaz_id, aciklama, durum, iscilik_ucreti, id_))

    def is_emri_sil(self, id_):
        self._calistir("DELETE FROM is_emri WHERE id = ?", (id_,))

    # parça
    def parca_ekle(self, ad, birim_fiyat, stok):
        return self._calistir(
            "INSERT INTO parca (ad, birim_fiyat, stok) VALUES (?, ?, ?)",
            (ad, birim_fiyat, stok)).lastrowid

    def parca_listele(self):
        return self._sorgula(
            "SELECT id, ad, birim_fiyat, stok FROM parca ORDER BY ad, id")

    def parca_getir(self, id_):
        return self._tek(
            "SELECT id, ad, birim_fiyat, stok FROM parca WHERE id = ?", (id_,))

    def parca_guncelle(self, id_, ad, birim_fiyat, stok):
        self._calistir(
            "UPDATE parca SET ad = ?, birim_fiyat = ?, stok = ? WHERE id = ?",
            (ad, birim_fiyat, stok, id_))

    def parca_sil(self, id_):
        self._calistir("DELETE FROM parca WHERE id = ?", (id_,))

    def parca_stok_degistir(self, parca_id, fark):
        self._calistir("UPDATE parca SET stok = stok + ? WHERE id = ?",
                       (fark, parca_id))

    # iş emri - parça
    def is_emrine_parca_ekle(self, is_emri_id, parca_id, adet):
        self._calistir(
            "INSERT INTO is_emri_parca (is_emri_id, parca_id, adet) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT (is_emri_id, parca_id) "
            "DO UPDATE SET adet = adet + excluded.adet",
            (is_emri_id, parca_id, adet))

    def is_emri_parca_adet_ayarla(self, is_emri_id, parca_id, adet):
        self._calistir(
            "UPDATE is_emri_parca SET adet = ? "
            "WHERE is_emri_id = ? AND parca_id = ?",
            (adet, is_emri_id, parca_id))

    def is_emrinden_parca_cikar(self, is_emri_id, parca_id):
        self._calistir(
            "DELETE FROM is_emri_parca WHERE is_emri_id = ? AND parca_id = ?",
            (is_emri_id, parca_id))

    def is_emri_parca_getir(self, is_emri_id, parca_id):
        return self._tek(
            "SELECT ep.parca_id, p.ad, p.birim_fiyat, ep.adet "
            "FROM is_emri_parca ep JOIN parca p ON p.id = ep.parca_id "
            "WHERE ep.is_emri_id = ? AND ep.parca_id = ?",
            (is_emri_id, parca_id))

    def is_emri_parcalari(self, is_emri_id):
        return self._sorgula(
            "SELECT ep.parca_id, p.ad, p.birim_fiyat, ep.adet "
            "FROM is_emri_parca ep JOIN parca p ON p.id = ep.parca_id "
            "WHERE ep.is_emri_id = ? ORDER BY p.ad",
            (is_emri_id,))
