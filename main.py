from gui import Uygulama
from servisler import Servisler
from veritabani import VeriTabani


def main():
    db = VeriTabani("servis_takip.db")
    try:
        Uygulama(Servisler(db)).mainloop()
    finally:
        db.kapat()


if __name__ == "__main__":
    main()
