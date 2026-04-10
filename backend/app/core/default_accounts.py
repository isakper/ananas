"""Default chart-of-accounts seed values."""

from __future__ import annotations

DEFAULT_ACCOUNTS: tuple[tuple[int, str], ...] = (
    (1930, "Företagskonto"),
    (2440, "Leverantörsskulder"),
    (2640, "Ingående moms"),
    (4010, "Inköp material & varor"),
    (5010, "Lokalhyra"),
    (5060, "Driftskostnader lokal"),
    (5220, "Hyra inventarier"),
    (5410, "Förbrukningsinventarier"),
    (5460, "Förbrukningsmaterial"),
    (5610, "Kontorsmaterial"),
    (5690, "Övriga kontorskostnader"),
    (6110, "Kontorsförnödenheter"),
    (6211, "Fast telefoni"),
    (6230, "Datakommunikation"),
    (6310, "Företagsförsäkringar"),
    (6530, "IT-tjänster"),
    (6540, "IT-drift & hosting"),
    (6570, "Programvara, licenser"),
    (6910, "Licensavgifter & medlemskap"),
    (7631, "Personalmat & fika"),
)
