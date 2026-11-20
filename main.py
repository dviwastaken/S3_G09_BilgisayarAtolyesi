import sys

from gui import Uygulama, uygulama_olustur
from servisler import Servisler
from veritabani import VeriTabani


def main():
    uygulama = uygulama_olustur(sys.argv)
    db = VeriTabani("servis_takip.db")
    pencere = Uygulama(Servisler(db))
    pencere.show()
    cikis = uygulama.exec()
    db.kapat()
    sys.exit(cikis)


if __name__ == "__main__":
    main()
