class _Servis:
    def __init__(self, db):
        self.db = db


class MusteriServisi(_Servis):
    def listele(self):
        return self.db.musteri_listele()

    def ekle(self, **alanlar):
        return self.db.musteri_ekle(**alanlar)

    def guncelle(self, id_, **alanlar):
        self.db.musteri_guncelle(id_, **alanlar)

    def sil(self, id_):
        self.db.musteri_sil(id_)


class CihazServisi(_Servis):
    def listele(self):
        return self.db.cihaz_listele()

    def ekle(self, **alanlar):
        return self.db.cihaz_ekle(**alanlar)

    def guncelle(self, id_, **alanlar):
        self.db.cihaz_guncelle(id_, **alanlar)

    def sil(self, id_):
        self.db.cihaz_sil(id_)


class ParcaServisi(_Servis):
    def listele(self):
        return self.db.parca_listele()

    def ekle(self, **alanlar):
        return self.db.parca_ekle(**alanlar)

    def guncelle(self, id_, **alanlar):
        self.db.parca_guncelle(id_, **alanlar)

    def sil(self, id_):
        self.db.parca_sil(id_)


class IsEmriServisi(_Servis):
    def listele(self):
        return self.db.is_emri_listele()

    def ekle(self, **alanlar):
        return self.db.is_emri_ekle(**alanlar)

    def guncelle(self, id_, **alanlar):
        self.db.is_emri_guncelle(id_, **alanlar)

    def sil(self, id_):
        self.db.is_emri_sil(id_)

    def parcalari_listele(self, is_emri_id):
        return self.db.is_emri_parcalari(is_emri_id)

    def parca_ekle(self, is_emri_id, parca_id, adet):
        self.db.is_emrine_parca_ekle(is_emri_id, parca_id, adet)

    def parca_adet_ayarla(self, is_emri_id, parca_id, adet):
        self.db.is_emri_parca_adet_ayarla(is_emri_id, parca_id, adet)

    def parca_cikar(self, is_emri_id, parca_id):
        self.db.is_emrinden_parca_cikar(is_emri_id, parca_id)

    def toplam_maliyet(self, is_emri_id):
        raise NotImplementedError("Toplam maliyet henüz hesaplanmıyor.")

    def durum_ilerlet(self, is_emri_id):
        raise NotImplementedError("Durum ilerletme henüz hazır değil.")


class Servisler:
    def __init__(self, db):
        self.musteri = MusteriServisi(db)
        self.cihaz = CihazServisi(db)
        self.parca = ParcaServisi(db)
        self.is_emri = IsEmriServisi(db)
